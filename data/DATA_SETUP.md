# SENTINEL — Live Dataset Setup (Fivetran → BigQuery)

SENTINEL's causal engine reads **real Fivetran-synced data** from BigQuery. This
guide refreshes the AcmeSaaS dataset with a richer 17-row weekly series that
gives the causal battery more statistical power.

**Why bother:** the original 7-row series scores **2/3** causal tests significant.
The richer 17-row series (`acmesaas_metrics.csv`) scores **3/3** — Granger
p=0.026, ITS significant, Mann-Whitney p=0.0002, 89% churn effect. Verified locally.

> Keep the data **Fivetran-synced** — don't write it straight to BigQuery. The
> whole point is that the numbers flow Source → Fivetran → BigQuery, live.

## Steps

1. **Open the source Google Sheet** that the `humble_currently` (google_sheets)
   connector syncs to BigQuery `google_sheets.acmesaas_metrics`.
2. **Replace its contents** with `data/acmesaas_metrics.csv` (header row + 17 rows).
   - Keep the decision date row **2026-06-03** — SENTINEL anchors the
     before/after split there (`_SCENARIO_DECISION_DATE["acmesaas"]`).
   - Column headers must stay: `date, mrr, arr, nps, churn_rate,
     support_tickets_7d, active_customers, cac, ltv, runway_months`
     (Fivetran normalizes `support_tickets_7d` → `support_tickets_7_d` in BigQuery).
3. **Trigger a sync** — either:
   - SENTINEL UI → **Fivetran Platform → Sync** on `humble_currently`, or
   - `curl -X POST <url>/api/connectors/humble_currently/sync`, or
   - the Fivetran dashboard → Sync now.
4. **Wait ~1 min**, then verify the live trace picked it up:
   ```bash
   curl http://127.0.0.1:8101/api/demo/acmesaas/full \
     | python -c "import sys,json;t=json.load(sys.stdin)['trace'];print(t['data_source'], t['causal_analysis']['significant_tests'],'/3', t['bradford_hill']['total_score'])"
   # expect: bigquery_live 3 /3 <higher score>
   ```

## Optional — second live data source (more breadth)

The `highway_ambitious` (fivetran_log) connector already syncs Fivetran's own run
logs to BigQuery. To surface it as a registered SENTINEL source, add to `.env` /
`env-cloud.yaml`:

```env
SENTINEL_BQ_FIVETRAN_LOG_TABLE=fivetran_log.log
```

(Adjust the table name to your actual `fivetran_log` dataset table.) It then
appears in `/api/connectors/list` → `bigquery_registry`, showing SENTINEL reading
from two live Fivetran connectors instead of one.
