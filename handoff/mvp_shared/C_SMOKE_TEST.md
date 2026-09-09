# C Smoke Test

The current repository contains a deterministic local seller matching baseline.
After A/B produces `clustering_input_v2_2.csv`, run:

```powershell
python scripts/e2e/run_mvp_local_e2e.py `
  --input data/processed/mvp_shared_smoke/clustering_input_v2_2.csv `
  --offers handoff/mvp_shared/smoke/seller_offers_smoke.csv `
  --output-dir data/processed/mvp_shared_smoke/c_output
```

Expected smoke result for this bundle:

- demands: 20
- clusters: 20
- offers: 200
- candidate matches: 4,000

This is a local CSV baseline. The future always-on C HTTP Deployment, its
`/health` endpoint, and `SELLER_ANALYSIS_INTERNAL_KEY` handling belong to the
C implementation PR and are not included in this smoke command.
