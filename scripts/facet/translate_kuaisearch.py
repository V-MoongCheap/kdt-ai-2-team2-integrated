"""Translate KuaiSearch health queries for downstream Korean Facet extraction.

Raw Chinese query text is never overwritten. The translated layer is a
derived, local-only artifact and must not be treated as ground truth.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd


def _translate_batch(rows: list[dict[str, str]], model: str, endpoint: str, timeout: int) -> list[dict[str, str]]:
    prompt = (
        "Translate each Chinese ecommerce query into natural Korean. "
        "Keep identifiers and the actual product type, including non-health products. "
        "Preserve product attributes and constraints; do not explain. Return JSON only "
        "as {\"translations\":[{\"source_record_id\":\"...\",\"query_translated\":\"...\"}]} "
        f"for every input row. Input: {json.dumps(rows, ensure_ascii=False)}"
    )
    body = json.dumps({"model": model, "prompt": prompt, "format": {"type": "object", "properties": {"translations": {"type": "array", "items": {"type": "object", "properties": {"source_record_id": {"type": "string"}, "query_translated": {"type": "string"}}, "required": ["source_record_id", "query_translated"]}}}, "required": ["translations"]}, "options": {"temperature": 0}, "stream": False, "think": False}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(f"{endpoint.rstrip('/')}/api/generate", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = json.loads(payload.get("response", "{}"))
    return result.get("translations", []) if isinstance(result, dict) else []


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate local KuaiSearch health queries into Korean")
    parser.add_argument("--input", type=Path, default=Path("data/interim/facet_evidence/kuaiseach_health_queries.parquet"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/facet_evidence/kuaiseach_health_queries_ko.parquet"))
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    frame = pd.read_parquet(args.input).fillna("")
    frame = frame.drop_duplicates(subset=["query_raw"]).reset_index(drop=True)
    if args.limit is not None:
        frame = frame.iloc[:args.limit].copy()
    previous = pd.read_parquet(args.output).fillna("") if args.output.exists() else pd.DataFrame()
    cache = dict(zip(previous.get("query_raw", []), previous.get("query_translated", []))) if not previous.empty else {}
    frame["query_translated"] = frame["query_raw"].map(cache).fillna("")
    frame["query_translated"] = frame["query_translated"].str.strip()
    pending_indices = frame.index[frame["query_translated"].eq("")].tolist()
    started = time.perf_counter(); calls = 0; failures = 0
    errors = []
    for start in range(0, len(pending_indices), args.batch_size):
        pending = frame.loc[pending_indices[start:start + args.batch_size]]
        if not pending.empty:
            calls += 1
            try:
                translated = _translate_batch([{"source_record_id": str(row.source_record_id), "query_raw": str(row.query_raw)} for row in pending.itertuples()], args.model, args.endpoint, args.timeout)
                lookup = {}
                expected = set(pending.source_record_id.astype(str))
                for item in translated:
                    record_id = str(item.get("source_record_id"))
                    value = item.get("query_translated")
                    if record_id not in expected or record_id in lookup:
                        raise ValueError("Unexpected or duplicate response ID")
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError("Empty or invalid translation")
                    lookup[record_id] = value.strip()
                for index, row in pending.iterrows():
                    if str(row.source_record_id) in lookup:
                        frame.at[index, "query_translated"] = lookup[str(row.source_record_id)]
                if expected - lookup.keys():
                    raise ValueError("Missing response IDs: " + ", ".join(sorted(expected - lookup.keys())))
            except Exception as exc:
                failures += 1
                errors.append({"source_record_ids": pending.source_record_id.astype(str).tolist(), "error": str(exc)})
                print({"batch_start": start, "error": str(exc)}, flush=True)
        frame.to_parquet(args.output, index=False)
        print({"translated": int(frame.query_translated.ne("").sum()), "rows": len(frame), "calls": calls, "failures": failures}, flush=True)
    frame.to_parquet(args.output, index=False)
    frame.to_csv(args.output.with_name(args.output.stem + "_preview.csv"), index=False, encoding="utf-8-sig")
    remaining = int(frame.query_translated.eq("").sum())
    report = {"status": "COMPLETED" if remaining == 0 else "COMPLETED_WITH_WARNINGS", "rows": len(frame), "translated": len(frame) - remaining, "remaining": remaining, "calls": calls, "failures": failures, "runtime_seconds": round(time.perf_counter() - started, 3), "model": args.model, "errors": errors}
    args.output.with_suffix(".report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
