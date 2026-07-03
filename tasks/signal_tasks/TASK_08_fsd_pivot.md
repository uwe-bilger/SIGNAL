# TASK_08: Pivot SIGNAL from Relatable (CPG) to Thermo Fisher FSD

## Context

SIGNAL was originally built as an interview portfolio piece for a Relatable
(consumer products) demand planning role. That interview process is over —
Uwe was hired by Thermo Fisher as Sr Supply Chain Manager / global SIOP
process owner for the **Filtration and Separation Division (FSD)**.

SIGNAL is being repurposed: it's no longer a portfolio demo, it's becoming
a real working demand/supply planning dashboard **and teaching tool** —
mock data that illustrates real planning effects (bias, timing artifacts,
level shifts, no-history SKUs, ERP migration data-quality steps) for
onboarding and training other planners at FSD.

**This task supersedes the Relatable-era content in TASK_00, TASK_02, and
TASK_05.** The underlying architecture (BigQuery/FastAPI/Cloud
Run/React/Cloudflare Pages, the 4-4-5 fiscal calendar harmonization, the
version dimension) is sound and does not change. This is a content and
data-model pivot, not a rearchitecture.

## Do NOT change

- Stack: BigQuery (`signal_dw`), FastAPI on Cloud Run, React on Cloudflare
  Pages, GCS, IONOS DNS.
- 4-4-5 → Gregorian fiscal calendar harmonization logic (partial week
  proration). This is real and stays as-is.
- Version dimension (Budget / OP Plan / LE1–3 / Latest Estimate +
  LAG1–LAG10 forecast accuracy snapshots).
- `CLAUDE.md` — already written generically, no Relatable-specific content
  in it, leave untouched.
- Overall Act 1 / Act 2 / Act 3 structure (current state → challenger pack
  → reconciliation). Only the *content* inside them changes (SKUs, brands,
  channel names); the mechanics stay.

## What changes: new business/data model

### 1. Business hierarchy (replaces Marketing hierarchy)

Old: `Division → Brand → Product Line → Sub Product Line → SKU`

New: `Division (FSD) → Business Line → Product Family → Platform/Series → SKU`

Three real Business Lines (confirmed via Thermo Fisher's own materials):
- **Bioprocessing Filtration** — depth filters, chromatographic
  clarification, AEX polishing (viral clearance / host cell protein
  reduction), membrane sterile filtration
- **Healthcare & Industrial Filtration** — medical device filtration,
  industrial process filtration
- **Membranes (incl. Membranes for OEM)** — membrane media supplied to
  other manufacturers for medical/industrial use (battery, semiconductor,
  water purification). Note in code comments: this line's demand driver is
  structurally different — it tracks a *customer's* production schedule,
  not end-patient/procedure volume. Good candidate for a deliberately
  different demand-pattern generator in the mock data.

### 2. Product hierarchy (keep shape, change content)

`Major Category → Category → Subcategory → SKU`, reorganized around
filtration technology instead of CPG product lines (depth filtration,
membrane sterile filtration, chromatography resins, viral
clearance/polishing, industrial/OEM membranes).

### 3. Channel/geography dimension (replaces Channel Type → Market →
   Customer Group → Key Account, 5 types incl. TikTok Shop)

New: `Channel Type → End-Market → Customer → Account`
- Channel Type: Direct Sales / Distributor / OEM Contract / CDMO Key
  Account
- End-Market: Pharma & Biotech / Industrial (battery, semiconductor,
  ultra-pure water) / Medtech

**Flag this clearly as a placeholder taxonomy in code comments** — it's
inferred from public Thermo Fisher materials, not confirmed against real
FSD CRM/channel structure yet. Revisit once Uwe has real system access.

### 4. NEW: Site/Plant dimension (net new — did not exist before)

This is the most consequential addition and the one with the richest
teaching value. FSD is a multi-plant, multi-country network mid-migration
between two ERP systems, and that migration itself is a real, dateable
data-quality event worth simulating.

Fields:
```
site_id, site_name, city, state_or_region, country,
business_lines_served (array),
legacy_erp ('SAP'), target_erp ('Oracle JDE/E1'),
migration_wave (int), planned_cutover_date (date),
migration_status ('legacy' | 'in_flight' | 'live_on_target'),
data_quality_flag (derived: poor pre-cutover, improving post-cutover)
```

Seed sites — three are real and confirmed, the rest should be clearly
labeled as plausible placeholders:
- **Charlotte, NC** (real — FSD anchor site)
- **Maplewood, MN** (real — Solventum's former HQ, FSD anchor site)
- **Frederick, MD** (real — FSD-adjacent site)
- 2–3 additional European sites — FSD's footprint is confirmed to include
  Europe, but specific city names are not yet confirmed. Generate
  plausible placeholder sites (e.g. a German and an Irish site, common for
  filtration/bioprocessing manufacturing) and mark them explicitly with a
  `is_placeholder_site: true` flag so they're never presented as fact in
  the UI — only as "illustrative" in tooltips/legends.

### 5. KPIs — replace generic forecast-accuracy-only framing with FSD's
   real, named metrics

- **WFA (Weighted Forecast Accuracy)** — baseline **54%**, target **75%**
  within 12 months. Model as a noisy improving trend, not a straight
  line — this is itself a good process-behavior-chart teaching example
  (routine variation around an improving trend vs. a genuine step change).
- **Inventory days on hand** — baseline ~**100 days**, framed internally
  as "lean" given ~2x demand growth.
- **Inventory entitlement** — model as a separate target metric from raw
  inventory days: the *right* inventory positioned in the *right* place,
  not simply "less inventory." Worth its own visual (actual vs.
  entitlement, by site or SKU segment) rather than folding it into a
  generic inventory chart.

### 6. Org/process model (optional Act 3 enhancement — flag as stretch)

Real, confirmed rollout sequence: **site-level SIOP → division roll-up →
executive SIOP**, run "side by side" per site rather than big-bang.
Escalation chain: demand review flags a supply issue → site supply review
responds with trade-offs → unresolved items escalate to exec SIOP for a
decision.

If time allows, add a lightweight **process maturity** attribute per site
(Stage 1–5, à la a standard S&OP maturity model) so the dashboard can show
FSD's early-stage state next to a hypothetical mature-division comparison
(internally, Thermo Fisher's CSD division is cited as the mature
template). This is a stretch goal — do not block the core pivot on it.

## Act 4 reframe: from "Hugimals M&A" to "FSD Integration"

The old Act 4 story (30 acquired SKUs with no history, from a fictional
Hugimals acquisition) gets replaced by a **more defensible, more real**
story: FSD itself is the newly acquired entity.

- Rename the route/component from `Act4Acquisition` to `Act4Integration`
  (update `frontend/src/pages/Act4Acquisition.tsx` →
  `Act4Integration.tsx`, and the corresponding API router
  `api/routers/acquisition.py` → `integration.py`).
- Two layered "no-history" mechanics to model, not one:
  1. **Whole-of-FSD acquisition boundary**: all data before the Thermo
     Fisher acquisition close (Sept 2025) is legacy Solventum/3M history.
     Flag with `is_pre_acquisition` on the time dimension or fact tables,
     distinct from any SKU-level flag.
  2. **Per-site ERP migration wave**: sites on legacy SAP show
     degraded/missing data quality; on their JDE cutover date, data
     quality visibly improves. This is a real, site-dateable level-shift
     event — a clean example of a *legitimate* level shift for teaching
     purposes, and it can sit next to a synthetic timing-artifact example
     (e.g. a large shipment landing one day into the new fiscal period)
     to teach the difference between "real signal" and "artifact of how
     you sliced the data."

## File-by-file punch list

1. **`README.md`** — rewrite opening framing (no longer "portfolio demo
   for Sr. Manager Demand Planning & S&OP roles"; it's a working
   demand/supply planning and teaching tool for FSD). Update Act
   descriptions, especially Act 4.
2. **`tasks/signal_tasks/TASK_00_context.md`** — full rewrite. This is the
   project's north star doc; see draft content below to use as the base.
3. **`tasks/signal_tasks/TASK_02_mockdata_v4.md`** — rewrite brand/SKU
   naming conventions section for FSD; add a new section specifying the
   Site/Plant dimension and ERP migration wave generator logic.
4. **`tasks/signal_tasks/TASK_05_frontend.md`** — update Act 4 spec to
   reflect the Integration reframe; update any Relatable-specific
   copy/mockup references.
5. **`etl/generate_mock_data.py`** — replace Relatable/Hugimals brand and
   SKU generation with FSD Business Line/Product Family/SKU generation;
   add Site dimension generation with migration wave logic and
   data-quality-by-date effects; add WFA and inventory entitlement measure
   generators.
6. **`api/routers/acquisition.py`** → rename to `integration.py`; update
   endpoints to serve the FSD-acquisition-boundary and ERP-migration-wave
   data instead of Hugimals-specific fields.
7. **`frontend/src/pages/Act4Acquisition.tsx`** → rename to
   `Act4Integration.tsx`; rebuild UI copy, chart labels, and any
   Hugimals-specific visuals to reflect the new story.

## Draft replacement content for `TASK_00_context.md`

Use this as the starting point; adjust as needed once inside the repo.

```markdown
# TASK_00: Project Context

## What SIGNAL is

SIGNAL (Supply Intelligence & Granular Navigation for Agile Lifecycle) is
a demand and supply planning dashboard built for Thermo Fisher's
Filtration and Separation Division (FSD). It serves two purposes:

1. A working analytics tool reflecting FSD's real planning structure
   (business lines, sites, ERP landscape, KPIs).
2. A teaching tool with mock data engineered to demonstrate real planning
   effects — forecast bias, timing artifacts, genuine level shifts,
   acquisition/no-history SKU handling, and ERP-migration data-quality
   transitions — for onboarding and training other planners.

## Business context

FSD was formed from Thermo Fisher's acquisition of Solventum's
Purification & Filtration business (closed Sept 2025); Solventum itself
was spun off from 3M in 2024. FSD sits in Thermo Fisher's Life Sciences
Solutions segment and has three business lines: Bioprocessing Filtration,
Healthcare & Industrial Filtration, and Membranes (incl. Membranes for
OEM).

FSD is early-stage from a planning-maturity standpoint: no formal SIOP
process existed before this build-out, WFA (Weighted Forecast Accuracy)
sits at 54% against a 75% 12-month target, inventory runs ~100 days on
hand, and the division is growing roughly 2x while supply planning
capability lags. The ERP landscape is legacy SAP (inherited from
3M/Solventum) migrating in site-by-site waves to Oracle JD Edwards (JDE).

## Data model

[Insert Business Line hierarchy, Product hierarchy, Channel/Geography
dimension, Site/Plant dimension, and Version dimension as specified in
TASK_01 (schema) and TASK_02 (mock data), updated per TASK_08.]

## Stack

GCP project `signal-499604`, BigQuery dataset `signal_dw`, GCS bucket
`signal-raw-data`. FastAPI on Cloud Run. React on Cloudflare Pages. DNS
via IONOS, live at signal.bilger.us.

## What "done" looks like

A publicly accessible dashboard covering: Act 1 (current-state bottoms-up
plan), Act 2 (challenger/top-down gap view), Act 3 (reconciliation:
Budget vs. LE vs. Latest Estimate), Act 4 (FSD integration: acquisition
boundary + ERP migration wave effects). Every data point should be
explainable and traceable to a specific, intentional mock-data effect —
this is a teaching tool as much as a dashboard.
```

## Execution instructions

1. Create a feature branch: `feat/task-08-fsd-pivot`.
2. Work through the file-by-file punch list above, in order (schema/data
   generation before API before frontend, since downstream layers depend
   on the new dimensions existing).
3. Regenerate mock data end to end
   (`python etl/generate_mock_data.py` → `python etl/load_to_bigquery.py`)
   and confirm the new Site dimension and ERP-migration-wave logic
   populate correctly.
4. Run the API and frontend locally and sanity-check Act 4 specifically,
   since it has the biggest content and naming changes.
5. Do not push directly to `main` — this repo's git rules require
   feature-branch work merged only after the verification checklist below
   passes. Pushing the completed branch to trigger the Cloudflare deploy
   is fine once merged.

## Verification checklist

- [ ] `grep -ril -iE "relatable|hugimals|WDYM|buzzed|incohearent" .` returns
      no results anywhere in the repo
- [ ] New Site/Plant dimension exists in the BigQuery schema and is
      populated with the seed sites above (real + clearly-flagged
      placeholders)
- [ ] Mock data regenerates cleanly end to end with no errors
- [ ] WFA and inventory entitlement measures exist and render sensibly
      (WFA trending 54%→75% with noise, not a straight line)
- [ ] Act 4 is renamed to Integration, reflects the acquisition-boundary +
      ERP-migration-wave story, and no longer references Hugimals
- [ ] `acquisition.py` renamed to `integration.py`, endpoints updated and
      responding
- [ ] Frontend builds with no errors and all four Acts render
- [ ] `README.md` and `TASK_00_context.md` reflect FSD framing throughout
- [ ] `CLAUDE.md` left untouched (already correct)
