"""Inspect authorized local purchase/sales aggregate exports only."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ALIASES = {
    "period": ("년월", "period", "date"),
    "sido": ("시도", "sido", "region"),
    "sigungu": ("시군구", "sigungu"),
    "category_detail": ("상품 분류", "category_detail", "category"),
    "product_name": ("제품명", "product_name", "상품명"),
    "sales_count": ("판매건수", "sales_count"),
    "sales_amount": ("판매금액", "sales_amount", "구매금액"),
    "unit_price": ("판매단가", "unit_price"),
}


def normalize_aggregate(frame: pd.DataFrame, source_type: str) -> pd.DataFrame:
    frame = frame.fillna("")
    result = pd.DataFrame(index=frame.index)
    for target, names in ALIASES.items():
        matched = next((name for name in names if name in frame.columns), None)
        result[target] = frame[matched] if matched else ""
    result["source_type"] = source_type
    result["market_metric_type"] = result.apply(lambda row: "sales_count" if str(row.sales_count).strip() else "sales_amount" if str(row.sales_amount).strip() else "unknown", axis=1)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("foodpolis", "lg_uplus"), required=True)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    input_dir = args.input_dir or Path("data/raw/purchase") / args.source
    output = args.output or Path("data/processed/purchase") / f"{args.source}_aggregate.parquet"
    files = sorted([*input_dir.glob("*.csv"), *input_dir.glob("*.xlsx"), *input_dir.glob("*.xls")])
    if not files:
        print({"status": "WAITING_FOR_MANUAL_DOWNLOAD", "source": args.source, "input_dir": str(input_dir)})
        return 0
    path = files[0]
    frame = pd.read_excel(path, dtype=str) if path.suffix.lower() in {".xls", ".xlsx"} else pd.read_csv(path, dtype=str)
    source_type = "KOREAN_HFF_RETAIL_SALES" if args.source == "foodpolis" else "KOREAN_HFF_PURCHASE_AGGREGATE"
    normalized = normalize_aggregate(frame, source_type)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_parquet(output, index=False)
    normalized.to_csv(output.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    print({"status": "COMPLETED", "source": args.source, "rows": len(normalized), "columns": list(frame.columns), "output": str(output)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
