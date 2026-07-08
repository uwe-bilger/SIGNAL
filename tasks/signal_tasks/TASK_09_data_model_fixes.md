# TASK_09: Data model fixes found during Power BI exploration

*(Full rewrite — this supersedes the earlier draft of TASK_09 entirely.
That draft was never executed; everything below reflects the complete,
current design.)*

## Context

Connecting Power BI directly to `signal_dw` surfaced several structural
problems in the original schema: forecast and actuals pre-merged into one
wide table, a hardcoded `LAG1`-`LAG10` label instead of derived lag,
retail-POS framing that doesn't fit a B2B manufacturer, and — most
seriously — financial dollars and demand units mixed into a single
`fact_financial_plan` table. This task replaces all of that with a clean
set of single-purpose fact tables, each modeled on what one real system,
owned by one real team, would actually export.

**Core principle for this task: nothing is pre-merged.** Every fact table
below represents one domain (demand forecast, demand actuals, financial
plan, financial actuals) at one grain. Comparisons across domains (e.g.
"what did we plan to sell, in dollars") happen at query time — in a
BigQuery view, a DAX measure, or Power Query — never stored as a joined
row in a source table.

## Do NOT change

Stack (BigQuery/FastAPI/Cloud Run/React/Power BI), the 4-4-5 fiscal
calendar harmonization logic, `CLAUDE.md`. This task only touches the
fact tables listed below and anything downstream that reads them.

## The six fact tables

All six use **monthly grain** — no weekly grain anywhere in this set,
including sell-through (this reverses an earlier draft that had
sell-through at weekly grain; monthly is correct across the board for
this build).

### 1. `fact_forecast_sellin_snapshot`
Grain: `SKU × Site × Channel × target_month × snapshot_date`
Fields: `forecast_units` only.
Immutable, append-only. One snapshot per month (see "Snapshot timing"
below). Applies to all channel types.

### 2. `fact_forecast_sellthrough_snapshot`
Grain: `SKU × Channel × target_month × snapshot_date`
Fields: `forecast_units` only.
Same snapshot mechanics as #1. **Only populated for Distributor and OEM
Contract channel types** — sell-through has no meaning for Direct Sales
or CDMO Key Account, since there's no intermediary reporting layer.
Direct Sales/CDMO simply have no rows here, not nulls or zeros.

### 3. `fact_sellin_actuals`
Grain: `SKU × Site × Channel × month`
Fields: `actual_units` only. No `snapshot_date`, no version — actuals
aren't versioned, they just happened once realized.

### 4. `fact_sellthrough_actuals`
Grain: `SKU × Channel × month`
Fields: `actual_units` only. Same Distributor/OEM Contract-only scope as
its forecast counterpart (#2).

### 5. `fact_financial_snapshot`
Grain: `Division × Channel × Category × target_month × snapshot_date`
Fields: `revenue`, `cost`, `margin` only. **No SKU, no units, anywhere in
this table.** This is finance's own coarser grain — no attempt to fake
SKU-level precision that finance never plans at.

### 6. `fact_financial_actuals`
Grain: `Division × Channel × Category × month`
Fields: `revenue`, `cost`, `margin` only. No snapshot_date, no version.

### Not yet specified: supply/inventory
Supply/inventory (on-hand units, weeks of supply) is its own domain,
separate from all six tables above, and still needs its own fact
table(s) — grain and structure not yet designed. **Do not fold
inventory/supply fields into any of the six tables above.** Leave this as
an open item rather than guessing at the structure; flag it back for a
follow-up task once the demand/financial split above is stable.

## Snapshot timing — one per month, no separate stored version label

- **One snapshot per month**, dated as the **3rd Friday of that month**,
  consistently across all four snapshot-capable tables (#1, #2, #5 — #6
  has no snapshot concept, and #3/#4 are actuals with no snapshot
  either).
- **`version` (Budget, LE01–LE11) is never a stored column.** It's always
  derived — a BigQuery view column or DAX measure comparing
  `snapshot_date`'s month to `target_period_date`'s month:
  - The fixed Budget-setting month (December, prior fiscal year) → label
    `Budget`
  - Otherwise → `LE0N` where N is the snapshot month's position within
    the fiscal year (Jan snapshot → `LE01`, Feb → `LE02`, ... Nov →
    `LE11`). **There is no `LE12`** — by December, only one month of the
    fiscal year remains, not worth its own version label.
- Rationale for deriving rather than storing: a hardcoded version label
  can silently drift out of sync with the dates next to it (this is the
  same class of bug as the original `LAG1`-`LAG10` string labels this
  task is already fixing elsewhere — don't reintroduce it here).
- **`lag_months`** (for the demand-side snapshot tables) is likewise
  always derived: `target_period_date - snapshot_date`, never stored or
  hand-labeled.

## Where each piece of logic lives

- **BigQuery**: owns the six-table split above, the real
  `target_period_date`/`snapshot_date` columns, and views that derive
  `version` and `lag_months`. This is the single source of truth every
  downstream tool should see, not just Power BI.
- **Power BI Model view**: relationships between forecast and actuals
  tables (and between demand and financial tables, if ever needed for a
  specific report) go through shared dimension tables where possible,
  joined at `target_month`/`month` + shared keys — never a stored
  pre-join.
- **DAX measures**: WFA, bias %, MAPE-by-lag, and any forecast-vs-actual
  or plan-vs-financial comparison should be live DAX measures driven by a
  Measurement Month slicer — not stored columns, not Power Query steps.
  This is what lets a user "dial back" the measurement month and see
  numbers recompute live.

## Verification checklist

- [ ] All six fact tables exist with exactly the fields listed above —
      no `version` column stored on any of them, no unit/dollar mixing
      across the demand and financial tables
- [ ] Sell-through tables (#2, #4) only contain rows for Distributor/OEM
      Contract channel types
- [ ] `fact_financial_snapshot`/`fact_financial_actuals` contain no SKU
      or unit fields anywhere
- [ ] `target_period_date` and `snapshot_date` exist as real date columns
      on all three snapshot tables; snapshot_date consistently falls on
      the 3rd Friday of its month
- [ ] `version` and `lag_months` are derived (view columns or DAX
      measures), not stored source columns, anywhere in the model
- [ ] No table in this set joins forecast to actuals, or demand to
      financial, at rest — only at query time
- [ ] Mock data regenerates cleanly end to end against the new schema
- [ ] Spot check: for the same SKU and target period, a longer-lag
      forecast (e.g. LE02) should generally be less accurate than a
      shorter-lag one (e.g. LE09) once compared against actuals — if the
      mock data doesn't reflect that relationship, the generator logic
      needs adjusting, not just the schema
- [ ] Supply/inventory domain is explicitly left unspecified in this
      task, not folded into any of the six tables, and flagged as a
      follow-up
- [ ] Update NEXT.md's Now/Next/Parked as part of finishing this task
