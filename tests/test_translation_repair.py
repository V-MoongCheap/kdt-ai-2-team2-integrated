import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def runner(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "scripts/facet"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location("repair_runner", directory / "repair_kuaisearch_translation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_rejects_placeholders_and_product_changes(runner):
    assert "PLACEHOLDER" in runner.quality_flags("猫粮", "...")
    assert "TERM_MISMATCH:菠萝" in runner.quality_flags("菠萝软糖", "바나나 젤리")
    assert not runner.quality_flags("菠萝软糖", "파인애플 젤리")
    assert "NUMBER_MISSING" in runner.quality_flags("猫粮2袋", "고양이 사료")


def test_repair_preserves_original_and_resumes(runner, tmp_path, monkeypatch):
    source = tmp_path / "source.parquet"
    output = tmp_path / "v2.parquet"
    frame = pd.DataFrame({"source_record_id": ["1", "2"], "query_raw": ["猫粮", "菠萝软糖"], "query_translated": ["...", "바나나 젤리"]})
    frame.to_parquet(source, index=False)
    original = source.read_bytes()
    monkeypatch.setattr("sys.argv", ["repair", "--input", str(source), "--output", str(output), "--passes", "1"])
    monkeypatch.setattr(runner, "_translate_batch", lambda *args: [{"source_record_id": "0", "query_translated": "고양이 사료"}])
    runner.main()
    saved = pd.read_parquet(output)
    assert saved.query_translated.tolist() == ["고양이 사료", "바나나 젤리"]
    assert saved.repair_status.tolist() == ["AUTOMATED_CHECKS_PASSED", "NEEDS_REVIEW"]
    assert source.read_bytes() == original
    calls = []

    def translate(rows, *args):
        calls.extend(rows)
        return [{"source_record_id": "1", "query_translated": "파인애플 젤리"}]

    monkeypatch.setattr(runner, "_translate_batch", translate)
    runner.main()
    assert len(calls) == 1
    assert calls[0]["source_record_id"] == "1"
    report = json.loads(output.with_suffix(".report.json").read_text())
    assert report["remaining_flagged"] == 0
    assert pd.read_parquet(output).translation_original.tolist() == ["...", "바나나 젤리"]
    frame.assign(query_raw=["狗粮", "菠萝软糖"]).to_parquet(source)
    with pytest.raises(ValueError, match="snapshot changed"):
        runner.main()
