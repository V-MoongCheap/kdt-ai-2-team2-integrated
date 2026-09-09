"""Report verified and pending Korean HFF purchase/sales evidence sources."""

from __future__ import annotations

import argparse
from pathlib import Path


SOURCES = [
    {"source": "Foodpolis / 식품정보24", "basis": "공식 소매채널 판매정보 대시보드", "hff_separable": "YES", "access": "MANUAL_DOWNLOAD", "cost": "UNKNOWN", "status": "WAITING_FOR_MANUAL_DOWNLOAD", "next_step": "공식 계정으로 Export 파일을 내려받아 data/raw/purchase/foodpolis/에 보관"},
    {"source": "LG U+ 건강기능식품 융합데이터", "basis": "공개 소개자료에서 시장지표가 언급되었으나 검증된 다운로드 URL/파일 미확인", "hff_separable": "UNKNOWN", "access": "NOT_VERIFIED", "cost": "FREE_ONLY", "status": "MISSING_VALID_SOURCE", "next_step": "공식 무료 파일 또는 API URL을 확인하기 전에는 사용하지 않음"},
    {"source": "공공데이터포털 / FIS / 연구자료", "basis": "후보 탐색 대상이나 Product-level HFF 구매·판매 원자료는 현재 로컬 검증 없음", "hff_separable": "UNKNOWN", "access": "SEARCH_REQUIRED", "cost": "FREE_ONLY", "status": "NOT_VERIFIED", "next_step": "원자료·분류 기준·재사용 조건을 확인한 뒤 등록"},
]


def build_report(output: Path) -> dict[str, int]:
    lines = ["# 한국 건강기능식품 Purchase/Sales Evidence Sources", "", "이 보고서는 실제 구매·판매 기반 근거와 단순 생산량·검색순위·시장 기사 자료를 구분한다. 검증 전 자료는 파이프라인에 넣지 않는다.", "", "| Source | Basis | HFF 분리 | Access | Cost | Status | Next Step |", "|---|---|---|---|---|---|---|"]
    for row in SOURCES:
        lines.append("| " + " | ".join(row.values()) + " |")
    lines += ["", "## 현재 판정", "- 검증 완료된 Product-level 또는 Category-level 구매/판매 원자료: 0개.", "- Foodpolis는 공식 수동 Export 파일을 받기 전까지 `WAITING_FOR_MANUAL_DOWNLOAD`으로 유지한다.", "- LG U+ 자료는 확인 가능한 공식 다운로드 파일이 없어 `MISSING_VALID_SOURCE`로 유지한다.", "- 생산실적, 일반 시장규모, 검색·클릭 비율은 구매/판매 evidence로 승격하지 않는다.", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return {"source_count": len(SOURCES), "verified_source_count": sum(row["status"] == "VERIFIED" for row in SOURCES)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/purchase_evidence_sources.md"))
    args = parser.parse_args()
    print(build_report(args.output))
