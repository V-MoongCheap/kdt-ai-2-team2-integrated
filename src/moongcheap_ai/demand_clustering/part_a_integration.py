"""Part A artifact checks and B's explicit legacy-expression compatibility."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ..demand_constraints import DemandConstraintParser
from ..demand_constraints.classifier import normalize


def taxonomy_version(taxonomy: Mapping[str, Any]) -> str:
    versions = {
        str(taxonomy[key]).strip()
        for key in ("version", "taxonomy_version")
        if taxonomy.get(key)
    }
    if len(versions) != 1 or not next(iter(versions), ""):
        raise ValueError("taxonomy must declare one unambiguous version")
    return versions.pop()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_profile_versions(
    profiles: pd.DataFrame, taxonomy: Mapping[str, Any],
) -> str:
    expected = taxonomy_version(taxonomy)
    if "taxonomy_version" not in profiles:
        raise ValueError("profiles missing taxonomy_version")
    actual = set(profiles["taxonomy_version"].fillna("").astype(str).str.strip())
    if actual - {expected}:
        raise ValueError(
            f"profile taxonomy versions {sorted(actual)} do not match {expected}; "
            "prepare a compatible profile release before starting the batch"
        )
    return expected


def build_part_b_parser(
    taxonomy: Mapping[str, Any],
    *,
    rules_path: Path,
    aliases_path: Path,
    compatibility_aliases_path: Path | None = None,
) -> tuple[DemandConstraintParser, dict[str, Any]]:
    """Keep A's reviewed aliases authoritative for overlapping surfaces.

    Optional B compatibility aliases retain existing frequency/ingredient
    expressions. They are reported as a separate, unapproved source; this
    function neither changes A's files nor promotes B aliases to APPLIED.
    """
    version = taxonomy_version(taxonomy)
    primary = json.loads(aliases_path.read_text(encoding="utf-8"))
    if primary.get("taxonomy_version", version) != version:
        raise ValueError("primary alias taxonomy version does not match taxonomy")
    if any(
        rule.get("review_status", rule.get("status", "APPLIED")) != "APPLIED"
        for rule in primary.get("aliases", [])
    ):
        raise ValueError("primary aliases must be an APPLIED-only export")
    enriched = deepcopy(taxonomy)
    summary: dict[str, Any] = {
        "taxonomyVersion": version,
        "primaryAliasVersion": primary.get("version", ""),
        "primaryAliasSha256": file_digest(aliases_path),
        "compatibilityAliasVersion": None,
        "compatibilityAliasStatus": None,
        "compatibilityAliasSha256": None,
        "compatibilitySurfaceCount": 0,
    }
    if compatibility_aliases_path is not None:
        compatibility = json.loads(
            compatibility_aliases_path.read_text(encoding="utf-8")
        )
        summary.update({
            "compatibilityAliasVersion": compatibility.get("version", ""),
            "compatibilityAliasStatus": compatibility.get("status", "UNREVIEWED"),
            "compatibilityAliasSha256": file_digest(compatibility_aliases_path),
        })
        for category in enriched.get("categories", []):
            category_id = category["category_id"]
            # Reserve all primary surfaces in this category, even if B's
            # historical registry points the same text at a different value.
            reserved = {
                normalize(surface)
                for rule in primary.get("aliases", [])
                if not rule.get("category_local_values")
                or category_id in rule["category_local_values"]
                for surface in rule.get("surfaces", [])
            }
            for facet in category.get("facets", []):
                for rule in compatibility.get("aliases", []):
                    if rule["facet_name"] != facet["name"]:
                        continue
                    if rule.get("review_status", rule.get("status")) in {
                        "DEFERRED", "REJECTED",
                    }:
                        continue
                    for value in facet.get("values", []):
                        if int(value["code"]) == 0 or normalize(value["value"]) != normalize(rule["canonical_value"]):
                            continue
                        existing = value.get("aliases", [])
                        if isinstance(existing, str):
                            existing = existing.split("|")
                        aliases = list(existing)
                        seen = {normalize(surface) for surface in aliases}
                        for surface in rule.get("surfaces", []):
                            normalized = normalize(surface)
                            if normalized and normalized not in reserved | seen:
                                aliases.append(surface)
                                seen.add(normalized)
                                summary["compatibilitySurfaceCount"] += 1
                        value["aliases"] = aliases
    return DemandConstraintParser.from_taxonomy(
        enriched, rules_path=rules_path, aliases_path=aliases_path,
    ), summary
