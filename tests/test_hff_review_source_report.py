from pathlib import Path

from scripts.reviews.build_hff_review_source_report import SOURCES, build_report


def test_source_preflight_has_at_least_ten_candidates() -> None:
    assert len(SOURCES) >= 10
    assert {row["decision"] for row in SOURCES} <= {"GREEN", "CONDITIONAL", "BLOCKED"}


def test_blocked_esther_is_not_pilotable() -> None:
    esther = next(row for row in SOURCES if row["source"] == "esthermall")
    assert esther["decision"] == "BLOCKED"
    assert esther["pilot_possible"] == "NO"


def test_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "sources.md"
    build_report(output)
    text = output.read_text(encoding="utf-8")
    for field in ("source", "review_exists", "robots_status", "terms_status", "pilot_possible", "decision"):
        assert field in text
