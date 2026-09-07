"""Repair flagged translations with checkpoints and an immutable source snapshot."""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from audit_kuaisearch_translation import screen
from translate_kuaisearch import GLOSSARY, _translate_batch, normalize_translation


def quality_flags(raw, translated):
    flags = [flag for flag in screen(raw, translated)[0].split("|") if flag]
    for word, meanings in GLOSSARY.items():
        if word in raw and not any(meaning in translated for meaning in meanings):
            flags.append("TERM_MISMATCH:" + word)
    return flags


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def checkpoint(frame, output):
    temporary = output.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary, index=False)
    # Windows readers can briefly hold the destination open during inspection.
    for attempt in range(6):
        try:
            temporary.replace(output)
            break
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.2 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/interim/facet_evidence/kuaiseach_health_queries_ko.parquet"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/facet_evidence/kuaiseach_health_queries_ko_v2.parquet"))
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--priority-source-ids", default="", help="Comma-separated source IDs to process first")
    parser.add_argument("--finalize-only", action="store_true", help="Export checkpoint reports without calling a model")
    args = parser.parse_args()
    if args.model.startswith("translategemma:"):
        args.batch_size = 1
    if args.input.resolve() == args.output.resolve():
        parser.error("Use a separate output to preserve original translations")
    if args.batch_size < 1 or args.passes < 1 or (args.limit is not None and args.limit < 1):
        parser.error("batch-size, passes and limit must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
    metadata = args.output.with_suffix(".metadata.json")
    if args.output.exists():
        previous_meta = json.loads(metadata.read_text(encoding="utf-8"))
        if previous_meta["source_sha256"] != source_hash:
            raise ValueError("Source snapshot changed; use a new output")
        frame = pd.read_parquet(args.output).fillna("")
    else:
        frame = pd.read_parquet(args.input).fillna("")
        frame["translation_original"] = frame.query_translated
        frame["repair_status"] = "NOT_REPROCESSED"
        frame["repair_model"] = ""
        frame["repair_flags"] = ""
        frame["repair_candidate"] = ""
        frame["repair_attempts"] = 0
        write_json(metadata, {"version": "translation_repair_v2", "source_sha256": source_hash, "source": str(args.input), "accuracy": None})
    flags = [quality_flags(str(row.query_raw), str(row.query_translated)) for row in frame.itertuples()]
    frame["repair_flags"] = ["|".join(value) for value in flags]
    candidates = [index for index, value in enumerate(flags) if value]
    # Correct known term errors and placeholders first; ambiguous names remain reviewable.
    priority_ids = set(args.priority_source_ids.split(",")) - {""}
    candidates.sort(key=lambda i: (str(frame.at[i, "source_record_id"]) not in priority_ids, not any(flag.startswith("TERM_MISMATCH") for flag in flags[i]), "PLACEHOLDER" not in flags[i], i))
    selected = candidates[:args.limit] if args.limit else candidates
    no_text = [i for i in selected if not re.search(r"[\w]", str(frame.at[i, "query_raw"]))]
    frame.loc[no_text, "repair_status"] = "SOURCE_NONLEXICAL_REVIEW"
    nonlexical_indices = set(no_text)
    pending = [i for i in selected if i not in nonlexical_indices]
    started = time.perf_counter()
    calls = failures = consecutive_errors = 0
    journal = args.output.with_suffix(".attempts.jsonl")
    for pass_number in range(0 if args.finalize_only else args.passes):
        batch_size = args.batch_size if pass_number == 0 else 1
        retry = []
        for start in range(0, len(pending), batch_size):
            indexes = pending[start:start + batch_size]
            rows = [{"source_record_id": str(i), "query_raw": str(frame.at[i, "query_raw"])} for i in indexes]
            calls += 1
            call_start = time.perf_counter()
            error = ""
            result = []
            try:
                result = _translate_batch(rows, args.model, args.endpoint, args.timeout)
                if not isinstance(result, list):
                    raise ValueError("translations must be a list")
                lookup = {}
                for item in result:
                    key = item.get("source_record_id")
                    if key not in {row["source_record_id"] for row in rows} or key in lookup:
                        raise ValueError("Unexpected or duplicate response ID")
                    lookup[key] = item.get("query_translated")
            except Exception as exc:
                error = str(exc)
                lookup = {}
            consecutive_errors = consecutive_errors + 1 if error else 0
            rejected = []
            for i in indexes:
                frame.at[i, "repair_attempts"] = int(frame.at[i, "repair_attempts"]) + 1
                value = lookup.get(str(i))
                normalized = normalize_translation(str(frame.at[i, "query_raw"]), value.strip())[0] if isinstance(value, str) else ""
                new_flags = quality_flags(str(frame.at[i, "query_raw"]), normalized) if isinstance(value, str) else ["MISSING_RESPONSE"]
                frame.at[i, "repair_candidate"] = normalized
                frame.at[i, "repair_model"] = args.model
                if not error and not new_flags:
                    frame.at[i, "query_translated"] = normalized
                    frame.at[i, "repair_status"] = "AUTOMATED_CHECKS_PASSED"
                    frame.at[i, "repair_flags"] = ""
                else:
                    frame.at[i, "repair_status"] = "NEEDS_REVIEW"
                    rejected.append({"row": i, "flags": new_flags})
                    retry.append(i)
            if error or rejected:
                failures += 1
            with journal.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"model": args.model, "rows": indexes, "response": result, "error": error, "rejected": rejected, "runtime_seconds": round(time.perf_counter() - call_start, 3)}, ensure_ascii=False) + "\n")
            checkpoint(frame, args.output)
            progress = {"status": "RUNNING", "updated_at": datetime.now(timezone.utc).isoformat(), "pass": pass_number + 1, "processed": min(start + batch_size, len(pending)), "pass_rows": len(pending), "calls": calls, "repaired_total": int(frame.repair_status.eq("AUTOMATED_CHECKS_PASSED").sum()), "remaining_flagged": int(frame.repair_flags.ne("").sum()), "runtime_seconds": round(time.perf_counter() - started, 3)}
            write_json(args.output.with_suffix(".progress.json"), progress)
            print(progress, flush=True)
            if consecutive_errors >= 3:
                break
        pending = retry
        if not pending or consecutive_errors >= 3:
            break
    checkpoint(frame, args.output)
    review = frame[frame.repair_flags.ne("")]
    review.to_csv(args.output.with_suffix(".review.csv"), index=False, encoding="utf-8-sig")
    frame[frame.repair_status.eq("AUTOMATED_CHECKS_PASSED")].to_csv(args.output.with_suffix(".changes.csv"), index=False, encoding="utf-8-sig")
    report = {"status": "CHECKPOINT_EXPORTED" if args.finalize_only else "COMPLETED_WITH_REVIEW" if len(review) else "AUTOMATED_CHECKS_PASSED", "rows": len(frame), "selected": len(selected), "repaired_total": int(frame.repair_status.eq("AUTOMATED_CHECKS_PASSED").sum()), "remaining_flagged": len(review), "source_nonlexical": len(no_text), "calls": calls, "failed_or_rejected_batches": failures, "runtime_seconds": round(time.perf_counter() - started, 3), "model": args.model, "accuracy": None}
    write_json(args.output.with_suffix(".report.json"), report)
    write_json(args.output.with_suffix(".progress.json"), report)
    print(report, flush=True)


if __name__ == "__main__":
    main()
