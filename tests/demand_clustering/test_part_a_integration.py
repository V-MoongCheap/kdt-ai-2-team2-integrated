import json
from pathlib import Path

import pandas as pd
import pytest

from moongcheap_ai.demand_clustering.label_diagnostics import inspect_label
from moongcheap_ai.demand_clustering.part_a_integration import (
    build_part_b_parser,
    validate_profile_versions,
)

ROOT = Path(__file__).resolve().parents[2]
CATEGORY = "health-functional-food:probiotics"


@pytest.fixture(scope="module")
def taxonomy():
    return json.loads((ROOT / "config/facet_taxonomy_v2_2.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parser(taxonomy):
    original = json.dumps(taxonomy, sort_keys=True)
    parser, summary = build_part_b_parser(
        taxonomy,
        rules_path=ROOT / "config/demand_constraint_rules.json",
        aliases_path=ROOT / "config/model1_aliases_reviewed_v2.json",
        compatibility_aliases_path=ROOT / "config/demand_constraint_aliases.json",
    )
    assert json.dumps(taxonomy, sort_keys=True) == original
    assert summary["primaryAliasVersion"] == "model1-reviewed-aliases-v2"
    assert summary["compatibilityAliasStatus"] == "EXPERIMENTAL_DEVELOPMENT"
    return parser


@pytest.mark.parametrize("text,expected", [
    ("가루면 좋겠어요.", {("product_form", 1)}),
    ("알약 제품이면 좋겠어요.", {("product_form", 2)}),
    ("하루 한 번 먹는 제품이면 좋겠어요.", {("daily_frequency", 1)}),
    ("하루 두 번 먹는 제품이면 좋겠어요.", {("daily_frequency", 2)}),
    ("분말이면서 하루 한 번 먹는 제품이면 좋겠어요.", {("product_form", 1), ("daily_frequency", 1)}),
    ("프로바이오틱스와 아연이면 좋겠어요.", {("functional_ingredients", 4)}),
])
def test_approved_forms_and_existing_b_conditions(parser, text, expected):
    result = parser.interpret(CATEGORY, text, is_substitutable=True)
    assert result.status == "PARSED"
    assert {(c.facet_name, c.value_code) for c in result.constraints} == expected


def test_constraint_types_and_alternative_group_survive(parser):
    excluded = parser.interpret(CATEGORY, "분말은 제외해주세요.", is_substitutable=True)
    assert excluded.constraints[0].constraint_type == "EXCLUDE"
    required = parser.interpret(CATEGORY, "반드시 분말 제품으로 부탁해요.", is_substitutable=True)
    assert required.constraints[0].constraint_type == "MUST"
    alternative = parser.interpret(CATEGORY, "분말 또는 캡슐도 괜찮아요.", is_substitutable=True)
    assert len(alternative.preference_groups) == 1
    assert alternative.preference_groups[0].operator == "ANY_OF"


def test_primary_alias_wins_over_conflicting_b_compatibility(taxonomy, tmp_path):
    compatibility = tmp_path / "compat.json"
    compatibility.write_text(json.dumps({"aliases": [{
        "facet_name": "product_form", "canonical_value": "분말", "surfaces": ["알약"],
    }]}))
    parser, _ = build_part_b_parser(
        taxonomy,
        rules_path=ROOT / "config/demand_constraint_rules.json",
        aliases_path=ROOT / "config/model1_aliases_reviewed_v2.json",
        compatibility_aliases_path=compatibility,
    )
    result = parser.interpret(CATEGORY, "알약 제품이면 좋겠어요.", is_substitutable=True)
    assert [(c.value_code, c.value) for c in result.constraints] == [(2, "캡슐")]


def test_mixed_profile_versions_are_rejected(taxonomy):
    with pytest.raises(ValueError, match="do not match v2.2"):
        validate_profile_versions(pd.DataFrame({"taxonomy_version": ["v2.2", "v2.1"]}), taxonomy)
    assert validate_profile_versions(pd.DataFrame({"taxonomy_version": ["v2.2"]}), taxonomy) == "v2.2"


@pytest.mark.parametrize("label,status", [
    (None, "MISSING"), ("", "MISSING"), ("0-0-0", "VALID_CATEGORY_LOCAL"),
    ("1-0-0", "VALID_CATEGORY_LOCAL"), ("1-0", "INVALID_FORMAT"),
    ("powder-0-0", "INVALID_FORMAT"), ("999-0-0", "UNKNOWN_VALUE_CODE"),
])
def test_label_is_decoded_only_with_its_category(taxonomy, label, status):
    category = next(c for c in taxonomy["categories"] if c["category_id"] == CATEGORY)
    result = inspect_label(label, category)
    assert result["status"] == status
    if label == "1-0-0":
        assert result["facetValues"]["product_form"] == {"code": 1, "value": "분말"}
