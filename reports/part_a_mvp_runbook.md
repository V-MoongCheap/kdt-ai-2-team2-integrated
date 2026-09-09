# Part A MVP Runtime Runbook

## Scope

This entry point parses Consumer Demand `extra_requirement` with the approved
V2.2 taxonomy and the reviewed APPLIED alias registry. It is deterministic and
does not call an external LLM.

It does not run Demand Board creation, clustering, embeddings, seller matching,
or candidate ranking. Those are downstream responsibilities.

## Inputs

Required CSV columns:

- `demand_id`
- `catalog_id`
- `category_id` (or a catalog CSV that maps the catalog ID to a category)
- `extra_requirement`
- `is_substitutable`

## Local execution

```powershell
$env:PYTHONPATH = "src"
python scripts/labeling/run_part_a_runtime.py `
  --input <demand.csv> `
  --output data/processed/demands/part_a_runtime_v2_2.csv `
  --taxonomy config/facet_taxonomy_v2_2.json `
  --rules config/demand_constraint_rules.json `
  --alias-registry config/model1_aliases_reviewed_v2.json
```

The command also writes a JSON summary beside the output. It skips rows whose
`processed_at` is already populated.

## Output checks

Check these fields before handing results to Part B:

- `status`
- `effectiveRequirementMode`
- `constraints`
- `passthroughText`
- `reasonCodes`
- `taxonomyVersion`
- `parserVersion`

Expected status values are `PARSED`, `PASSTHROUGH`, `NONE`, `CONFLICT`,
`TAXONOMY_AMBIGUOUS`, `REVIEW`, and `NOT_APPLICABLE`.

`PASSTHROUGH` retains meaningful text that is outside the structured taxonomy.
It is not a failed parse. `CONFLICT`, `TAXONOMY_AMBIGUOUS`, and `REVIEW` have
no effective structured requirement and must not be silently converted into a
hard condition.

## Operational adapter

The CSV runner is the credential-free smoke path. A database adapter may read
unprocessed demands and a Backend adapter may write the JSON contract, but
those adapters must preserve the same status and Category-local code rules.
Secrets are supplied through the runtime environment and are never written to
reports or output files.

