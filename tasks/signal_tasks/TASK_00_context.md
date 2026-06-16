# SIGNAL — Project Context
> Read this before executing any task. Do not execute this file.

## What is SIGNAL?
SIGNAL (Supply Intelligence & Granular Navigation for Agile Lifecycle) is a demand
planning intelligence platform built as a portfolio demo for a Sr. Manager Demand
Planning & S&OP interview at Relatable (consumer products, ~$200M, founder-owned,
Google Workspace shop).

The deliverable is a shareable public URL at signal.bilger.us — fully interactive,
filterable, drillable, and defensible data point by data point.

## Infrastructure
- **GCP Project:** signal-499604
- **BigQuery:** primary data store, dataset name: `signal_dw`
- **GCS Bucket:** signal-raw-data (us-central1)
- **Service Account:** signal-etl
- **Credentials:** ./secrets/signal-key.json
- **API:** FastAPI on Cloud Run
- **Frontend:** React on Cloudflare Pages
- **Domain:** signal.bilger.us
- **GitHub:** github.com/uwe-bilger/SIGNAL

## Dimensional Model

### Product dimensions (two separate hierarchies, both resolve to SKU)
**Marketing hierarchy:**
Division → Brand → Product Line → Sub Product Line → SKU

**Product hierarchy:**
Major Category → Category → Subcategory → SKU

### Geography dimension
Channel Type → Market → Customer Group → Key Account
Channel Types: Retail, E-commerce, DTC, Distributor

### Time dimension
Fiscal year (4-4-5 calendar) → Quarter → Month → Week → Partial Week
Includes Gregorian calendar mapping for each fiscal period.

### Planning version dimension
**Financial versions:** Budget, Op Plan, LE1, LE2, LE3, Latest Estimate
**Forecast accuracy versions:** Lag1 through Lag10
(Lag1 = 1 month ago forecast, Lag10 = 10 months ago forecast)

## Measures (per SKU, per geography, per time period, per version)
**Sell-in:** units, dollars
**Sell-through (POS):** units, dollars
**Inventory:** on hand units, weeks of supply
**Forecast components:**
- Corrected history (baseline adjusted)
- Statistical forecast (baseline)
- Manual override (delta units)
- Promotional uplift (named promotions, additive)
- Total forecast (stat + promo + override)

## Mock Data Scope
- 300 SKUs across 3 divisions
- 5 years history (2020-2024) + 2 years forward forecast (2025-2026)
- Weekly grain for POS/inventory, monthly grain for financial plan
- All planning versions populated
- Lag1-Lag10 forecast snapshots
- ~10 key accounts per channel type
- Named promotions (at least 5 per year)

## Dashboard Structure (four acts)
**Act 1 — Current state**
Bottoms-up demand plan, SKU by retailer, what Sales has today.

**Act 2 — Challenger pack**
Top-down view, gap vs. bottoms-up, forward-looking exception layer.

**Act 3 — Reconciliation**
Demand plan vs. monthly LE vs. budget anchor. LE vs LE comparison.
Lag forecast accuracy tracking.

**Act 4 — M&A integration**
Hugmoals acquisition onboarding, no-history SKU handling,
supply risk flags during transition.

## Design Intent
Modern, clean, no default chart library aesthetic. Recharts for visualization.
Feels like a product, not a dashboard. Mobile and desktop responsive.
No login required. Public URL shareable directly.

## Task Execution Order
TASK_01 → TASK_02 → TASK_03 → TASK_04 → TASK_05 → TASK_06 → TASK_07

Never skip a task. Each task ends with a verification checklist.
Complete all checklist items before moving to the next task.
