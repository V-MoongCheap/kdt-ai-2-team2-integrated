"""Read existing A labels for category-local integration diagnostics only."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable, Mapping

from .input_models import DemandInput


def inspect_label(
    label: str | None, category: Mapping[str, Any],
) -> dict[str, Any]:
    """Decode the label shape, without inferring MUST/EXCLUDE/PREFER from it."""
    if label is None or not str(label).strip():
        return {"status": "MISSING", "facetValues": {}}
    text = str(label).strip()
    facets = [facet for _, facet in sorted(
        enumerate(category.get("facets", []), 1),
        key=lambda pair: int(pair[1].get("order", pair[0])),
    )]
    if not re.fullmatch(r"[0-9]+(?:-[0-9]+)*", text) or len(text.split("-")) != len(facets):
        return {"status": "INVALID_FORMAT", "facetValues": {}}
    decoded = {}
    for raw_code, facet in zip(text.split("-"), facets):
        try:
            code = int(raw_code)
        except ValueError:
            return {"status": "INVALID_FORMAT", "facetValues": {}}
        value = next((v for v in facet["values"] if int(v["code"]) == code), None)
        if value is None:
            return {"status": "UNKNOWN_VALUE_CODE", "facetValues": {}}
        decoded[facet["name"]] = {"code": code, "value": value["value"]}
    return {"status": "VALID_CATEGORY_LOCAL", "facetValues": decoded}


def summarize_demand_labels(
    demands: Iterable[DemandInput],
    category_by_catalog: Mapping[int, str],
    taxonomy: Mapping[str, Any],
) -> dict[str, Any]:
    categories = {c["category_id"]: c for c in taxonomy.get("categories", [])}
    counts: Counter[str] = Counter()
    for demand in demands:
        category = categories.get(category_by_catalog.get(demand.catalog_id, ""))
        if category is None:
            counts["CATEGORY_UNAVAILABLE"] += 1
        else:
            counts[inspect_label(demand.label, category)["status"]] += 1
    return {
        "scope": "INITIAL_ELIGIBLE_DEMANDS",
        "demandCount": sum(counts.values()),
        "statusCounts": dict(sorted(counts.items())),
        "labelSourceVersion": "NOT_RECORDED_IN_DEMAND",
        "usedForCandidateSelection": False,
    }
