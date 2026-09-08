"""Deterministic review gates for multi-source Model 1 facet candidates."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


FACET_MAP = {
    "product form": ("product_form", "PRODUCT"),
    "제품 형태": ("product_form", "PRODUCT"),
    "functional ingredients": ("functional_ingredients", "PRODUCT"),
    "기능성 성분": ("functional_ingredients", "PRODUCT"),
    "regulated function": ("regulated_function", "EVIDENCE_ONLY"),
    "규제 기능": ("regulated_function", "EVIDENCE_ONLY"),
    "intake method": ("intake_method", "PRODUCT"),
    "섭취 방법": ("intake_method", "PRODUCT"),
    "price band": ("price_band", "DEMAND"),
    "가격대": ("price_band", "DEMAND"),
    "consumer preference": ("consumer_preference", "DEMAND_SIGNAL"),
    "purchase intent": ("purchase_intent", "DEMAND_SIGNAL"),
}

FORM_MAP = {
    "powder": "powder", "분말": "powder",
    "tablet": "tablet", "정": "tablet", "정제": "tablet",
    "capsule": "capsule", "캡슐": "capsule",
    "liquid": "liquid", "액상": "liquid",
    "stick": "stick", "스틱": "stick",
}

OUT_OF_SCOPE = (
    "약", "의약", "치료", "질환", "처방", "알레르기", "하이드로겔", "에센스",
    "medicine", "drug", "treatment", "cosmetic",
)
RAW_SENTENCE_MARKERS = ("도움을 줄", "유지하는데", "가장 좋은", "필요", "추천")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip().casefold()


def normalize_value(facet_id: str, value: Any) -> str:
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip()
    if facet_id == "product_form":
        return FORM_MAP.get(text.casefold(), text)
    if facet_id == "functional_ingredients":
        text = re.sub(r"\s*\((?:또는|or)\s*[^)]*\)", "", text, flags=re.I)
        text = re.sub(r"\s*\([^)]*(?:기능성|기능[_ -]?\d{4}|생리활성)[^)]*\)", "", text, flags=re.I)
    if facet_id == "regulated_function":
        text = re.sub(r"\s*\([^)]*\)", "", text)
    return text


def _contains(haystack: Any, needle: str) -> bool:
    return bool(needle) and needle in normalize_text(haystack)


def review_candidates(candidates: pd.DataFrame, inputs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    input_frame = inputs.fillna("").copy()
    text_columns = [
        column for column in (
            "product_name", "product_form", "functional_ingredients", "regulated_function",
            "intake_method", "price_text", "quantity_text", "seller_condition", "evidence_text",
        ) if column in input_frame.columns
    ]
    for _, candidate in candidates.fillna("").iterrows():
        raw_name = str(candidate.get("name", ""))
        name_key = normalize_text(raw_name)
        facet_id, scope = FACET_MAP.get(name_key, (name_key.replace(" ", "_"), "UNKNOWN"))
        raw_value = str(candidate.get("value", ""))
        normalized = normalize_value(facet_id, raw_value)
        category = str(candidate.get("category_key", ""))
        category_rows = input_frame[input_frame.get("category_key", pd.Series(dtype=str)).eq(category)]
        matching_rows = category_rows[category_rows[text_columns].astype(str).apply(
            lambda column: column.map(lambda value: _contains(value, normalize_text(raw_value)))
        ).any(axis=1)] if text_columns and not category_rows.empty else category_rows.iloc[0:0]
        evidence_text = str(candidate.get("source_text", ""))
        evidence_matches = _contains(evidence_text, normalize_text(raw_value))
        reasons: list[str] = []
        status = "ACCEPT_CANDIDATE"
        if scope == "UNKNOWN":
            status = "REVIEW_REQUIRED"
            reasons.append("unrecognized_facet")
        if not normalized:
            status = "REJECT"
            reasons.append("empty_value")
        if any(token in normalize_text(raw_value) for token in OUT_OF_SCOPE):
            status = "REJECT"
            reasons.append("out_of_scope_product_or_treatment_term")
        if any(marker in raw_value for marker in RAW_SENTENCE_MARKERS):
            status = "REVIEW_REQUIRED" if status != "REJECT" else status
            reasons.append("raw_natural_language_sentence")
        if scope == "EVIDENCE_ONLY":
            status = "REVIEW_REQUIRED" if status != "REJECT" else status
            reasons.append("regulated_function_is_evidence_only")
        if scope == "DEMAND" or scope == "DEMAND_SIGNAL":
            status = "REVIEW_REQUIRED" if status != "REJECT" else status
            reasons.append("demand_signal_not_product_facet")
        if facet_id == "intake_method":
            status = "REVIEW_REQUIRED" if status != "REJECT" else status
            reasons.append("requires_structured_intake_parser")
        if not evidence_matches:
            status = "REVIEW_REQUIRED" if status != "REJECT" else status
            reasons.append("evidence_text_mismatch")
        if len(matching_rows) == 0:
            status = "REJECT" if status != "REJECT" else status
            reasons.append("no_matching_input_row")
        elif len(matching_rows) < 2 and status == "ACCEPT_CANDIDATE":
            status = "REVIEW_REQUIRED"
            reasons.append("single_observed_input_row")
        rows.append({
            **candidate.to_dict(),
            "canonical_facet_id": facet_id,
            "normalized_value": normalized,
            "review_scope": scope,
            "input_match_count": int(len(matching_rows)),
            "evidence_text_matches_value": bool(evidence_matches),
            "review_status": status,
            "review_reasons": "|".join(dict.fromkeys(reasons)) or "passes_basic_gates",
        })
    return pd.DataFrame(rows)


def write_review_artifacts(candidates_path: Path, input_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(candidates_path).fillna("")
    inputs = pd.read_json(input_path, lines=True).fillna("")
    reviewed = review_candidates(candidates, inputs)
    reviewed_path = output_dir / "multisource_candidate_review_v1.csv"
    reviewed.to_csv(reviewed_path, index=False, encoding="utf-8-sig")
    summary = reviewed.groupby(["review_status", "review_scope"], dropna=False).size().reset_index(name="rows") if not reviewed.empty else pd.DataFrame(columns=["review_status", "review_scope", "rows"])
    summary.to_csv(output_dir / "multisource_candidate_review_summary_v1.csv", index=False, encoding="utf-8-sig")
    lines = [
        "# Multi-source Facet 후보 자동 검토 V1", "",
        "모델 출력 후보를 원본 입력과 대조한 결정론적 1차 검토 결과다.",
        "ACCEPT_CANDIDATE는 기본 게이트 통과 후보이며 최종 Taxonomy 확정을 뜻하지 않는다.", "",
        "## 상태별 건수", "", "| 상태 | 건수 |", "|---|---:|",
    ]
    for status, count in reviewed["review_status"].value_counts().items() if not reviewed.empty else []:
        lines.append(f"| {status} | {int(count)} |")
    lines += ["", "## 검토 기준", "", "- 후보 값이 같은 Category의 입력 행에 실제로 나타나는지 확인", "- 증거 원문과 후보 값의 일치 여부 확인", "- 규제 기능은 근거로만 보존하고 상품 Facet으로 자동 확정하지 않음", "- 가격대·구매 의도는 Demand 신호로 분리", "- 의약품·치료·화장품 범위 이탈 표현은 제외", "- 섭취 방법은 구조화 파서 검토 대상으로 보냄"]
    (output_dir / "multisource_candidate_review_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"rows": len(reviewed), "status_counts": reviewed["review_status"].value_counts().to_dict() if not reviewed.empty else {}}
