"""Prepare a new profile release only after proving taxonomy compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ..part_a_integration import file_digest, taxonomy_version, validate_profile_versions
from ..substitute_proposal_planner import build_runtime_catalog_profiles


def category_code_contract(taxonomy: Mapping[str, Any]) -> dict[str, tuple]:
    return {
        category["category_id"]: tuple(
            (
                int(facet["order"]), facet["name"],
                tuple(sorted((int(value["code"]), value["value"]) for value in facet["values"])),
            )
            for facet in sorted(category["facets"], key=lambda f: int(f["order"]))
        )
        for category in taxonomy["categories"]
    }


def prepare_profile_release(
    profiles_path: Path,
    source_taxonomy_path: Path,
    target_taxonomy_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Preserve IDs/evidence; re-version only identical category-local codebooks.

    V2.1's provisional taxonomy file and profiles named v2.1 are a known
    naming pair. This exception still requires an exact codebook comparison.
    """
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite profile release: {output_dir}")
    source = json.loads(source_taxonomy_path.read_text(encoding="utf-8"))
    target = json.loads(target_taxonomy_path.read_text(encoding="utf-8"))
    if category_code_contract(source) != category_code_contract(target):
        raise ValueError("category-local facet order, names, codes or values changed; rebuild profiles from evidence")
    source_version = taxonomy_version(source)
    target_version = taxonomy_version(target)
    profiles = pd.read_csv(profiles_path, dtype=str, keep_default_na=False)
    if "taxonomy_version" not in profiles or profiles.empty:
        raise ValueError("source profiles must be nonempty and declare taxonomy_version")
    allowed = {source_version, source_version.removesuffix("-provisional")}
    if set(profiles["taxonomy_version"].str.strip()) - allowed:
        raise ValueError("source profile versions do not match the source taxonomy")
    before = build_runtime_catalog_profiles(profiles, source)
    updated = profiles.copy()
    updated["taxonomy_version"] = target_version
    validate_profile_versions(updated, target)
    after = build_runtime_catalog_profiles(updated, target)
    changed_ids = [
        catalog_id for catalog_id in before
        if before[catalog_id].facet_values != after[catalog_id].facet_values
        or before[catalog_id].semantic_text != after[catalog_id].semantic_text
    ]
    if changed_ids:
        raise ValueError("runtime profile interpretation changed; rebuild profiles from evidence")
    output_dir.mkdir(parents=True)
    updated.to_csv(output_dir / "catalog_profiles.csv", index=False, encoding="utf-8-sig")
    (output_dir / "taxonomy.json").write_bytes(target_taxonomy_path.read_bytes())
    manifest = {
        "schemaVersion": "b-profile-release.v1",
        "taxonomyVersion": target_version,
        "sourceTaxonomyVersion": source_version,
        "sourceProfileVersions": sorted(set(profiles["taxonomy_version"])),
        "profileCount": len(updated),
        "categoryCodeContractIdentical": True,
        "changedRuntimeProfiles": len(changed_ids),
        "catalogIdMapping": "PRESERVED_FROM_INPUT_NOT_REBOUND_TO_BACKEND",
        "sourceProfileSha256": file_digest(profiles_path),
        "sourceTaxonomySha256": file_digest(source_taxonomy_path),
        "profileSha256": file_digest(output_dir / "catalog_profiles.csv"),
        "taxonomySha256": file_digest(output_dir / "taxonomy.json"),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return manifest
