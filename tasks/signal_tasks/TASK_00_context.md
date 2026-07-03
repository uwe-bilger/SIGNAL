# TASK_00: Project Context
> Read this before executing any task. Do not execute this file.

## What SIGNAL is

SIGNAL (Supply Intelligence & Granular Navigation for Agile Lifecycle) is a demand
and supply planning dashboard built for Thermo Fisher's Filtration and Separation
Division (FSD). It serves two purposes:

1. A working analytics tool reflecting FSD's real planning structure (business lines,
   manufacturing sites, ERP landscape, KPIs).
2. A teaching tool with mock data engineered to demonstrate real planning effects —
   forecast bias, timing artifacts, genuine level shifts, demand spikes (pandemic,
   GLP-1, EV battery), acquisition/no-history SKU handling, and ERP-migration
   data-quality transitions — for onboarding and training other planners.

## Business context

FSD was formed from Thermo Fisher's acquisition of Solventum's Purification &
Filtration business (closed Sept 2025). Solventum itself was spun off from 3M in
2024. FSD sits in Thermo Fisher's Life Sciences Solutions segment.

Three Business Lines:
- **Bioprocessing Filtration** — depth filters, chromatographic clarification, AEX
  polishing (viral clearance / HCP reduction), membrane sterile filtration
- **Healthcare & Industrial Filtration** — medical device filtration (syringe filters,
  IV line filters, venting), industrial process filtration (liquid, gas)
- **Membranes (incl. OEM)** — membrane media supplied to OEM customers for battery
  separators, semiconductor ultra-pure water, and medical OEM devices. Note: demand
  driver is structurally different — tracks the customer's production schedule, not
  end-patient/procedure volume.

FSD is early-stage from a planning-maturity standpoint:
- No formal SIOP process before this build-out
- WFA (Weighted Forecast Accuracy) at 54% against a 75% 12-month target
- Inventory running ~100 days on hand
- Division growing ~2x while supply planning capability lags
- ERP: legacy SAP (3M/Solventum) migrating in site-by-site waves to Oracle JDE

## Infrastructure

- **GCP Project:** signal-499604
- **BigQuery:** dataset `signal_dw`
- **GCS Bucket:** signal-raw-data
- **Service Account:** signal-etl / secrets/signal-key.json (never committed)
- **API:** FastAPI on Cloud Run (us-central1)
- **Frontend:** React on Cloudflare Pages
- **Domain:** signal.bilger.us
- **GitHub:** github.com/uwe-bilger/SIGNAL

## Dimensional model

### Product hierarchy (column names preserved from v4 schema)
```
division_id         → Business Line  (DIV-01: Bioprocessing, DIV-02: H&I, DIV-03: Membranes)
brand_id            → Product Family (depth filtration, sterile, chromatography, viral clearance, ...)
product_line_id     → Platform/Series (Clariflex™, SterilPure™, AEX-Pro™, ViralGuard™, ...)
sub_product_line_id → Fine classification (size/grade/format)
```

### Product category hierarchy
```
Major Category → Category → Subcategory → SKU
(Filtration Media | Systems & Devices | Membrane Products)
```

### Channel/geography dimension (PLACEHOLDER — not validated vs. FSD CRM)
```
Channel Type → End-Market → Customer Group → Key Account
Types: Direct Sales / Distributor / OEM Contract / CDMO Key Account
End-Markets: Large Pharma | Biotech | Distribution | Battery OEM | Semiconductor | CDMO
```

### Site/Plant dimension (net new in v5)
```
site_id, city, country, business_lines_served,
legacy_erp, target_erp, migration_wave, planned_cutover_date,
migration_status (legacy | in_flight | live_on_target), is_placeholder_site
```
Real confirmed sites: Charlotte NC, Maplewood MN, Frederick MD.
European placeholders (illustrative only): Düsseldorf DE, Limerick IE.

### Time dimension
4-4-5 fiscal calendar + Gregorian mapping. Adds `is_pre_acquisition` flag:
True for dates before 2025-09-01 (Solventum/3M era data).

### Version dimension (unchanged)
Budget / OP Plan / LE1 / LE2 / LE3 / Latest Estimate + LAG1–LAG10

## Measures (per SKU × account × time × version)
- Sell-in: units, dollars
- Sell-through (POS): units, dollars
- Inventory: on_hand_units, weeks_of_supply
- **inventory_entitlement_days** (target DOH — right inventory in right place)
- **data_quality_score** (0.0–1.0, degrades pre-ERP cutover, improves post-cutover)
- Forecast components: stat, manual override, promo uplift, total

## Mock data scope

- ~165 FSD product SKUs across 3 Business Lines
- ~20 post-acquisition new SKUs (is_new_sku=True, launched Q4 2025–2026)
- 22 key accounts (pharma direct, distributor, OEM, CDMO)
- 5 manufacturing sites (3 real + 2 illustrative placeholder)
- 7 years: 2020–2026 (monthly financial plan, weekly POS, LAG1–LAG10 snapshots)
- WFA noise calibrated: 54% baseline (2024) improving toward 75% (2026)
- Demand spikes: COVID sterile filtration (2020), mRNA (2021), EV battery ramp (2022–2024),
  GLP-1/Ozempic/Mounjaro pull (2023–2024)

## Dashboard structure (four acts)

**Act 1 — Current State**
Bottoms-up demand plan: KPI row, SKU×account heatmap, monthly trend, exception badges.

**Act 2 — Challenger Pack**
Top-down view, gap vs. bottoms-up, forward exception layer.

**Act 3 — Reconciliation**
Budget vs. LE vs. Latest Estimate comparison. Lag forecast accuracy tracking.

**Act 4 — FSD Integration**
Acquisition boundary (pre vs. post Sept 2025), ERP migration wave timeline
per site, data quality step change, WFA improving trend, new post-TF SKUs.

## Task execution order
TASK_01 → TASK_02 → TASK_03 → TASK_04 → TASK_05 → TASK_06 → TASK_07 → TASK_08

Never skip a task. Each task ends with a verification checklist.
Complete all checklist items before moving to the next task.
