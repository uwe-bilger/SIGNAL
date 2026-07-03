# TASK_02 — Generate Mock Data (v5 — FSD Pivot)

## Objective
Generate all mock data for Thermo Fisher's Filtration and Separation Division (FSD).
Upload to GCS bucket `signal-raw-data`. The mock data is engineered to demonstrate
real planning effects as a teaching tool, not to represent actual FSD commercial data.

---

## SKU ID format
```
{BU_CODE}-{PRODUCT_CODE}-{VARIANT_NNN}

Examples:
  BPF-DFLT-001    Bioprocessing Filtration — Depth Filter (Clariflex™ lenticular)
  BPF-STRL-003    Bioprocessing Filtration — Sterile Filtration (SterilPure™ PES)
  BPF-CHRO-002    Bioprocessing Filtration — Chromatography (AEX-Pro™ resin 1L)
  BPF-VIRL-001    Bioprocessing Filtration — Viral Clearance (ViralGuard™)
  HIF-MEDF-001    Healthcare & Industrial — Medical Device (MedLine™ syringe filter)
  HIF-INDF-003    Healthcare & Industrial — Industrial (InduPure™ cartridge)
  MEM-OEMM-001    Membranes OEM — Battery separator (BattSep™)
  MEM-SPEC-003    Membranes — Specialty NanoFilt™
```

---

## Business Lines (3) — stored in division_id column

```
DIV-01: Bioprocessing Filtration
DIV-02: Healthcare & Industrial Filtration
DIV-03: Membranes (incl. OEM)
         ↑ Demand driver is structurally different: tracks customer's
           production schedule, not end-patient volume. This is intentional
           and worth calling out in teaching contexts.
```

---

## Product Families (8) — stored in brand_id column

```
BRD-01: Depth Filtration            (DIV-01)
BRD-02: Membrane Sterile Filtration (DIV-01)
BRD-03: Chromatographic Clarification (DIV-01)
BRD-04: Viral Clearance             (DIV-01)
BRD-05: Medical Device Filtration   (DIV-02)
BRD-06: Industrial Process Filtration (DIV-02)
BRD-07: OEM Membrane Media          (DIV-03)
BRD-08: Specialty Membranes         (DIV-03)
```

---

## Platform/Series (18) — stored in product_line_id column

```
PL-01: Clariflex™ Lenticular Series        (BRD-01)
PL-02: SingleClear™ Capsule Depth Filters  (BRD-01)
PL-03: SterilPure™ PES Series              (BRD-02)
PL-04: SterilPure™ PVDF Series             (BRD-02)
PL-05: FlexFlow™ Sterilizing Capsules      (BRD-02)
PL-06: AEX-Pro™ Anion Exchange             (BRD-03)
PL-07: MixMode™ Multimodal Chromatography  (BRD-03)
PL-08: ViralGuard™ Parvo-Retrovirus        (BRD-04)
PL-09: ParvoSure™ 20nm Filters             (BRD-04)
PL-10: MedLine™ Syringe Filters            (BRD-05)
PL-11: AirShield™ Venting Filters          (BRD-05)
PL-12: SafeFlow™ IV Line Filters           (BRD-05)
PL-13: InduPure™ Liquid Process Filters    (BRD-06)
PL-14: GasGuard™ Gas Filtration            (BRD-06)
PL-15: BattSep™ Battery Separator          (BRD-07)
PL-16: UPW-Mem™ Ultra-Pure Water           (BRD-07)
PL-17: MedOEM™ Medical OEM Membranes       (BRD-07)
PL-18: NanoFilt™ Specialty Filtration      (BRD-08)
```

---

## SKU count: ~165 total

- DIV-01 Bioprocessing: ~60 SKUs (depth filters, sterile, chromatography, viral clearance)
- DIV-02 Healthcare & Industrial: ~33 SKUs (syringe filters, IV filters, venting, industrial)
- DIV-03 Membranes: ~35 SKUs (battery separators, UPW, medical OEM, specialty)
- ~20 post-acquisition new SKUs (is_new_sku=True), launched Q4 2025–2026

Post-acquisition SKUs represent products introduced after TF closed the acquisition,
enabled by Thermo Fisher R&D resources. They have no Solventum/3M history.

---

## Channel/geography — PLACEHOLDER TAXONOMY

Not validated against FSD's actual CRM or channel structure.
Revisit once system access is available. Flag in code comments.

### Channel Types (4)
```
CHN-01: Direct Sales
CHN-02: Distributor
CHN-03: OEM Contract
CHN-04: CDMO Key Account
```

### Key Accounts (22)
Direct pharma:
  KA-01: Pfizer (largest — strong GLP-1 pull from 2023)
  KA-02: Merck & Co
  KA-03: AstraZeneca
  KA-04: Roche
  KA-05: Novo Nordisk (GLP-1)
  KA-06: Lilly (GLP-1)
  KA-07: Sanofi
  KA-08: BMS
  KA-09: Biogen
  KA-10: Moderna (mRNA)
  KA-11: Amgen
  KA-12: J&J Biologics

Distribution:
  KA-13: VWR / Avantor (highest distribution volume)
  KA-14: Fisher Scientific
  KA-15: Sigma-Aldrich / Merck KGaA

OEM:
  KA-16: CATL (battery OEM, largest volume driver in DIV-03)
  KA-17: Samsung SDI
  KA-18: TSMC / UPW

CDMO:
  KA-19: Lonza
  KA-20: Catalent
  KA-21: Samsung Biologics
  KA-22: WuXi AppTec

---

## Site / Plant dimension  (net new in v5)

Three sites are real and confirmed from public FSD/Thermo Fisher materials.
Two are plausible European placeholders — `is_placeholder_site=True` means
they must never be presented as fact in the UI (only "illustrative" in tooltips).

```
SITE-01: Charlotte, NC      (real)   — Wave 1, cutover 2025-07-01, live_on_target
SITE-02: Maplewood, MN     (real)   — Wave 2, cutover 2025-10-01, in_flight
SITE-03: Frederick, MD     (real)   — Wave 2, cutover 2026-01-01, legacy
SITE-04: Düsseldorf, DE    (placeholder) — Wave 3, cutover 2026-04-01, legacy
SITE-05: Limerick, IE      (placeholder) — Wave 3, cutover 2026-07-01, legacy
```

ERP migration: SAP (3M/Solventum) → Oracle JD Edwards site-by-site.
Cutover date creates a visible step change in data_quality_score —
a dateable, legitimate level shift useful for teaching.

data_quality_score field in fact_financial_plan:
- Pre-cutover: 0.40–0.65 (missing records, duplicate GL entries, no SIOP tie-out)
- In-flight (last 90 days before cutover): degrades further (data freeze)
- Post-cutover: 0.85–1.0 (full JDE integration)

---

## Category hierarchy

### Major Categories (3)
- MCAT-01: Filtration Media
- MCAT-02: Systems & Devices
- MCAT-03: Membrane Products

### Categories (9)
- CAT-01: Depth Filtration         (MCAT-01)
- CAT-02: Sterile Filtration       (MCAT-01)
- CAT-03: Viral Clearance          (MCAT-01)
- CAT-04: Chromatography           (MCAT-02)
- CAT-05: Medical Device Filtration (MCAT-02)
- CAT-06: Industrial Filtration    (MCAT-02)
- CAT-07: Battery Separator Membranes (MCAT-03)
- CAT-08: UPW & Semiconductor Membranes (MCAT-03)
- CAT-09: Medical OEM Membranes    (MCAT-03)

---

## Time dimension (4-4-5 fiscal calendar — unchanged from v4)

See TASK_01 for 4-4-5 algorithm. Adds one new field:
- `is_pre_acquisition` (BOOL): True for dates before 2025-09-01
  (Solventum/3M era — legacy SIOP, lower data quality, 54% WFA baseline)

---

## Demand signal design

### Seasonality
B2B filtration is much flatter than CPG. Key drivers:
- Quarter-end purchasing effects (pharma budget cycles)
- Year-end inventory builds (distribution accounts)
- OEM: quarterly batch ordering from customer production schedule

### YoY growth
- DIV-01 Bioprocessing: +17%/yr (pharma investment, GLP-1 capacity build, cell & gene)
- DIV-02 Healthcare & Industrial: +6%/yr (stable)
- DIV-03 Membranes: +28%/yr (EV battery boom + semiconductor expansion)

### Demand spikes (engineered teaching examples)
- 2020 Q1-Q3: COVID-driven sterile filtration surge (2.2x for KA-13, KA-14, KA-01, KA-02)
- 2021 Q1-Q2: mRNA vaccine scale-up (1.6x for distribution + Moderna)
- 2022–2023: EV battery ramp (1.8x→2.1x for CATL, Samsung SDI)
- 2023–2024: GLP-1 demand pull (1.5x→1.7x for Novo Nordisk, Lilly, Pfizer)
- 2024: Semiconductor expansion (2.4x for OEM membrane accounts)

### Forecast accuracy / WFA calibration
FSD WFA baseline: 54% (MAPE ≈ 46%). Target: 75% within 12 months.

Noise std by year (LAG1):
- 2020: 0.56 | 2021: 0.54 | 2022: 0.51 | 2023: 0.48
- 2024: 0.45  | 2025: 0.38 | 2026: 0.32

Intentional biases:
- New SKU launches: over-forecast by ~18% in Budget (qualification uncertainty)
- Demand spikes (COVID, EV, GLP-1): under-forecast (missed by 1/spike_factor)

### inventory_entitlement_days (new field in fact_financial_plan)
Target DOH per category (right inventory in right place, not just "less inventory"):
- CAT-01 Depth: 70d | CAT-02 Sterile: 55d | CAT-03 Viral: 80d | CAT-04 Chroma: 90d
- CAT-05 MedDev: 45d | CAT-06 Industrial: 50d | CAT-07 Battery: 35d (JIT)
- CAT-08 UPW: 40d | CAT-09 MedOEM: 60d

Actual DOH is modeled at 1.1–1.6× entitlement (reflecting ~100 day actual inventory).

---

## File naming (unchanged from v4)

```
dimensions/dim_sku.csv
dimensions/dim_division.csv
dimensions/dim_brand.csv
dimensions/dim_product_line.csv
dimensions/dim_sub_product_line.csv
dimensions/dim_major_category.csv
dimensions/dim_category.csv
dimensions/dim_subcategory.csv
dimensions/dim_channel_type.csv
dimensions/dim_market.csv
dimensions/dim_customer_group.csv
dimensions/dim_key_account.csv
dimensions/dim_time.csv         ← adds is_pre_acquisition field
dimensions/dim_version.csv
dimensions/dim_promotion.csv
dimensions/dim_site.csv         ← new in v5
facts/fact_financial_plan_2020.csv  ← adds site_id, data_quality_score, inventory_entitlement_days
...
facts/fact_pos_weekly.csv
facts/fact_forecast_snapshot.csv
```

---

## Verification Checklist
- [ ] `grep -ril -iE "relatable|hugimals|WDYM|buzzed|incohearent" .` → no results
- [ ] `dim_sku.csv` has ~165 rows; all follow BRAND-PROD-NNN format
- [ ] ~20 SKUs have is_new_sku=True (post-TF-acquisition product introductions)
- [ ] `dim_site.csv` has 5 rows (3 real + 2 placeholder); is_placeholder_site correct
- [ ] `dim_time.csv` has is_pre_acquisition=True for dates before 2025-09-01
- [ ] `fact_financial_plan` has site_id, data_quality_score, inventory_entitlement_days cols
- [ ] data_quality_score for SITE-01 post-2025-07: avg > 0.85
- [ ] data_quality_score for SITE-03 (legacy): avg < 0.65
- [ ] WFA at LAG1: MAPE ≈ 45-50% for 2024 data (reflecting 54% baseline)
- [ ] Demand spike visible: DIV-03 2022-2023 units 2x vs 2021 for CATL/Samsung SDI
- [ ] GLP-1 pull visible: DIV-01 2023-2024 units +50% for Novo Nordisk, Lilly
- [ ] All files uploaded to gs://signal-raw-data/raw/
