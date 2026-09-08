"""Run deterministic review gates against Model 1 multi-source candidates."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from moongcheap_ai.data_foundation.model1_review import collapse_same_model_candidates, normalize_review_candidates, write_review_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/processed/model1_multisource_v1/multisource_model_candidates_v1.csv"))
    parser.add_argument("--input", type=Path, default=Path("data/processed/model1_multisource_v1/multisource_model_input_v1.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/model1_multisource_v1"))
    parser.add_argument("--refresh-review", action="store_true", help="rebuild the review CSV; otherwise reuse an existing open review file")
    args = parser.parse_args()
    reviewed_path = args.output_dir / "multisource_candidate_review_v1.csv"
    if args.refresh_review or not reviewed_path.exists():
        result = write_review_artifacts(args.candidates, args.input, args.output_dir)
    else:
        result = {"rows": len(pd.read_csv(reviewed_path)), "status_counts": "reused_existing_review"}
    normalized = normalize_review_candidates(pd.read_csv(reviewed_path).fillna(""))
    normalized = collapse_same_model_candidates(normalized)
    demand_constraints = normalized[normalized["canonical_facet_id"].eq("price_band")].copy()
    demand_constraints["finalization_status"] = "DEMAND_CONDITION"
    demand_constraints.to_csv(args.output_dir / "multisource_demand_constraints_v1.csv", index=False, encoding="utf-8-sig")
    facet_normalized = normalized[~normalized["canonical_facet_id"].eq("price_band")].copy()
    facet_path = args.output_dir / "multisource_candidate_normalized_v1.csv"
    try:
        facet_normalized.to_csv(facet_path, index=False, encoding="utf-8-sig")
    except PermissionError:
        facet_path = args.output_dir / "multisource_candidate_normalized_product_only_v1.csv"
        facet_normalized.to_csv(facet_path, index=False, encoding="utf-8-sig")
    lines = [
        "# Multi-source Facet 후보 정규화 V1", "",
        "검토 후보를 비교·검토 가능한 원자 값과 구조화 필드로 분리한 산출물이다.",
        "정규화는 후보를 자동 확정하지 않으며 `finalization_status`를 함께 확인해야 한다.", "",
        "## 주요 상태", "",
        "- `ACCEPT_CANDIDATE`: 기본 검토 게이트를 통과한 후보",
        "- `REVIEW_REQUIRED`: 정규화됐지만 사람 검토가 필요한 후보",
        "- `EVIDENCE_ONLY`: MFDS 규제 기능 원문으로만 보존할 후보",
        "- `REJECT`: 범위 이탈 또는 근거 부족으로 제외할 후보", "",
        f"상품 Facet 정규화 행: {len(facet_normalized):,}",
        f"Demand 가격 조건 행: {len(demand_constraints):,}",
        "가격대는 상품 Facet에 포함하지 않고 별도 Demand 조건으로 보존"
    ]
    (args.output_dir / "multisource_candidate_normalized_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(result | {"normalized_rows": len(normalized)})


if __name__ == "__main__":
    main()
