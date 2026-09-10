"""Compare historical B aliases, A-only aliases, and B's V2.2 compatibility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from moongcheap_ai.demand_constraints import DemandConstraintParser
from moongcheap_ai.demand_clustering.part_a_integration import build_part_b_parser


def signature(result):
    payload = result.to_dict()
    def condition(item):
        return {k: item[k] for k in ("facet_name", "value_code", "constraint_type")}
    return {
        "status": payload["status"],
        "mode": payload["effective_requirement_mode"],
        "constraints": [condition(c) for c in payload["constraints"]],
        "preferenceGroups": [
            {"operator": g["operator"], "aggregation": g["aggregation"],
             "members": [condition(c) for c in g["members"]]}
            for g in payload["preference_groups"]
        ],
    }


def lost_conditions(before, after):
    def atoms(result):
        conditions = result["constraints"] + [c for g in result["preferenceGroups"] for c in g["members"]]
        return {json.dumps(c, sort_keys=True) for c in conditions}
    return [json.loads(raw) for raw in sorted(atoms(before) - atoms(after))]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input", nargs="+", type=Path, required=True)
    cli.add_argument("--baseline-taxonomy", type=Path)
    cli.add_argument("--taxonomy", type=Path, default=Path("config/facet_taxonomy_v2_2.json"))
    cli.add_argument("--rules", type=Path, default=Path("config/demand_constraint_rules.json"))
    cli.add_argument("--aliases", type=Path, default=Path("config/model1_aliases_reviewed_v2.json"))
    cli.add_argument("--compatibility-aliases", type=Path, default=Path("config/demand_constraint_aliases.json"))
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
    before_taxonomy = json.loads((args.baseline_taxonomy or args.taxonomy).read_text(encoding="utf-8"))
    before = DemandConstraintParser.from_taxonomy(
        before_taxonomy, rules_path=args.rules, aliases_path=args.compatibility_aliases,
    )
    a_only, _ = build_part_b_parser(taxonomy, rules_path=args.rules, aliases_path=args.aliases)
    after, artifact_summary = build_part_b_parser(
        taxonomy, rules_path=args.rules, aliases_path=args.aliases,
        compatibility_aliases_path=args.compatibility_aliases,
    )
    rows = []
    for source in args.input:
        for index, row in pd.read_csv(source, dtype=str, keep_default_na=False).iterrows():
            text = row["extra_requirement"]
            category = row["category_id"]
            raw_consent = row.get("is_substitutable", "true").strip().lower()
            if raw_consent not in {"true", "false"}:
                raise ValueError("comparison input requires true/false is_substitutable")
            results = [signature(p.interpret(category, text, is_substitutable=raw_consent == "true")) for p in (before, a_only, after)]
            rows.append({
                "source": str(source), "caseId": row.get("sample_id", row.get("case_id", str(index))),
                "categoryId": category, "text": text,
                "before": results[0], "aOnly": results[1], "after": results[2],
                "aOnlyLostConditions": lost_conditions(results[0], results[1]),
                "afterLostConditions": lost_conditions(results[0], results[2]),
                "afterChanged": results[0] != results[2],
            })
    summary = {
        "rows": len(rows),
        "aOnlyLostConditionRows": sum(bool(r["aOnlyLostConditions"]) for r in rows),
        "afterLostConditionRows": sum(bool(r["afterLostConditions"]) for r in rows),
        "afterChangedRows": sum(r["afterChanged"] for r in rows),
        "interpretationOnly": True,
        "externalLlmCalls": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"summary": summary, "artifacts": artifact_summary, "cases": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
