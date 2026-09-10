"""Replay frozen language evaluation and archived v0.46 service inputs offline.

Gold scores reproduce a historical development benchmark, not real-user accuracy.
Service coverage measures routing/structure and must not be called accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from moongcheap_ai.demand_clustering.evaluation.profile_release import (
    category_code_contract,
)
from moongcheap_ai.demand_clustering.part_a_integration import (
    build_part_b_parser,
    file_digest,
)
from moongcheap_ai.demand_constraints import DemandConstraintParser


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def atoms(items):
    return sorted({(c["facet_name"], int(c["value_code"]), c["constraint_type"]) for c in items})


def meaning(payload):
    """Compare decision-bearing fields; exclude proofs and renamed diagnostics."""
    return {
        "status": payload["status"],
        "mode": payload["effective_requirement_mode"],
        "constraints": atoms(payload["constraints"]),
        "preferenceGroups": sorted([
            (g["operator"], g["aggregation"], atoms(g["members"]))
            for g in payload["preference_groups"]
        ]),
        "semanticPreferences": list(payload["semantic_preferences"]),
        "taxonomyEquivalences": payload["taxonomy_equivalences"],
    }


def archived_meaning(row):
    return meaning({
        "status": row["constraint_status"],
        "effective_requirement_mode": row["effective_constraint_mode"],
        "constraints": json.loads(row["constraints"]),
        "preference_groups": json.loads(row["preference_groups"]),
        "semantic_preferences": json.loads(row["free_text_preferences"]),
        "taxonomy_equivalences": json.loads(row["taxonomy_equivalences"]),
    })


def condition_set(result):
    return set(result["constraints"]) | {
        item for _, _, members in result["preferenceGroups"] for item in members
    }


def evaluate_gold(parser, rows, *, service):
    failures = []
    parsed = parsed_correct = 0
    statuses = Counter()
    for row in rows:
        result = (
            parser.interpret(row["category_id"], row["extra_requirement"], is_substitutable=True)
            if service else parser.parse(row["category_id"], row["extra_requirement"])
        ).to_dict()
        expected = atoms(json.loads(row["expected_constraints_json"]))
        correct = result["status"] == row["expected_status"]
        if row["expected_status"] == "PARSED" or result["status"] == "PARSED":
            correct = correct and atoms(result["constraints"]) == expected
        statuses[result["status"]] += 1
        parsed += result["status"] == "PARSED"
        parsed_correct += result["status"] == "PARSED" and correct
        if not correct:
            failures.append({
                "sampleId": row["sample_id"], "text": row["extra_requirement"],
                "expectedStatus": row["expected_status"], "expectedConstraints": expected,
                "actual": result,
            })
    return {
        "rows": len(rows), "correct": len(rows) - len(failures),
        "parsed": parsed, "parsedCorrect": parsed_correct,
        "incorrectAutomaticInterpretations": parsed - parsed_correct,
        "statusCounts": dict(statuses), "failures": failures,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--baseline-taxonomy", type=Path, required=True)
    cli.add_argument("--service-input", type=Path, required=True)
    cli.add_argument("--archived-service-output", type=Path, required=True)
    cli.add_argument("--gold", type=Path, default=Path("tests/demand_constraints/fixtures/v042_approved_eval.csv"))
    cli.add_argument("--taxonomy", type=Path, default=Path("config/facet_taxonomy_v2_2.json"))
    cli.add_argument("--rules", type=Path, default=Path("config/demand_constraint_rules.json"))
    cli.add_argument("--aliases", type=Path, default=Path("config/model1_aliases_reviewed_v2.json"))
    cli.add_argument("--compatibility-aliases", type=Path, default=Path("config/demand_constraint_aliases.json"))
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    before_taxonomy = json.loads(args.baseline_taxonomy.read_text(encoding="utf-8"))
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
    parsers = {
        "before": DemandConstraintParser.from_taxonomy(
            before_taxonomy, rules_path=args.rules, aliases_path=args.compatibility_aliases,
        ),
        "aOnly": build_part_b_parser(taxonomy, rules_path=args.rules, aliases_path=args.aliases)[0],
        "after": build_part_b_parser(
            taxonomy, rules_path=args.rules, aliases_path=args.aliases,
            compatibility_aliases_path=args.compatibility_aliases,
        )[0],
    }
    gold_rows = read_rows(args.gold)
    service_rows = read_rows(args.service_input)
    archived_rows = read_rows(args.archived_service_output)
    if not gold_rows or not service_rows:
        raise ValueError("evaluation inputs must be nonempty")
    archived = {row["demand_id"]: row for row in archived_rows}
    ids = [row["demand_id"] for row in service_rows]
    if len(set(ids)) != len(ids) or len(archived) != len(archived_rows) or set(ids) != set(archived):
        raise ValueError("service input/archive must have matching unique demand IDs")
    gold = {}
    service_results = {}
    for name, parser in parsers.items():
        gold[name] = {
            "languageOnly": evaluate_gold(parser, gold_rows, service=False),
            "servicePolicy": evaluate_gold(parser, gold_rows, service=True),
        }
        results = []
        for row in service_rows:
            raw_consent = row["is_substitutable"].strip().lower()
            if raw_consent not in {"true", "false"}:
                raise ValueError("service input requires explicit true/false consent")
            archive = archived[row["demand_id"]]
            if row["category_id"] != archive["category_id"] or (
                raw_consent == "true" and row["extra_requirement"] != archive["extra_requirement"]
            ):
                raise ValueError("archived category/eligible requirement differs from input")
            result = parser.interpret(
                row["category_id"], row["extra_requirement"], is_substitutable=raw_consent == "true",
            )
            # JSON round trip also normalizes tuples for comparison to archived CSV JSON.
            results.append(meaning(json.loads(json.dumps(result.to_dict(), ensure_ascii=False))))
        service_results[name] = results
        print(json.dumps({"variant": name, "languageCorrect": gold[name]["languageOnly"]["correct"],
                          "serviceStatusCounts": dict(Counter(r["status"] for r in results))}), flush=True)
    summaries = {}
    changes = []
    for name, results in service_results.items():
        summaries[name] = {
            "statusCounts": dict(sorted(Counter(r["status"] for r in results).items())),
            "modeCounts": dict(sorted(Counter(r["mode"] for r in results).items())),
            "changedFromBefore": 0, "lostConditionRows": 0, "differentFromV046Archive": 0,
        }
    for index, row in enumerate(service_rows):
        baseline = service_results["before"][index]
        original = archived_meaning(archived[row["demand_id"]])
        case = {name: results[index] for name, results in service_results.items()}
        for name, result in case.items():
            summaries[name]["changedFromBefore"] += result != baseline
            summaries[name]["lostConditionRows"] += bool(condition_set(baseline) - condition_set(result))
            summaries[name]["differentFromV046Archive"] += result != original
        if any(result != baseline for result in case.values()) or baseline != original:
            changes.append({"demandId": row["demand_id"], "categoryId": row["category_id"],
                            "text": row["extra_requirement"], "archived": original, **case})
    report = {
        "scope": "HISTORICAL_DEVELOPMENT_REGRESSION_NOT_REAL_USER_ACCURACY",
        "externalLlmCalls": 0, "kiwipiepyVersion": version("kiwipiepy"),
        "rulesVersion": json.loads(args.rules.read_text(encoding="utf-8"))["version"],
        "categoryCodeContractIdentical": category_code_contract(before_taxonomy) == category_code_contract(taxonomy),
        "inputs": {name: {"path": str(path), "sha256": file_digest(path)}
                   for name, path in vars(args).items() if isinstance(path, Path) and name != "output"},
        "gold": gold,
        "service": {
            "rows": len(service_rows),
            "consentingNonemptyRows": sum(row["is_substitutable"].strip().lower() == "true" and bool(row["extra_requirement"].strip()) for row in service_rows),
            "variants": summaries, "changedCases": changes,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
