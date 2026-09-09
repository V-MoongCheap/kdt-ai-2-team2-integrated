"""Build the small, reproducible handoff bundle for local MVP smoke tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd


def _copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(repo_root: Path, source_root: Path, output: Path, limit: int = 20) -> dict[str, object]:
    (output / "smoke").mkdir(parents=True, exist_ok=True)
    config_names = [
        "facet_taxonomy_v2_2.json",
        "model1_aliases_reviewed_v2.json",
        "taxonomy_value_crosswalk_v2.json",
        "demand_constraint_rules.json",
        "demand_constraint_aliases.json",
    ]
    for name in config_names:
        _copy(repo_root / "config" / name, output / "config" / name)
    _copy(repo_root / ".env.example", output / ".env.example")

    demand_path = source_root / "data/processed/demand_5000_v1/model2_eval_sample_200_v1.csv"
    facet_path = source_root / "data/processed/model1_v0_refresh4/product_facet_mapping_v0.csv"
    offer_path = source_root / "data/processed/domeggook/seller_offers_core.csv"
    demands = pd.read_csv(demand_path, dtype=str).fillna("").head(limit)
    demands.to_csv(output / "smoke/demands_v2_2.csv", index=False, encoding="utf-8-sig")
    product_ids = set(demands.get("catalog_id", pd.Series(dtype=str)).astype(str))
    facets = pd.read_csv(facet_path, dtype=str).fillna("")
    if "source_product_id" in facets:
        facets = facets[facets["source_product_id"].astype(str).map(lambda value: f"catalog-seed-{value}" in product_ids)]
    facets.to_csv(output / "smoke/product_facets_smoke.csv", index=False, encoding="utf-8-sig")
    pd.read_csv(offer_path, dtype=str).fillna("").head(200).to_csv(output / "smoke/seller_offers_smoke.csv", index=False, encoding="utf-8-sig")

    manifest_files = sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file() and path.name != "manifest.json")
    manifest = {
        "bundle_version": "mvp-shared-v2.2",
        "purpose": "A/B/C local smoke handoff; no secrets or raw corpus",
        "source_taxonomy": "config/facet_taxonomy_v2_2.json",
        "runtime_mode": "Rule/Alias-only; LABELING_LLM_FALLBACK_ENABLED=false",
        "files": [{"path": name, "sha256": _sha256(output / name), "bytes": (output / name).stat().st_size} for name in manifest_files],
        "production_artifacts_not_included": [
            "PostgreSQL Demand data",
            "Backend internal key",
            "E5 model directory",
            "full product facet mapping CSV",
            "full seller offer corpus",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output": str(output), "files": len(manifest_files), "demand_rows": len(demands), "facet_rows": len(facets), "offer_rows": 200}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-root", type=Path, default=Path(".."))
    parser.add_argument("--output", type=Path, default=Path("handoff/mvp_shared"))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    print(build(args.repo_root, args.source_root, args.output, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
