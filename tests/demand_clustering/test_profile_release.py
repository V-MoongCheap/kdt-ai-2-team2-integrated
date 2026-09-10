import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from moongcheap_ai.demand_clustering.evaluation.profile_release import prepare_profile_release

ROOT = Path(__file__).resolve().parents[2]


def source_files(tmp_path):
    target = ROOT / "config/facet_taxonomy_v2_2.json"
    taxonomy = json.loads(target.read_text(encoding="utf-8"))
    taxonomy["version"] = "v2.1-provisional"
    source = tmp_path / "v21.json"
    source.write_text(json.dumps(taxonomy))
    profiles = tmp_path / "profiles.csv"
    pd.DataFrame([{
        "catalog_id": "123", "product_name": "검증용 상품",
        "service_category_id": "health-functional-food:probiotics",
        "taxonomy_version": "v2.1", "product_form": "분말",
        "functional_ingredients_json": '["프로바이오틱스"]',
        "main_functionality_claim_ids_json": '["probiotics"]',
        "main_functionality_claim_texts_json": '["장 건강"]',
        "intake_method_text": "1일 1회", "profile_status": "EVIDENCE_READY",
    }]).to_csv(profiles, index=False)
    return profiles, source, target


def test_release_preserves_ids_evidence_and_source_files(tmp_path):
    profiles, source, target = source_files(tmp_path)
    original = profiles.read_bytes()
    output = tmp_path / "release"
    result = prepare_profile_release(profiles, source, target, output)
    assert result["taxonomyVersion"] == "v2.2"
    assert result["changedRuntimeProfiles"] == 0
    assert profiles.read_bytes() == original
    before = pd.read_csv(profiles, dtype=str)
    after = pd.read_csv(output / "catalog_profiles.csv", dtype=str)
    assert after.taxonomy_version.tolist() == ["v2.2"]
    pd.testing.assert_frame_equal(before.drop(columns="taxonomy_version"), after.drop(columns="taxonomy_version"))
    assert (output / "taxonomy.json").read_bytes() == target.read_bytes()
    with pytest.raises(ValueError, match="refusing to overwrite"):
        prepare_profile_release(profiles, source, target, output)


def test_release_rejects_changed_category_local_codebook(tmp_path):
    profiles, source, target = source_files(tmp_path)
    taxonomy = json.loads(source.read_text(encoding="utf-8"))
    taxonomy["categories"][0]["facets"][0]["values"][1]["value"] = "다른 값"
    source.write_text(json.dumps(taxonomy))
    with pytest.raises(ValueError, match="codes or values changed"):
        prepare_profile_release(profiles, source, target, tmp_path / "release")
    assert not (tmp_path / "release").exists()


def test_new_profile_generator_reads_taxonomy_version_and_preserves_source_ids(tmp_path, monkeypatch):
    from scripts.evaluation.build_catalog_wide_mfds_profiles import main

    datasets = {
        "category-mapping": [{"source_product_id": "mfds-1", "service_category_candidate_key": "RED_GINSENG"}],
        "products": [{
            "source_product_id": "mfds-1", "name": "홍삼 완제품", "product_type": "홍삼",
            "product_form": "액상", "main_functionality": "면역력 증진에 도움을 줄 수 있음",
            "intake_method": "1일 1회 섭취", "functional_ingredients": "홍삼",
        }],
        "references": [{
            "category_reference_name": "홍삼", "ingredient_name": "진세노사이드",
            "main_functionality": "면역력 증진에 도움을 줄 수 있음",
        }],
        "claims": [{"claim_key_candidate": "claim-1", "claim_text_candidate": "면역력 증진에 도움을 줄 수 있음"}],
    }
    arguments = ["build_catalog_wide_mfds_profiles.py"]
    for option, rows in datasets.items():
        path = tmp_path / f"{option}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        arguments.extend([f"--{option}", str(path)])
    output = tmp_path / "generated"
    target = ROOT / "config/facet_taxonomy_v2_2.json"
    arguments.extend(["--taxonomy", str(target), "--output-dir", str(output)])
    monkeypatch.setattr(sys, "argv", arguments)
    main()
    result = pd.read_csv(output / "catalog_profiles.csv", dtype=str)
    assert result.taxonomy_version.tolist() == ["v2.2"]
    assert result.catalog_id.tolist() == ["mfds-1"]
    assert (output / "taxonomy.json").read_bytes() == target.read_bytes()
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8"))["taxonomyVersion"] == "v2.2"
