import pandas as pd

from moongcheap_ai.data_foundation.model1_review import normalize_review_candidates, review_candidates


def _inputs() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "category_key": "health-functional-food:skin_collagen",
            "source_product_id": "p1",
            "product_form": "분말",
            "functional_ingredients": "콜라겐",
            "regulated_function": "피부 건강에 도움을 줄 수 있음",
            "intake_method": "1일 1회 1포",
            "price_text": "UNDER_10000",
            "evidence_text": "분말 콜라겐",
        },
        {
            "category_key": "health-functional-food:skin_collagen",
            "source_product_id": "p2",
            "product_form": "분말",
            "functional_ingredients": "콜라겐",
            "regulated_function": "피부 건강에 도움을 줄 수 있음",
            "intake_method": "1일 1회 1포",
            "price_text": "UNDER_10000",
            "evidence_text": "분말 콜라겐",
        },
    ])


def _candidate(name: str, value: str, source_text: str = "") -> pd.DataFrame:
    return pd.DataFrame([{
        "category_key": "health-functional-food:skin_collagen",
        "name": name,
        "value": value,
        "source_text": source_text,
        "source_product_id": "p1",
    }])


def test_product_form_with_repeated_input_evidence_passes():
    result = review_candidates(_candidate("Product Form", "분말", "분말"), _inputs())
    row = result.iloc[0]
    assert row.review_status == "ACCEPT_CANDIDATE"
    assert row.canonical_facet_id == "product_form"
    assert row.normalized_value == "powder"
    assert row.input_match_count == 2


def test_regulated_function_is_review_only():
    result = review_candidates(_candidate("Regulated Function", "피부 건강에 도움을 줄 수 있음", "피부 건강에 도움을 줄 수 있음"), _inputs())
    assert result.iloc[0].review_status == "REVIEW_REQUIRED"
    assert "regulated_function_is_evidence_only" in result.iloc[0].review_reasons


def test_out_of_scope_search_term_is_rejected():
    result = review_candidates(_candidate("Consumer Preference", "피부 알레르기 약", "피부 알레르기 약"), _inputs())
    assert result.iloc[0].review_status == "REJECT"
    assert "out_of_scope_product_or_treatment_term" in result.iloc[0].review_reasons


def test_price_is_demand_scope_and_not_product_facet():
    result = review_candidates(_candidate("Price Band", "UNDER_10000", "UNDER_10000"), _inputs())
    assert result.iloc[0].review_scope == "DEMAND"
    assert result.iloc[0].review_status == "REVIEW_REQUIRED"


def test_ingredient_recognition_number_is_separated():
    reviewed = review_candidates(
        _candidate("Functional Ingredients", "AP \ucf5c\ub77c\uac94 \ud6a8\uc18c\ubd84\ud574 \ud3a9\ud0c0\uc774\ub4dc(\uae30\ub2a5\uc131\uc6d0\ub8cc\uc778\uc815\uc81c2010-25\ud638)", "AP \ucf5c\ub77c\uac94"),
        _inputs(),
    )
    normalized = normalize_review_candidates(reviewed)
    assert normalized.iloc[0].recognition_number == "2010-25"
    assert "2010-25" not in normalized.iloc[0].normalized_atom


def test_intake_is_split_into_structured_fields():
    reviewed = review_candidates(_candidate("Intake Method", "1일 2회", "1일 2회"), _inputs())
    normalized = normalize_review_candidates(reviewed)
    assert normalized.iloc[0].intake_days == "1"
    assert normalized.iloc[0].intake_frequency == "2"
