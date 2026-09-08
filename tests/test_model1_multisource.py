import importlib.util
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "model1" / "run_multisource_facet_discovery.py"
SPEC = importlib.util.spec_from_file_location("model1_multisource", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _input_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "category_key": "health-functional-food:probiotics",
                "category_name": "유산균·프로바이오틱스",
                "source_product_id": "mfds:p1",
                "product_name": "유산균 캡슐",
                "source_category": "프로바이오틱스",
                "product_form": "캡슐",
                "functional_ingredients": "프로바이오틱스",
                "regulated_function": "",
                "intake_method": "",
                "sampling_reason": "test",
                "source_type": "MFDS_PRODUCT",
                "price_text": "",
                "quantity_text": "",
                "seller_condition": "",
                "evidence_text": "유산균 캡슐",
            },
            {
                "category_key": "health-functional-food:probiotics",
                "category_name": "유산균·프로바이오틱스",
                "source_product_id": "seller:s1",
                "product_name": "유산균 캡슐 판매 공고",
                "source_category": "건강식품",
                "product_form": "캡슐",
                "functional_ingredients": "프로바이오틱스",
                "regulated_function": "",
                "intake_method": "",
                "sampling_reason": "test",
                "source_type": "SELLER_LISTING",
                "price_text": "12000",
                "quantity_text": "2",
                "seller_condition": "",
                "evidence_text": "유산균 캡슐 판매 공고",
            },
        ]
    )


def test_reasoned_output_keeps_reason_and_source_type():
    payload = {
        "category_key": "health-functional-food:probiotics",
        "category_name": "유산균·프로바이오틱스",
        "facets": [
            {
                "facet_id_candidate": "product_form",
                "name": "Product Form",
                "definition": "제형",
                "reason": "상품 데이터와 판매 공고에서 반복되어 구매 비교에 사용할 수 있습니다.",
                "values": [{"value": "캡슐", "aliases": []}],
                "evidence": [{"source_product_id": "mfds:p1", "source_field": "product_form", "source_text": "캡슐"}],
            }
        ],
    }

    parsed, failures = MODULE.parse_reasoned_output(payload, _input_frame())

    assert not failures
    assert parsed.iloc[0]["reason_status"] == "PRESENT"
    assert parsed.iloc[0]["evidence_source_type"] == "MFDS_PRODUCT"


def test_selection_requires_model_and_source_consensus():
    base = MODULE.parse_reasoned_output(
        {
            "category_key": "health-functional-food:probiotics",
            "category_name": "유산균·프로바이오틱스",
            "facets": [
                {
                    "name": "Product Form",
                    "definition": "제형",
                    "reason": "반복 관찰",
                    "values": [{"value": "캡슐", "aliases": []}],
                    "evidence": [{"source_product_id": "mfds:p1", "source_field": "product_form", "source_text": "캡슐"}],
                }
            ],
        },
        _input_frame(),
    )[0]
    candidate = pd.concat([base.assign(model="qwen3:4b"), base.assign(model="gemma3:4b", source_product_id="seller:s1", evidence_source_type="SELLER_LISTING")], ignore_index=True)

    selected = MODULE.select_candidates(candidate)

    assert selected.iloc[0]["selection_status"] == "SELECTED_CANDIDATE"
    assert selected.iloc[0]["model_support"] == 2
    assert selected.iloc[0]["source_type_count"] == 2
