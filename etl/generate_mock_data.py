"""
SIGNAL mock data generator — v6 (TASK_09 data model fixes)
Generates all dimension and fact CSVs for Thermo Fisher's Filtration & Separation Division.
Uploads to gs://signal-raw-data/raw/

v6 replaces the monolithic fact_financial_plan with six single-purpose fact
tables (nothing pre-merged, version/lag always derived downstream):
  1. fact_forecast_sellin_snapshot      SKU × Site × Channel × target_month × snapshot_date
  2. fact_forecast_sellthrough_snapshot SKU × Channel × target_month × snapshot_date (Dist/OEM only)
  3. fact_sellin_actuals                SKU × Site × Channel × month
  4. fact_sellthrough_actuals           SKU × Channel × month (Dist/OEM only)
  5. fact_financial_snapshot            Division × Channel × Category × target_month × snapshot_date
  6. fact_financial_actuals             Division × Channel × Category × month
Plus one ops-domain table (not one of the six): fact_site_data_quality.
Supply/inventory is explicitly OUT OF SCOPE here — follow-up task.
"""

import csv
import os
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from google.cloud import storage

random.seed(42)
np.random.seed(42)

OUT_DIR = Path(__file__).parent / "mock_data"
DIM_DIR = OUT_DIR / "dimensions"
FACT_DIR = OUT_DIR / "facts"
DIM_DIR.mkdir(parents=True, exist_ok=True)
FACT_DIR.mkdir(parents=True, exist_ok=True)

BUCKET_NAME = "signal-raw-data"

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                      str(Path(__file__).parent.parent / "secrets" / "signal-key.json"))


# ---------------------------------------------------------------------------
# GCS upload helper
# ---------------------------------------------------------------------------

def upload(local_path: Path, gcs_prefix: str = "raw"):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob_name = f"{gcs_prefix}/{local_path.parent.name}/{local_path.name}"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path), timeout=1800, checksum=None)
    print(f"  Uploaded {blob_name}")


def write_csv(path: Path, rows: list, fieldnames: list = None):
    if not rows:
        print(f"  WARNING: no rows for {path.name}")
        return
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Wrote {path.name}: {len(rows)} rows")


# ---------------------------------------------------------------------------
# Fiscal calendar helpers (4-4-5, year starts first Monday of February)
# Unchanged from v4 — architecture is sound.
# ---------------------------------------------------------------------------

WEEKS_PER_MONTH = [4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5]


def fiscal_year_start(year: int) -> date:
    feb1 = date(year, 2, 1)
    days_until_monday = (7 - feb1.weekday()) % 7
    return feb1 + timedelta(days=days_until_monday)


def build_fiscal_week_map(year_range=range(2019, 2028)):
    result = {}
    for yr in year_range:
        start = fiscal_year_start(yr)
        week_num = 0
        for m_idx, wk_count in enumerate(WEEKS_PER_MONTH):
            for w in range(wk_count):
                week_num += 1
                fq = m_idx // 3 + 1
                fm = m_idx + 1
                for d in range(7):
                    day = start + timedelta(weeks=(week_num - 1), days=d)
                    if day not in result:
                        result[day] = (yr, fq, fm, week_num)
    return result


FISCAL_MAP = build_fiscal_week_map()


def date_to_fiscal(d: date):
    if d in FISCAL_MAP:
        return FISCAL_MAP[d]
    return (d.year, (d.month - 1) // 3 + 1, d.month, 1)


# Thermo Fisher acquired Solventum P&F (becoming FSD) in Sept 2025.
# All data before this date is "pre-acquisition" (legacy Solventum/3M history).
ACQUISITION_DATE = date(2025, 9, 1)


# ---------------------------------------------------------------------------
# dim_time  (adds is_pre_acquisition flag)
# ---------------------------------------------------------------------------

def gen_dim_time():
    print("Generating dim_time...")
    fw_bounds = {}
    for yr in range(2019, 2028):
        start = fiscal_year_start(yr)
        week_num = 0
        for m_idx, wk_count in enumerate(WEEKS_PER_MONTH):
            for w in range(wk_count):
                week_num += 1
                fw_start = start + timedelta(weeks=(week_num - 1))
                fw_end = fw_start + timedelta(days=6)
                key = (yr, m_idx // 3 + 1, m_idx + 1, week_num)
                fw_bounds[key] = (fw_start, fw_end)

    rows = []
    d = date(2019, 1, 1)
    end = date(2026, 12, 31)
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    while d <= end:
        fy, fq, fm, fw = date_to_fiscal(d)
        key = (fy, fq, fm, fw)
        fw_start, fw_end = fw_bounds.get(key, (d, d))

        is_partial = fw_start.month != fw_end.month or fw_start.year != fw_end.year

        if is_partial:
            curr_month_days = sum(
                1 for i in range(7)
                if (fw_start + timedelta(days=i)).month == fw_end.month
                   and (fw_start + timedelta(days=i)).year == fw_end.year
            )
            prior_month_days = 7 - curr_month_days
            proration = round(curr_month_days / 7, 6)
        else:
            curr_month_days = 7
            prior_month_days = 0
            proration = 1.0

        rows.append({
            "date_id": d.isoformat(),
            "calendar_year": d.year,
            "calendar_quarter": (d.month - 1) // 3 + 1,
            "calendar_month": d.month,
            "calendar_month_name": month_names[d.month - 1],
            "calendar_week_of_year": d.isocalendar()[1],
            "day_of_week": d.isoweekday(),
            "is_weekend": d.isoweekday() >= 6,
            "fiscal_year": fy,
            "fiscal_quarter": fq,
            "fiscal_month": fm,
            "fiscal_week": fw,
            "fiscal_period_name": f"FY{fy}-Q{fq}-P{fm:02d}-W{fw:02d}",
            "fiscal_445_pattern": str(WEEKS_PER_MONTH[(fm - 1)]),
            "is_partial_week": is_partial,
            "partial_week_prior_month_days": prior_month_days,
            "partial_week_current_month_days": curr_month_days,
            "partial_week_proration_factor": proration,
            # True for all dates before TF acquisition close (Sept 2025).
            # Pre-acquisition data reflects legacy Solventum/3M planning processes —
            # lower data quality, no formal SIOP, WFA baseline of 54%.
            "is_pre_acquisition": d < ACQUISITION_DATE,
        })
        d += timedelta(days=1)

    path = DIM_DIR / "dim_time.csv"
    write_csv(path, rows)
    upload(path)
    return rows


# ---------------------------------------------------------------------------
# FSD business hierarchy dimensions
#
# Column names preserved from v4 schema (division_id / brand_id /
# product_line_id / sub_product_line_id) — the data model shape is unchanged;
# the content pivots from Relatable CPG to FSD filtration.
#
# Mapping:
#   division_id         → Business Line  (3 BLs)
#   brand_id            → Product Family (depth, sterile, chroma, viral, ...)
#   product_line_id     → Platform/Series
#   sub_product_line_id → Fine classification
# ---------------------------------------------------------------------------

DIVISIONS = [
    # (division_id, division_name)
    ("DIV-01", "Bioprocessing Filtration"),
    ("DIV-02", "Healthcare & Industrial Filtration"),
    # Demand driver is structurally different for Membranes: tracks the OEM customer's
    # production schedule, not end-patient/procedure volume. See gen_fact_financial_plan.
    ("DIV-03", "Membranes (incl. OEM)"),
]

BRANDS = [
    # (brand_id, product_family_name, division_id)
    ("BRD-01", "Depth Filtration",             "DIV-01"),
    ("BRD-02", "Membrane Sterile Filtration",   "DIV-01"),
    ("BRD-03", "Chromatographic Clarification", "DIV-01"),
    ("BRD-04", "Viral Clearance",               "DIV-01"),
    ("BRD-05", "Medical Device Filtration",     "DIV-02"),
    ("BRD-06", "Industrial Process Filtration", "DIV-02"),
    ("BRD-07", "OEM Membrane Media",            "DIV-03"),
    ("BRD-08", "Specialty Membranes",           "DIV-03"),
]

PRODUCT_LINES = [
    # (product_line_id, platform_series_name, brand_id)
    ("PL-01", "Clariflex™ Lenticular Series",       "BRD-01"),
    ("PL-02", "SingleClear™ Capsule Depth Filters", "BRD-01"),
    ("PL-03", "SterilPure™ PES Series",             "BRD-02"),
    ("PL-04", "SterilPure™ PVDF Series",            "BRD-02"),
    ("PL-05", "FlexFlow™ Sterilizing Capsules",     "BRD-02"),
    ("PL-06", "AEX-Pro™ Anion Exchange",            "BRD-03"),
    ("PL-07", "MixMode™ Multimodal Chromatography", "BRD-03"),
    ("PL-08", "ViralGuard™ Parvo-Retrovirus",       "BRD-04"),
    ("PL-09", "ParvoSure™ 20nm Filters",            "BRD-04"),
    ("PL-10", "MedLine™ Syringe Filters",           "BRD-05"),
    ("PL-11", "AirShield™ Venting Filters",         "BRD-05"),
    ("PL-12", "SafeFlow™ IV Line Filters",          "BRD-05"),
    ("PL-13", "InduPure™ Liquid Process Filters",   "BRD-06"),
    ("PL-14", "GasGuard™ Gas Filtration",           "BRD-06"),
    ("PL-15", "BattSep™ Battery Separator",         "BRD-07"),
    ("PL-16", "UPW-Mem™ Ultra-Pure Water",          "BRD-07"),
    ("PL-17", "MedOEM™ Medical OEM Membranes",      "BRD-07"),
    ("PL-18", "NanoFilt™ Specialty Filtration",     "BRD-08"),
]

SUB_PRODUCT_LINES = [
    ("SPL-01", "Lenticular Depth Sheets",         "PL-01"),
    ("SPL-02", "Lenticular Depth Pods",           "PL-01"),
    ("SPL-03", "Depth Filter Capsules Small",     "PL-02"),
    ("SPL-04", "Depth Filter Capsules Large",     "PL-02"),
    ("SPL-05", "0.2µm PES Sterilizing Filters",  "PL-03"),
    ("SPL-06", "0.45µm PES Clarifying Filters",  "PL-03"),
    ("SPL-07", "0.2µm PVDF Sterilizing",         "PL-04"),
    ("SPL-08", "0.45µm PVDF Clarifying",         "PL-04"),
    ("SPL-09", "Capsule Sterilizing Inline",      "PL-05"),
    ("SPL-10", "Capsule Sterilizing End-Use",     "PL-05"),
    ("SPL-11", "Strong AEX Resins",              "PL-06"),
    ("SPL-12", "Weak AEX Resins",               "PL-06"),
    ("SPL-13", "Mixed Mode Cation",              "PL-07"),
    ("SPL-14", "Mixed Mode Anion",               "PL-07"),
    ("SPL-15", "Parvo-Retrovirus Capsules",      "PL-08"),
    ("SPL-16", "Parvo-Retrovirus Cassettes",     "PL-08"),
    ("SPL-17", "20nm Parvo Filters",             "PL-09"),
    ("SPL-18", "Syringe Filters Sterile",        "PL-10"),
    ("SPL-19", "Syringe Filters Aqueous",        "PL-10"),
    ("SPL-20", "Hydrophobic Vent Filters",       "PL-11"),
    ("SPL-21", "Hydrophilic Vent Filters",       "PL-11"),
    ("SPL-22", "IV Line Filters 0.2µm",         "PL-12"),
    ("SPL-23", "IV Line Filters 1.2µm",         "PL-12"),
    ("SPL-24", "Bag Filters Industrial",         "PL-13"),
    ("SPL-25", "Cartridge Filters Industrial",   "PL-13"),
    ("SPL-26", "Process Gas Filters",            "PL-14"),
    ("SPL-27", "Compressed Air Filters",         "PL-14"),
    ("SPL-28", "Li-Ion Battery Separators",      "PL-15"),
    ("SPL-29", "Solid State Battery Separators", "PL-15"),
    ("SPL-30", "UPW Filtration Membranes",       "PL-16"),
    ("SPL-31", "Ultrapure Water Polishing",      "PL-16"),
    ("SPL-32", "Medical OEM Flat Sheet",         "PL-17"),
    ("SPL-33", "Medical OEM Hollow Fiber",       "PL-17"),
    ("SPL-34", "NanoFilt High-Performance",      "PL-18"),
    ("SPL-35", "NanoFilt Research Grade",        "PL-18"),
]

# ---------------------------------------------------------------------------
# Product category hierarchy (maps SKUs to filtration technology segments)
# ---------------------------------------------------------------------------

MAJOR_CATEGORIES = [
    ("MCAT-01", "Filtration Media"),
    ("MCAT-02", "Systems & Devices"),
    ("MCAT-03", "Membrane Products"),
]

CATEGORIES = [
    ("CAT-01", "Depth Filtration",              "MCAT-01"),
    ("CAT-02", "Sterile Filtration",            "MCAT-01"),
    ("CAT-03", "Viral Clearance",               "MCAT-01"),
    ("CAT-04", "Chromatography",                "MCAT-02"),
    ("CAT-05", "Medical Device Filtration",     "MCAT-02"),
    ("CAT-06", "Industrial Filtration",         "MCAT-02"),
    ("CAT-07", "Battery Separator Membranes",   "MCAT-03"),
    ("CAT-08", "UPW & Semiconductor Membranes", "MCAT-03"),
    ("CAT-09", "Medical OEM Membranes",         "MCAT-03"),
]

SUBCATEGORIES = [
    ("SCAT-01", "Lenticular Depth Filters",         "CAT-01"),
    ("SCAT-02", "Single-Use Depth Filter Capsules", "CAT-01"),
    ("SCAT-03", "PES Membrane Filters",             "CAT-02"),
    ("SCAT-04", "PVDF Membrane Filters",            "CAT-02"),
    ("SCAT-05", "Capsule Filters Sterilizing Grade","CAT-02"),
    ("SCAT-06", "Parvo-Retrovirus Filters",         "CAT-03"),
    ("SCAT-07", "20nm Virus Filters",               "CAT-03"),
    ("SCAT-08", "AEX Resins",                       "CAT-04"),
    ("SCAT-09", "Multimodal Resins",                "CAT-04"),
    ("SCAT-10", "Syringe Filters Medical",          "CAT-05"),
    ("SCAT-11", "Venting & Exhaust Filters",        "CAT-05"),
    ("SCAT-12", "IV Line Filters",                  "CAT-05"),
    ("SCAT-13", "Liquid Process Filters",           "CAT-06"),
    ("SCAT-14", "Gas Filtration",                   "CAT-06"),
    ("SCAT-15", "Li-Ion Battery Separators",        "CAT-07"),
    ("SCAT-16", "Solid State Battery Separators",   "CAT-07"),
    ("SCAT-17", "UPW Semiconductor Membranes",      "CAT-08"),
    ("SCAT-18", "Medical OEM Flat Sheet Membranes", "CAT-09"),
]

# ---------------------------------------------------------------------------
# Channel / geography hierarchy
#
# PLACEHOLDER TAXONOMY — inferred from public Thermo Fisher/FSD materials,
# not yet validated against FSD's actual CRM or channel structure.
# Revisit once system access is available.
# ---------------------------------------------------------------------------

CHANNEL_TYPES = [
    ("CHN-01", "Direct Sales"),
    ("CHN-02", "Distributor"),
    ("CHN-03", "OEM Contract"),
    ("CHN-04", "CDMO Key Account"),
]

MARKETS = [
    # (market_id, end_market_name, channel_type_id)
    ("MKT-01", "Large Pharma Direct",    "CHN-01"),
    ("MKT-02", "Biotech Direct",         "CHN-01"),
    ("MKT-03", "Global Distribution",    "CHN-02"),
    ("MKT-04", "Regional Distribution",  "CHN-02"),
    ("MKT-05", "Battery & EV OEM",       "CHN-03"),
    ("MKT-06", "Semiconductor OEM",      "CHN-03"),
    ("MKT-07", "Large CDMO",             "CHN-04"),
    ("MKT-08", "Specialty CDMO",         "CHN-04"),
]

CUSTOMER_GROUPS = [
    ("CG-01", "Global Top Pharma",    "MKT-01"),
    ("CG-02", "Mid-size Pharma",      "MKT-01"),
    ("CG-03", "Large Biotech",        "MKT-02"),
    ("CG-04", "Emerging Biotech",     "MKT-02"),
    ("CG-05", "Global Distribution",  "MKT-03"),
    ("CG-06", "Regional Distribution","MKT-04"),
    ("CG-07", "Battery OEM",          "MKT-05"),
    ("CG-08", "Semiconductor OEM",    "MKT-06"),
    ("CG-09", "Top-Tier CDMO",        "MKT-07"),
    ("CG-10", "Specialty CDMO",       "MKT-08"),
]

KEY_ACCOUNTS = [
    # (ka_id, account_name, customer_group_id, channel_type_id)
    # Direct pharma — largest buyers of bioprocessing filtration
    ("KA-01", "Pfizer",             "CG-01", "CHN-01"),
    ("KA-02", "Merck & Co",         "CG-01", "CHN-01"),
    ("KA-03", "AstraZeneca",        "CG-01", "CHN-01"),
    ("KA-04", "Roche",              "CG-01", "CHN-01"),
    ("KA-05", "Novo Nordisk",       "CG-01", "CHN-01"),
    ("KA-06", "Lilly",              "CG-02", "CHN-01"),
    ("KA-07", "Sanofi",             "CG-02", "CHN-01"),
    ("KA-08", "BMS",                "CG-01", "CHN-01"),
    ("KA-09", "Biogen",             "CG-03", "CHN-01"),
    ("KA-10", "Moderna",            "CG-03", "CHN-01"),
    ("KA-11", "Amgen",              "CG-03", "CHN-01"),
    ("KA-12", "J&J Biologics",      "CG-02", "CHN-01"),
    # Distributors
    ("KA-13", "VWR / Avantor",           "CG-05", "CHN-02"),
    ("KA-14", "Fisher Scientific",       "CG-05", "CHN-02"),
    ("KA-15", "Sigma-Aldrich / MKG",     "CG-05", "CHN-02"),
    # OEM — battery & semiconductor
    ("KA-16", "CATL",            "CG-07", "CHN-03"),
    ("KA-17", "Samsung SDI",     "CG-07", "CHN-03"),
    ("KA-18", "TSMC / UPW",     "CG-08", "CHN-03"),
    # CDMOs
    ("KA-19", "Lonza",              "CG-09", "CHN-04"),
    ("KA-20", "Catalent",           "CG-09", "CHN-04"),
    ("KA-21", "Samsung Biologics",  "CG-09", "CHN-04"),
    ("KA-22", "WuXi AppTec",        "CG-10", "CHN-04"),
]

KA_CHANNEL = {ka[0]: ka[3] for ka in KEY_ACCOUNTS}

# ---------------------------------------------------------------------------
# Site / Plant dimension  (net new — did not exist in v4)
#
# Three sites are real and confirmed from public FSD/Thermo Fisher materials:
# Charlotte NC, Maplewood MN, Frederick MD. European sites are plausible
# placeholders — is_placeholder_site=True means never present as fact in UI,
# only as "illustrative" in tooltips/legends.
#
# ERP migration: legacy SAP (inherited from 3M/Solventum) → Oracle JD Edwards.
# Migration waves are site-by-site; cutover dates create a visible data-quality
# step change — a real, dateable level-shift event useful for teaching the
# difference between legitimate signal and data artifact.
# ---------------------------------------------------------------------------

SITES = [
    # (site_id, site_name, city, state_or_region, country,
    #  business_lines_served, legacy_erp, target_erp,
    #  migration_wave, planned_cutover_date, migration_status, is_placeholder_site)
    ("SITE-01", "Charlotte Manufacturing Hub", "Charlotte",   "NC",      "US",
     "DIV-01|DIV-02", "SAP", "Oracle JDE/E1", 1, "2025-07-01", "live_on_target", False),
    ("SITE-02", "Maplewood Technology Center", "Maplewood",   "MN",      "US",
     "DIV-01|DIV-03", "SAP", "Oracle JDE/E1", 2, "2025-10-01", "in_flight",      False),
    ("SITE-03", "Frederick Operations",        "Frederick",   "MD",      "US",
     "DIV-02",        "SAP", "Oracle JDE/E1", 2, "2026-01-01", "legacy",          False),
    ("SITE-04", "Düsseldorf EMEA Hub",         "Düsseldorf",  "NRW",     "DE",
     "DIV-01|DIV-02", "SAP", "Oracle JDE/E1", 3, "2026-04-01", "legacy",          True),
    ("SITE-05", "Limerick Membrane Plant",     "Limerick",    "Munster", "IE",
     "DIV-03",        "SAP", "Oracle JDE/E1", 3, "2026-07-01", "legacy",          True),
]

# Map site → primary divisions and cutover date (for data quality scoring)
SITE_CUTOVER = {s[0]: date.fromisoformat(s[9]) for s in SITES}
SITE_STATUS   = {s[0]: s[10] for s in SITES}

# Primary site per division (simplified — one primary site, cross-ships possible)
DIV_PRIMARY_SITE = {
    "DIV-01": "SITE-01",
    "DIV-02": "SITE-03",
    "DIV-03": "SITE-02",
}

# ---------------------------------------------------------------------------
# SKU definitions
# ---------------------------------------------------------------------------

def build_skus():
    rows = []

    def sku(sku_id, name, div, brand, pl, spl, mcat, cat, scat,
            price, cost, launch, is_active=True, is_new=False):
        rows.append({
            "sku_id": sku_id,
            "sku_name": name,
            "division_id": div,
            "brand_id": brand,
            "product_line_id": pl,
            "sub_product_line_id": spl,
            "major_category_id": mcat,
            "category_id": cat,
            "subcategory_id": scat,
            "unit_cost": cost,
            "unit_price": price,
            "launch_date": launch,
            "is_active": is_active,
            "is_new_sku": is_new,
        })

    # ------------------------------------------------------------------
    # DIV-01 Bioprocessing Filtration
    # ------------------------------------------------------------------

    # BRD-01 Depth Filtration — Clariflex™ Lenticular (PL-01)
    # Sizes: 12", 16", 20" diameter; grades: T1, T2 (coarse→fine)
    sku("BPF-DFLT-001","Clariflex™ 12\" Depth Filter Sheet T1","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 145, 52, "2020-01-01")
    sku("BPF-DFLT-002","Clariflex™ 12\" Depth Filter Sheet T2","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 165, 60, "2020-01-01")
    sku("BPF-DFLT-003","Clariflex™ 16\" Depth Filter Sheet T1","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 245, 88, "2020-01-01")
    sku("BPF-DFLT-004","Clariflex™ 16\" Depth Filter Sheet T2","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 275, 99, "2020-01-01")
    sku("BPF-DFLT-005","Clariflex™ 20\" Depth Filter Sheet T1","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 395,142, "2020-01-01")
    sku("BPF-DFLT-006","Clariflex™ 20\" Depth Filter Sheet T2","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 435,157, "2020-01-01")
    sku("BPF-DFLT-007","Clariflex™ 20\" Depth Filter Pod XL",  "DIV-01","BRD-01","PL-01","SPL-02","MCAT-01","CAT-01","SCAT-01", 695,250, "2021-03-01")
    sku("BPF-DFLT-008","Clariflex™ 12\" Depth Filter Pod",     "DIV-01","BRD-01","PL-01","SPL-02","MCAT-01","CAT-01","SCAT-01", 325,117, "2021-03-01")
    sku("BPF-DFLT-009","Clariflex™ EC Grade Depth Sheet 16\"", "DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 310,112, "2022-06-01")
    sku("BPF-DFLT-010","Clariflex™ EC Grade Depth Sheet 20\"", "DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01", 480,173, "2022-06-01")

    # BRD-01 Depth Filtration — SingleClear™ Capsules (PL-02)
    sku("BPF-DFLT-011","SingleClear™ Depth Capsule 0.5L", "DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-02",  58,21, "2020-01-01")
    sku("BPF-DFLT-012","SingleClear™ Depth Capsule 1.5L", "DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-02",  95,34, "2020-01-01")
    sku("BPF-DFLT-013","SingleClear™ Depth Capsule 5L",   "DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-02", 185,67, "2020-06-01")
    sku("BPF-DFLT-014","SingleClear™ Depth Capsule 20L",  "DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-02", 420,151,"2020-06-01")
    sku("BPF-DFLT-015","SingleClear™ Depth Capsule 60L",  "DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-02", 850,306,"2021-01-01")
    sku("BPF-DFLT-016","SingleClear™ TF Grade Capsule 5L","DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-02", 215,77, "2022-03-01")
    sku("BPF-DFLT-017","SingleClear™ TF Grade Capsule 20L","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-02",475,171,"2022-03-01")
    # Post-acquisition new products: introduced after TF R&D resources applied
    sku("BPF-DFLT-018","SingleClear™ Next-Gen Capsule 5L", "DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-02",235,78, "2025-10-01", is_new=True)
    sku("BPF-DFLT-019","SingleClear™ Next-Gen Capsule 20L","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-02",510,169,"2025-10-01", is_new=True)

    # BRD-02 Sterile Filtration — SterilPure™ PES (PL-03)
    sku("BPF-STRL-001","SterilPure™ PES 0.2µm 47mm Disc",    "DIV-01","BRD-02","PL-03","SPL-05","MCAT-01","CAT-02","SCAT-03", 28,10, "2020-01-01")
    sku("BPF-STRL-002","SterilPure™ PES 0.2µm 142mm Disc",   "DIV-01","BRD-02","PL-03","SPL-05","MCAT-01","CAT-02","SCAT-03", 85,31, "2020-01-01")
    sku("BPF-STRL-003","SterilPure™ PES 0.2µm 10\" Cartridge","DIV-01","BRD-02","PL-03","SPL-05","MCAT-01","CAT-02","SCAT-03",145,52,"2020-01-01")
    sku("BPF-STRL-004","SterilPure™ PES 0.2µm 20\" Cartridge","DIV-01","BRD-02","PL-03","SPL-05","MCAT-01","CAT-02","SCAT-03",245,88,"2020-01-01")
    sku("BPF-STRL-005","SterilPure™ PES 0.45µm 10\" Cartridge","DIV-01","BRD-02","PL-03","SPL-06","MCAT-01","CAT-02","SCAT-03",135,49,"2020-01-01")
    sku("BPF-STRL-006","SterilPure™ PES 0.45µm 20\" Cartridge","DIV-01","BRD-02","PL-03","SPL-06","MCAT-01","CAT-02","SCAT-03",225,81,"2020-01-01")
    sku("BPF-STRL-007","SterilPure™ PES BioProcess 0.2µm 30\"","DIV-01","BRD-02","PL-03","SPL-05","MCAT-01","CAT-02","SCAT-03",385,139,"2021-06-01")
    sku("BPF-STRL-008","SterilPure™ PES 0.2µm EFA 1m²",       "DIV-01","BRD-02","PL-03","SPL-05","MCAT-01","CAT-02","SCAT-03",480,173,"2021-06-01")

    # BRD-02 Sterile Filtration — SterilPure™ PVDF (PL-04)
    sku("BPF-STRL-009","SterilPure™ PVDF 0.2µm 47mm Disc",    "DIV-01","BRD-02","PL-04","SPL-07","MCAT-01","CAT-02","SCAT-04", 32,12, "2020-01-01")
    sku("BPF-STRL-010","SterilPure™ PVDF 0.2µm 10\" Cartridge","DIV-01","BRD-02","PL-04","SPL-07","MCAT-01","CAT-02","SCAT-04",165,59,"2020-01-01")
    sku("BPF-STRL-011","SterilPure™ PVDF 0.2µm 20\" Cartridge","DIV-01","BRD-02","PL-04","SPL-07","MCAT-01","CAT-02","SCAT-04",275,99,"2020-01-01")
    sku("BPF-STRL-012","SterilPure™ PVDF 0.45µm 10\" Cartridge","DIV-01","BRD-02","PL-04","SPL-08","MCAT-01","CAT-02","SCAT-04",155,56,"2020-01-01")
    sku("BPF-STRL-013","SterilPure™ PVDF 0.45µm 20\" Cartridge","DIV-01","BRD-02","PL-04","SPL-08","MCAT-01","CAT-02","SCAT-04",260,94,"2020-01-01")

    # BRD-02 FlexFlow™ Sterilizing Capsules (PL-05)
    sku("BPF-STRL-014","FlexFlow™ Sterilizing Capsule 0.5L","DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-02","SCAT-05", 75,27,"2020-01-01")
    sku("BPF-STRL-015","FlexFlow™ Sterilizing Capsule 5L",  "DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-02","SCAT-05",195,70,"2020-01-01")
    sku("BPF-STRL-016","FlexFlow™ Sterilizing Capsule 20L", "DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-02","SCAT-05",445,160,"2021-01-01")
    sku("BPF-STRL-017","FlexFlow™ End-Use Capsule 0.2µm 1L","DIV-01","BRD-02","PL-05","SPL-10","MCAT-01","CAT-02","SCAT-05",110,40,"2021-06-01")
    sku("BPF-STRL-018","FlexFlow™ End-Use Capsule 0.2µm 5L","DIV-01","BRD-02","PL-05","SPL-10","MCAT-01","CAT-02","SCAT-05",245,88,"2021-06-01")
    # Post-acquisition new product: mRNA-optimized sterilizing filter
    sku("BPF-STRL-019","FlexFlow™ mRNA Grade Capsule 5L","DIV-01","BRD-02","PL-05","SPL-10","MCAT-01","CAT-02","SCAT-05",295,101,"2026-01-01", is_new=True)

    # BRD-03 Chromatographic Clarification — AEX-Pro™ (PL-06)
    sku("BPF-CHRO-001","AEX-Pro™ Strong Resin 100mL Pack", "DIV-01","BRD-03","PL-06","SPL-11","MCAT-02","CAT-04","SCAT-08",  480,168,"2020-01-01")
    sku("BPF-CHRO-002","AEX-Pro™ Strong Resin 1L Pack",    "DIV-01","BRD-03","PL-06","SPL-11","MCAT-02","CAT-04","SCAT-08", 3800,1330,"2020-01-01")
    sku("BPF-CHRO-003","AEX-Pro™ Strong Resin 5L Pack",    "DIV-01","BRD-03","PL-06","SPL-11","MCAT-02","CAT-04","SCAT-08",17500,6125,"2020-01-01")
    sku("BPF-CHRO-004","AEX-Pro™ Weak Resin 100mL Pack",   "DIV-01","BRD-03","PL-06","SPL-12","MCAT-02","CAT-04","SCAT-08",  420,147,"2020-01-01")
    sku("BPF-CHRO-005","AEX-Pro™ Weak Resin 1L Pack",      "DIV-01","BRD-03","PL-06","SPL-12","MCAT-02","CAT-04","SCAT-08", 3200,1120,"2020-01-01")
    sku("BPF-CHRO-006","AEX-Pro™ Polishing Column 50mL",   "DIV-01","BRD-03","PL-06","SPL-11","MCAT-02","CAT-04","SCAT-08",  650,228,"2021-03-01")
    sku("BPF-CHRO-007","AEX-Pro™ Polishing Column 500mL",  "DIV-01","BRD-03","PL-06","SPL-11","MCAT-02","CAT-04","SCAT-08", 5200,1820,"2021-03-01")

    # BRD-03 Chromatographic Clarification — MixMode™ (PL-07)
    sku("BPF-CHRO-008","MixMode™ Cation Resin 100mL",  "DIV-01","BRD-03","PL-07","SPL-13","MCAT-02","CAT-04","SCAT-09",  520,182,"2020-01-01")
    sku("BPF-CHRO-009","MixMode™ Cation Resin 1L",     "DIV-01","BRD-03","PL-07","SPL-13","MCAT-02","CAT-04","SCAT-09", 4100,1435,"2020-01-01")
    sku("BPF-CHRO-010","MixMode™ Anion Resin 100mL",   "DIV-01","BRD-03","PL-07","SPL-14","MCAT-02","CAT-04","SCAT-09",  490,172,"2020-06-01")
    sku("BPF-CHRO-011","MixMode™ Anion Resin 1L",      "DIV-01","BRD-03","PL-07","SPL-14","MCAT-02","CAT-04","SCAT-09", 3900,1365,"2020-06-01")
    sku("BPF-CHRO-012","MixMode™ HCP Reduction Column","DIV-01","BRD-03","PL-07","SPL-14","MCAT-02","CAT-04","SCAT-09", 6800,2380,"2022-01-01")
    # Post-acquisition: TF-developed next-gen resin
    sku("BPF-CHRO-013","MixMode™ Next-Gen Cation 1L","DIV-01","BRD-03","PL-07","SPL-13","MCAT-02","CAT-04","SCAT-09",4500,1440,"2026-03-01", is_new=True)

    # BRD-04 Viral Clearance — ViralGuard™ (PL-08)
    sku("BPF-VIRL-001","ViralGuard™ Parvo Filter 25cm²",  "DIV-01","BRD-04","PL-08","SPL-15","MCAT-01","CAT-03","SCAT-06", 890,312, "2020-01-01")
    sku("BPF-VIRL-002","ViralGuard™ Parvo Filter 100cm²", "DIV-01","BRD-04","PL-08","SPL-15","MCAT-01","CAT-03","SCAT-06",2800,980, "2020-01-01")
    sku("BPF-VIRL-003","ViralGuard™ Parvo Capsule 0.1m²", "DIV-01","BRD-04","PL-08","SPL-15","MCAT-01","CAT-03","SCAT-06",3500,1225,"2020-01-01")
    sku("BPF-VIRL-004","ViralGuard™ Parvo Cassette 1m²",  "DIV-01","BRD-04","PL-08","SPL-16","MCAT-01","CAT-03","SCAT-06",8500,2975,"2021-01-01")
    sku("BPF-VIRL-005","ViralGuard™ Retrovirus Filter 100cm²","DIV-01","BRD-04","PL-08","SPL-15","MCAT-01","CAT-03","SCAT-06",3200,1120,"2021-06-01")

    # BRD-04 Viral Clearance — ParvoSure™ 20nm (PL-09)
    sku("BPF-VIRL-006","ParvoSure™ 20nm Filter 25cm²", "DIV-01","BRD-04","PL-09","SPL-17","MCAT-01","CAT-03","SCAT-07",1200, 420,"2020-01-01")
    sku("BPF-VIRL-007","ParvoSure™ 20nm Filter 100cm²","DIV-01","BRD-04","PL-09","SPL-17","MCAT-01","CAT-03","SCAT-07",4200,1470,"2020-01-01")
    sku("BPF-VIRL-008","ParvoSure™ 20nm Capsule 0.1m²","DIV-01","BRD-04","PL-09","SPL-17","MCAT-01","CAT-03","SCAT-07",4800,1680,"2020-06-01")
    sku("BPF-VIRL-009","ParvoSure™ 20nm Cassette 1m²", "DIV-01","BRD-04","PL-09","SPL-17","MCAT-01","CAT-03","SCAT-07",11000,3850,"2021-01-01")
    # Post-acquisition: enhanced 19nm product
    sku("BPF-VIRL-010","ParvoSure™ Plus 19nm Capsule 0.1m²","DIV-01","BRD-04","PL-09","SPL-17","MCAT-01","CAT-03","SCAT-07",5600,1790,"2026-01-01", is_new=True)

    # ------------------------------------------------------------------
    # DIV-02 Healthcare & Industrial Filtration
    # ------------------------------------------------------------------

    # BRD-05 Medical Device Filtration — MedLine™ Syringe Filters (PL-10)
    sku("HIF-MEDF-001","MedLine™ Syringe Filter PVDF 0.22µm 13mm",  "DIV-02","BRD-05","PL-10","SPL-18","MCAT-02","CAT-05","SCAT-10", 12,  4, "2020-01-01")
    sku("HIF-MEDF-002","MedLine™ Syringe Filter PVDF 0.22µm 25mm",  "DIV-02","BRD-05","PL-10","SPL-18","MCAT-02","CAT-05","SCAT-10", 18,  7, "2020-01-01")
    sku("HIF-MEDF-003","MedLine™ Syringe Filter PES 0.22µm 25mm",   "DIV-02","BRD-05","PL-10","SPL-18","MCAT-02","CAT-05","SCAT-10", 15,  6, "2020-01-01")
    sku("HIF-MEDF-004","MedLine™ Syringe Filter Nylon 0.45µm 25mm", "DIV-02","BRD-05","PL-10","SPL-19","MCAT-02","CAT-05","SCAT-10", 14,  5, "2020-01-01")
    sku("HIF-MEDF-005","MedLine™ Syringe Filter MCE 0.45µm 47mm",   "DIV-02","BRD-05","PL-10","SPL-19","MCAT-02","CAT-05","SCAT-10", 22,  8, "2020-01-01")
    sku("HIF-MEDF-006","MedLine™ Syringe Filter PTFE 0.22µm 13mm",  "DIV-02","BRD-05","PL-10","SPL-18","MCAT-02","CAT-05","SCAT-10", 20,  7, "2021-01-01")
    sku("HIF-MEDF-007","MedLine™ Syringe Filter PTFE 0.45µm 25mm",  "DIV-02","BRD-05","PL-10","SPL-19","MCAT-02","CAT-05","SCAT-10", 24,  9, "2021-01-01")
    sku("HIF-MEDF-008","MedLine™ Bulk Pack PVDF 0.22µm 25mm 100ct", "DIV-02","BRD-05","PL-10","SPL-18","MCAT-02","CAT-05","SCAT-10",145, 52, "2021-06-01")
    sku("HIF-MEDF-009","MedLine™ Bulk Pack PES 0.22µm 25mm 100ct",  "DIV-02","BRD-05","PL-10","SPL-18","MCAT-02","CAT-05","SCAT-10",125, 45, "2021-06-01")

    # BRD-05 Medical Device — AirShield™ Venting Filters (PL-11)
    sku("HIF-MEDF-010","AirShield™ Vent Filter PTFE 0.2µm 10mm", "DIV-02","BRD-05","PL-11","SPL-20","MCAT-02","CAT-05","SCAT-11", 35, 13,"2020-01-01")
    sku("HIF-MEDF-011","AirShield™ Vent Filter PTFE 0.2µm 25mm", "DIV-02","BRD-05","PL-11","SPL-20","MCAT-02","CAT-05","SCAT-11", 52, 19,"2020-01-01")
    sku("HIF-MEDF-012","AirShield™ Vent Filter PTFE 0.2µm 50mm", "DIV-02","BRD-05","PL-11","SPL-20","MCAT-02","CAT-05","SCAT-11", 85, 31,"2020-01-01")
    sku("HIF-MEDF-013","AirShield™ Hydrophilic Vent 0.2µm 25mm", "DIV-02","BRD-05","PL-11","SPL-21","MCAT-02","CAT-05","SCAT-11", 58, 21,"2021-01-01")

    # BRD-05 Medical Device — SafeFlow™ IV Filters (PL-12)
    sku("HIF-MEDF-014","SafeFlow™ IV Filter 0.2µm In-Line",     "DIV-02","BRD-05","PL-12","SPL-22","MCAT-02","CAT-05","SCAT-12", 45, 16,"2020-01-01")
    sku("HIF-MEDF-015","SafeFlow™ IV Filter 0.2µm Luer Lock",   "DIV-02","BRD-05","PL-12","SPL-22","MCAT-02","CAT-05","SCAT-12", 55, 20,"2020-01-01")
    sku("HIF-MEDF-016","SafeFlow™ IV Filter 1.2µm Lipid Guard",  "DIV-02","BRD-05","PL-12","SPL-23","MCAT-02","CAT-05","SCAT-12", 65, 23,"2020-01-01")
    sku("HIF-MEDF-017","SafeFlow™ IV Filter 1.2µm Gravity Set",  "DIV-02","BRD-05","PL-12","SPL-23","MCAT-02","CAT-05","SCAT-12", 72, 26,"2020-01-01")
    sku("HIF-MEDF-018","SafeFlow™ IV Filter 0.2µm Add-On",       "DIV-02","BRD-05","PL-12","SPL-22","MCAT-02","CAT-05","SCAT-12", 42, 15,"2021-06-01")

    # BRD-06 Industrial Process — InduPure™ Liquid (PL-13)
    sku("HIF-INDF-001","InduPure™ Bag Filter 5µm P1 Size 1",    "DIV-02","BRD-06","PL-13","SPL-24","MCAT-02","CAT-06","SCAT-13", 38,14,"2020-01-01")
    sku("HIF-INDF-002","InduPure™ Bag Filter 5µm P1 Size 2",    "DIV-02","BRD-06","PL-13","SPL-24","MCAT-02","CAT-06","SCAT-13", 48,17,"2020-01-01")
    sku("HIF-INDF-003","InduPure™ Cartridge 5µm 10\" PP",       "DIV-02","BRD-06","PL-13","SPL-25","MCAT-02","CAT-06","SCAT-13", 42,15,"2020-01-01")
    sku("HIF-INDF-004","InduPure™ Cartridge 1µm 10\" PP",       "DIV-02","BRD-06","PL-13","SPL-25","MCAT-02","CAT-06","SCAT-13", 48,17,"2020-01-01")
    sku("HIF-INDF-005","InduPure™ Cartridge 0.2µm 20\" PES",    "DIV-02","BRD-06","PL-13","SPL-25","MCAT-02","CAT-06","SCAT-13",125,45,"2020-01-01")
    sku("HIF-INDF-006","InduPure™ Strainer Element 50µm",       "DIV-02","BRD-06","PL-13","SPL-24","MCAT-02","CAT-06","SCAT-13", 85,31,"2021-01-01")
    sku("HIF-INDF-007","InduPure™ High-Flow Cartridge 5µm 40\"","DIV-02","BRD-06","PL-13","SPL-25","MCAT-02","CAT-06","SCAT-13",195,70,"2021-06-01")
    sku("HIF-INDF-008","InduPure™ High-Flow Cartridge 1µm 40\"","DIV-02","BRD-06","PL-13","SPL-25","MCAT-02","CAT-06","SCAT-13",215,77,"2021-06-01")
    sku("HIF-INDF-009","InduPure™ Pleated Cartridge 0.45µm 30\"","DIV-02","BRD-06","PL-13","SPL-25","MCAT-02","CAT-06","SCAT-13",155,56,"2022-01-01")
    sku("HIF-INDF-010","InduPure™ Pleated Cartridge 0.2µm 30\"","DIV-02","BRD-06","PL-13","SPL-25","MCAT-02","CAT-06","SCAT-13",175,63,"2022-01-01")

    # BRD-06 Industrial — GasGuard™ (PL-14)
    sku("HIF-INDF-011","GasGuard™ Process Gas Filter 0.2µm 10\"","DIV-02","BRD-06","PL-14","SPL-26","MCAT-02","CAT-06","SCAT-14",135,49,"2020-01-01")
    sku("HIF-INDF-012","GasGuard™ Process Gas Filter 0.2µm 20\"","DIV-02","BRD-06","PL-14","SPL-26","MCAT-02","CAT-06","SCAT-14",225,81,"2020-01-01")
    sku("HIF-INDF-013","GasGuard™ Compressed Air Filter 0.2µm", "DIV-02","BRD-06","PL-14","SPL-27","MCAT-02","CAT-06","SCAT-14", 98,35,"2020-01-01")
    sku("HIF-INDF-014","GasGuard™ Sterile Vent PTFE 0.2µm 20\"","DIV-02","BRD-06","PL-14","SPL-27","MCAT-02","CAT-06","SCAT-14",195,70,"2021-01-01")
    sku("HIF-INDF-015","GasGuard™ High-Flow Vent Filter 1µm 30\"","DIV-02","BRD-06","PL-14","SPL-27","MCAT-02","CAT-06","SCAT-14",245,88,"2022-03-01")

    # ------------------------------------------------------------------
    # DIV-03 Membranes (incl. OEM)
    # Demand driver: tracks customer's production schedule, not end-patient volume.
    # ------------------------------------------------------------------

    # BRD-07 OEM Membrane Media — BattSep™ Battery Separators (PL-15)
    # Large-volume, production-schedule-driven; EV battery boom from 2022
    sku("MEM-OEMM-001","BattSep™ Li-Ion Separator 15µm 1m² Roll",  "DIV-03","BRD-07","PL-15","SPL-28","MCAT-03","CAT-07","SCAT-15", 42,15,"2020-01-01")
    sku("MEM-OEMM-002","BattSep™ Li-Ion Separator 12µm 1m² Roll",  "DIV-03","BRD-07","PL-15","SPL-28","MCAT-03","CAT-07","SCAT-15", 55,20,"2020-01-01")
    sku("MEM-OEMM-003","BattSep™ Li-Ion Separator 9µm 1m² Roll",   "DIV-03","BRD-07","PL-15","SPL-28","MCAT-03","CAT-07","SCAT-15", 72,26,"2021-01-01")
    sku("MEM-OEMM-004","BattSep™ Coated Separator 15µm 1m² Roll",  "DIV-03","BRD-07","PL-15","SPL-28","MCAT-03","CAT-07","SCAT-15", 68,24,"2021-06-01")
    sku("MEM-OEMM-005","BattSep™ Solid-State Precursor 20µm 1m²",  "DIV-03","BRD-07","PL-15","SPL-29","MCAT-03","CAT-07","SCAT-16",125,43,"2022-06-01")
    sku("MEM-OEMM-006","BattSep™ Solid-State Composite 15µm 1m²",  "DIV-03","BRD-07","PL-15","SPL-29","MCAT-03","CAT-07","SCAT-16",175,61,"2022-09-01")
    sku("MEM-OEMM-007","BattSep™ Next-Gen Solid-State 10µm 1m²",   "DIV-03","BRD-07","PL-15","SPL-29","MCAT-03","CAT-07","SCAT-16",220,77,"2023-06-01")
    # Post-acquisition next-gen
    sku("MEM-OEMM-008","BattSep™ Nano-Coat Separator 9µm 1m² Roll","DIV-03","BRD-07","PL-15","SPL-28","MCAT-03","CAT-07","SCAT-15", 85,28,"2025-10-01", is_new=True)

    # BRD-07 OEM — UPW-Mem™ Ultra-Pure Water (PL-16)
    sku("MEM-OEMM-009","UPW-Mem™ Ultrafiltration 10kDa 1m²",  "DIV-03","BRD-07","PL-16","SPL-30","MCAT-03","CAT-08","SCAT-17",185,65,"2020-01-01")
    sku("MEM-OEMM-010","UPW-Mem™ Ultrafiltration 30kDa 1m²",  "DIV-03","BRD-07","PL-16","SPL-30","MCAT-03","CAT-08","SCAT-17",165,58,"2020-01-01")
    sku("MEM-OEMM-011","UPW-Mem™ Nanofiltration 200Da 1m²",   "DIV-03","BRD-07","PL-16","SPL-31","MCAT-03","CAT-08","SCAT-17",245,86,"2020-06-01")
    sku("MEM-OEMM-012","UPW-Mem™ RO Membrane Semiconductor 1m²","DIV-03","BRD-07","PL-16","SPL-31","MCAT-03","CAT-08","SCAT-17",320,112,"2021-01-01")
    sku("MEM-OEMM-013","UPW-Mem™ Polishing UF 5kDa 1m²",      "DIV-03","BRD-07","PL-16","SPL-30","MCAT-03","CAT-08","SCAT-17",215,75,"2022-01-01")
    sku("MEM-OEMM-014","UPW-Mem™ High-Flux UF Spiral 4040",    "DIV-03","BRD-07","PL-16","SPL-31","MCAT-03","CAT-08","SCAT-17",480,168,"2022-06-01")

    # BRD-07 OEM — MedOEM™ Medical OEM Membranes (PL-17)
    sku("MEM-OEMM-015","MedOEM™ PES Flat Sheet 0.2µm 1m²",  "DIV-03","BRD-07","PL-17","SPL-32","MCAT-03","CAT-09","SCAT-18", 95,33,"2020-01-01")
    sku("MEM-OEMM-016","MedOEM™ PVDF Flat Sheet 0.2µm 1m²", "DIV-03","BRD-07","PL-17","SPL-32","MCAT-03","CAT-09","SCAT-18",115,40,"2020-01-01")
    sku("MEM-OEMM-017","MedOEM™ Hollow Fiber UF PES 1m²",   "DIV-03","BRD-07","PL-17","SPL-33","MCAT-03","CAT-09","SCAT-18",245,86,"2020-01-01")
    sku("MEM-OEMM-018","MedOEM™ Hollow Fiber MF PP 1m²",    "DIV-03","BRD-07","PL-17","SPL-33","MCAT-03","CAT-09","SCAT-18",185,65,"2021-01-01")
    sku("MEM-OEMM-019","MedOEM™ Hemodialysis Membrane 1m²", "DIV-03","BRD-07","PL-17","SPL-33","MCAT-03","CAT-09","SCAT-18",380,133,"2021-06-01")
    sku("MEM-OEMM-020","MedOEM™ Oxygenator Membrane 1m²",   "DIV-03","BRD-07","PL-17","SPL-33","MCAT-03","CAT-09","SCAT-18",520,182,"2022-01-01")

    # BRD-08 Specialty Membranes — NanoFilt™ (PL-18)
    sku("MEM-SPEC-001","NanoFilt™ High-Performance PVDF 0.1µm 1m²","DIV-03","BRD-08","PL-18","SPL-34","MCAT-03","CAT-08","SCAT-17",185,65,"2020-01-01")
    sku("MEM-SPEC-002","NanoFilt™ High-Performance PES 0.05µm 1m²","DIV-03","BRD-08","PL-18","SPL-34","MCAT-03","CAT-08","SCAT-17",225,79,"2020-01-01")
    sku("MEM-SPEC-003","NanoFilt™ Research Grade PTFE 0.1µm 1m²",  "DIV-03","BRD-08","PL-18","SPL-35","MCAT-03","CAT-08","SCAT-17",295,103,"2020-01-01")
    sku("MEM-SPEC-004","NanoFilt™ Research Grade PVDF 0.02µm 1m²", "DIV-03","BRD-08","PL-18","SPL-35","MCAT-03","CAT-08","SCAT-17",385,135,"2020-01-01")
    sku("MEM-SPEC-005","NanoFilt™ Ceramic Alumina 0.2µm Disc",      "DIV-03","BRD-08","PL-18","SPL-34","MCAT-03","CAT-08","SCAT-17",145,51,"2021-06-01")
    sku("MEM-SPEC-006","NanoFilt™ Ceramic Titania 0.05µm Disc",     "DIV-03","BRD-08","PL-18","SPL-34","MCAT-03","CAT-08","SCAT-17",185,65,"2021-06-01")
    sku("MEM-SPEC-007","NanoFilt™ Track-Etched PC 0.4µm 25mm",      "DIV-03","BRD-08","PL-18","SPL-35","MCAT-03","CAT-08","SCAT-17", 28,10,"2020-01-01")
    sku("MEM-SPEC-008","NanoFilt™ Track-Etched PC 0.2µm 25mm",      "DIV-03","BRD-08","PL-18","SPL-35","MCAT-03","CAT-08","SCAT-17", 35,12,"2020-01-01")
    sku("MEM-SPEC-009","NanoFilt™ Track-Etched PC 0.1µm 47mm",      "DIV-03","BRD-08","PL-18","SPL-35","MCAT-03","CAT-08","SCAT-17", 68,24,"2021-01-01")
    sku("MEM-SPEC-010","NanoFilt™ Fluoropolymer PTFE 0.1µm 1m²",   "DIV-03","BRD-08","PL-18","SPL-34","MCAT-03","CAT-08","SCAT-17",420,147,"2022-01-01")
    # Post-acquisition specialty products
    sku("MEM-SPEC-011","NanoFilt™ ALD-Coated Membrane 0.01µm 1m²","DIV-03","BRD-08","PL-18","SPL-34","MCAT-03","CAT-08","SCAT-17",680,218,"2026-01-01", is_new=True)
    sku("MEM-SPEC-012","NanoFilt™ Graphene Oxide Membrane 1m²",    "DIV-03","BRD-08","PL-18","SPL-34","MCAT-03","CAT-08","SCAT-17",850,272,"2026-03-01", is_new=True)

    return rows


# ---------------------------------------------------------------------------
# Snapshot calendar (TASK_09)
#
# One snapshot per month, dated the 3rd Friday of that month. version
# (Budget / LE01–LE11) and lag_months are NEVER stored columns — they are
# always derived downstream (BigQuery view / DAX) from snapshot_date vs
# target_period_date. A stored label can silently drift out of sync with
# the dates next to it (the LAG1-LAG10 bug this task removes).
#
# Cycle rules (FSD planning cadence):
# - December snapshot sets Budget for all 12 months of the NEXT year.
# - Jan..Nov snapshots re-forecast the remaining months of the CURRENT
#   year (derived labels LE01..LE11). December has no LE cycle — by then
#   only one month of the fiscal year remains (no LE12).
# ---------------------------------------------------------------------------

# Demo "as of" boundary: data ends at the June 2026 planning cycle.
ACTUALS_THROUGH = date(2026, 6, 30)   # last month with realized actuals
LAST_SNAPSHOT   = date(2026, 6, 30)   # last snapshot cycle that has run


def third_friday(year: int, month: int) -> date:
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7   # Friday == weekday 4
    return first + timedelta(days=offset + 14)


def snapshots_for_target(year: int, month: int) -> list:
    """All snapshot dates that forecast target month (year, month)."""
    snaps = [third_friday(year - 1, 12)]                       # Budget cycle
    snaps += [third_friday(year, m) for m in range(1, month)]  # LE cycles
    return [s for s in snaps if date(2019, 12, 1) <= s <= LAST_SNAPSHOT]


def lag_between(snapshot: date, target: date) -> int:
    """Whole months between snapshot month and target month (derived, never stored)."""
    return (target.year - snapshot.year) * 12 + (target.month - snapshot.month)


# ---------------------------------------------------------------------------
# dim_promotion  (FSD-appropriate planning events)
# ---------------------------------------------------------------------------

PROMO_TEMPLATES = [
    # (name_base, type, ka_id, m1, m2, lift_lo, lift_hi)
    ("INTERPHEX Conference Volume Commitment",   "ConferenceCommitment", "KA-01",  4,  5, 0.12, 0.25),
    ("BIO International Qualifier Campaign",     "QualificationPush",   "KA-09",  6,  7, 0.15, 0.30),
    ("Annual Contract Renewal — Pfizer",         "ContractRenewal",      "KA-01",  1,  2, 0.08, 0.20),
    ("Annual Contract Renewal — Merck",          "ContractRenewal",      "KA-02",  1,  2, 0.08, 0.20),
    ("Battery OEM Volume Ramp — CATL",           "OEMVolumeRamp",        "KA-16",None,None,0.20,0.45),
    ("Year-End Inventory Build — Distribution",  "InventoryBuild",       "KA-13", 11, 12, 0.10, 0.22),
    ("GLP-1 Scale-Up Pull — Large Pharma",       "DemandPull",           "KA-05",  7,  9, 0.18, 0.35),
    ("Pandemic Surge — Sterile Filtration",      "EmergencyPull",        "KA-14",  3,  6, 0.30, 0.60),
    ("mRNA Platform Qualification Campaign",     "QualificationPush",    "KA-10",  8,  9, 0.15, 0.30),
]

PROMO_SKUS = {
    "INTERPHEX Conference Volume Commitment":  ["BPF-DFLT-001","BPF-DFLT-003","BPF-STRL-003","BPF-VIRL-001"],
    "BIO International Qualifier Campaign":   ["BPF-CHRO-001","BPF-CHRO-008","BPF-VIRL-006","BPF-STRL-001"],
    "Annual Contract Renewal — Pfizer":       ["BPF-DFLT-001","BPF-STRL-003","BPF-VIRL-002","BPF-CHRO-002"],
    "Annual Contract Renewal — Merck":        ["BPF-DFLT-003","BPF-STRL-007","BPF-VIRL-003","BPF-CHRO-009"],
    "Battery OEM Volume Ramp — CATL":         ["MEM-OEMM-001","MEM-OEMM-002","MEM-OEMM-003","MEM-OEMM-004"],
    "Year-End Inventory Build — Distribution":["HIF-MEDF-001","HIF-MEDF-002","HIF-INDF-003","HIF-INDF-004"],
    "GLP-1 Scale-Up Pull — Large Pharma":     ["BPF-DFLT-013","BPF-DFLT-014","BPF-STRL-014","BPF-STRL-015"],
    "Pandemic Surge — Sterile Filtration":    ["BPF-STRL-003","BPF-STRL-004","BPF-STRL-014","BPF-STRL-015","BPF-VIRL-001"],
    "mRNA Platform Qualification Campaign":   ["BPF-STRL-016","BPF-STRL-017","BPF-VIRL-006","BPF-VIRL-007"],
}


def gen_promotions():
    rows = []
    pid = 1
    for year in range(2020, 2027):
        for tmpl in PROMO_TEMPLATES:
            name_base, ptype, ka, m1, m2, lift_lo, lift_hi = tmpl
            # Pandemic surge only relevant 2020-2021
            if name_base == "Pandemic Surge — Sterile Filtration" and year > 2021:
                continue
            # GLP-1 pull starts 2023
            if name_base == "GLP-1 Scale-Up Pull — Large Pharma" and year < 2023:
                continue
            name = f"{name_base} {year}"
            if m1 is None:
                m1 = random.randint(2, 8)
                m2 = m1 + random.randint(1, 3)
            end_m = min(m2, 12)
            start = date(year, m1, 1)
            end   = date(year, end_m, 28 if end_m == 2 else 30)
            skus  = PROMO_SKUS.get(name_base, ["BPF-DFLT-001"])
            for sku_id in skus:
                rows.append({
                    "promotion_id":      f"PROMO-{pid:04d}",
                    "promotion_name":    name,
                    "promotion_type":    ptype,
                    "start_date":        start.isoformat(),
                    "end_date":          end.isoformat(),
                    "sku_id":            sku_id,
                    "key_account_id":    ka,
                    "expected_lift_pct": round(random.uniform(lift_lo, lift_hi), 3),
                })
                pid += 1
    return rows


# ---------------------------------------------------------------------------
# SKU-account assignment
# ---------------------------------------------------------------------------

def build_sku_account_pairs(sku_rows):
    direct_kas = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-01"]
    dist_kas   = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-02"]
    oem_kas    = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-03"]
    cdmo_kas   = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-04"]

    pairs = []
    for s in sku_rows:
        sid = s["sku_id"]
        div = s["division_id"]
        assigned = set()

        if div == "DIV-01":
            # Bioprocessing: direct pharma + CDMOs + distribution
            assigned.update(direct_kas)
            assigned.update(cdmo_kas)
            assigned.update(random.sample(dist_kas, k=2))
        elif div == "DIV-02":
            # Healthcare & Industrial: distribution-heavy + select direct
            assigned.update(dist_kas)
            assigned.update(random.sample(direct_kas, k=random.randint(3, 5)))
        else:
            # Membranes / OEM: OEM accounts + select distribution; minimal direct
            assigned.update(oem_kas)
            assigned.update(random.sample(dist_kas, k=2))
            assigned.update(random.sample(direct_kas, k=2))

        for ka_id in assigned:
            pairs.append((sid, ka_id))

    return pairs


# ---------------------------------------------------------------------------
# Demand signals
# ---------------------------------------------------------------------------

# B2B filtration seasonality: much flatter than CPG.
# Quarter-end effects, annual budget releases, year-end builds.
SEASONALITY = {
    "CAT-01": np.array([1.05,0.90,1.10,1.05,0.95,1.00,0.95,1.00,1.10,1.00,1.05,1.10]),  # depth filtration
    "CAT-02": np.array([1.10,0.95,1.15,1.05,0.95,1.00,0.95,1.00,1.10,1.00,1.05,1.15]),  # sterile filtration
    "CAT-03": np.array([1.00,0.90,1.05,1.00,0.95,1.05,1.00,1.00,1.10,1.05,1.00,1.05]),  # viral clearance
    "CAT-04": np.array([1.05,0.90,1.10,1.00,0.95,1.05,1.00,0.95,1.10,1.00,1.00,1.10]),  # chromatography
    "CAT-05": np.array([1.05,0.90,1.05,1.00,1.00,1.00,0.95,1.00,1.05,1.00,1.05,1.10]),  # medical device
    "CAT-06": np.array([1.00,0.90,1.05,1.00,1.00,1.00,1.00,1.00,1.05,1.00,1.00,1.05]),  # industrial
    # OEM: driven by customer production schedule — quarterly batch ordering
    "CAT-07": np.array([1.00,1.20,0.90,1.20,0.90,1.10,1.20,0.90,1.10,1.20,0.90,1.10]),  # battery separators
    "CAT-08": np.array([1.00,1.10,1.00,1.10,1.00,1.00,1.10,1.00,1.00,1.10,1.00,1.00]),  # UPW/semiconductor
    "CAT-09": np.array([1.00,0.95,1.05,1.00,1.00,1.05,1.00,1.00,1.05,1.00,1.00,1.05]),  # medical OEM
}

ACCOUNT_BASE = {
    "KA-01": 380,  # Pfizer — largest pharma buyer
    "KA-02": 310,  # Merck
    "KA-03": 280,  # AstraZeneca
    "KA-04": 300,  # Roche
    "KA-05": 260,  # Novo Nordisk (GLP-1 surge driver)
    "KA-06": 220,  # Lilly (GLP-1 surge driver)
    "KA-07": 200,  # Sanofi
    "KA-08": 195,  # BMS
    "KA-09": 175,  # Biogen
    "KA-10": 140,  # Moderna
    "KA-11": 180,  # Amgen
    "KA-12": 210,  # J&J Biologics
    "KA-13": 750,  # VWR/Avantor — distribution volume
    "KA-14": 700,  # Fisher Scientific
    "KA-15": 580,  # Sigma-Aldrich
    "KA-16":1100,  # CATL — battery OEM, high volume
    "KA-17": 850,  # Samsung SDI
    "KA-18": 480,  # TSMC/UPW
    "KA-19": 320,  # Lonza CDMO
    "KA-20": 260,  # Catalent
    "KA-21": 240,  # Samsung Biologics
    "KA-22": 185,  # WuXi
}

YOY_GROWTH = {
    "DIV-01": 0.17,  # Bioprocessing: strong pharma/GLP-1/cell-gene demand
    "DIV-02": 0.06,  # Healthcare & Industrial: stable
    "DIV-03": 0.28,  # Membranes: EV battery boom + semiconductor expansion
}

# Demand spikes: pandemic surge (sterile filt 2020-2021), GLP-1 ramp (2023+),
# EV battery ramp (2022+), mRNA platform scale (2021-2022)
DEMAND_SPIKES = [
    # (div_id, year, m1, m2, multiplier, ka_ids)
    ("DIV-01", 2020,  3,  8, 2.2, ["KA-13","KA-14","KA-01","KA-02"]),  # COVID sterile filt
    ("DIV-01", 2021,  1,  6, 1.6, ["KA-13","KA-14","KA-10"]),           # mRNA vaccine
    ("DIV-03", 2022,  1, 12, 1.8, ["KA-16","KA-17"]),                   # EV ramp
    ("DIV-03", 2023,  1, 12, 2.1, ["KA-16","KA-17"]),                   # EV acceleration
    ("DIV-01", 2023,  6, 12, 1.5, ["KA-05","KA-06","KA-01"]),           # GLP-1 Ozempic/Mounjaro
    ("DIV-01", 2024,  1, 12, 1.7, ["KA-05","KA-06","KA-01","KA-02"]),   # GLP-1 continued
    ("DIV-03", 2024,  1, 12, 2.4, ["KA-16","KA-17","KA-18"]),           # semiconductor+EV
]


def get_spike_mult(div_id, year, month, ka_id):
    mult = 1.0
    for sdiv, yr, m1, m2, m, kas in DEMAND_SPIKES:
        if sdiv == div_id and yr == year and m1 <= month <= m2 and ka_id in kas:
            mult = max(mult, m)
    return mult


def sku_volume_scale(sku_id):
    """Volume scaling relative to ACCOUNT_BASE (category × format size effect)."""
    if sku_id.startswith("BPF-DFLT") and "001" <= sku_id[-3:] <= "010":
        return 0.65  # lenticular sheets — bulk but lower per-account
    if sku_id.startswith("BPF-DFLT"):
        return 0.55  # capsules
    if sku_id.startswith("BPF-STRL"):
        return 0.80  # sterile filtration — high volume
    if sku_id.startswith("BPF-CHRO") and "001" <= sku_id[-3:] <= "007":
        return 0.20  # AEX resins — high value, lower unit count
    if sku_id.startswith("BPF-CHRO"):
        return 0.18  # mixed-mode resins
    if sku_id.startswith("BPF-VIRL"):
        return 0.12  # viral clearance — very high value, low unit count
    if sku_id.startswith("HIF-MEDF") and "008" <= sku_id[-3:] <= "009":
        return 1.20  # bulk packs — higher volume
    if sku_id.startswith("HIF-MEDF"):
        return 0.90
    if sku_id.startswith("HIF-INDF"):
        return 0.70
    if sku_id.startswith("MEM-OEMM") and sku_id[8:12] in ("001,","002,","003,","004,"):
        return 1.50  # battery separators — OEM volume
    if sku_id.startswith("MEM-OEMM"):
        return 1.20
    if sku_id.startswith("MEM-SPEC"):
        return 0.40
    return 0.60


def base_units(sku_id, ka_id, cat_id, div_id, year, month, sku_info):
    launch = date.fromisoformat(sku_info["launch_date"])
    months_since = (year - launch.year) * 12 + (month - launch.month)
    if months_since < 0:
        return 0.0

    # B2B filtration: no strong lifecycle decay (consumables with repeat orders)
    if months_since == 0:
        ramp = 0.40  # initial qualification period, low orders
    elif months_since <= 3:
        ramp = 0.65  # qualification + first orders
    elif months_since <= 8:
        ramp = 0.88  # ramp toward steady state
    else:
        ramp = 1.00  # steady state — consumable, recurring demand

    # OEM/Membrane demand: driven by customer production schedule
    if div_id == "DIV-03":
        ka_ch = KA_CHANNEL.get(ka_id, "")
        if ka_ch not in ("CHN-02", "CHN-03"):
            ramp *= 0.60  # membranes primarily via OEM + distribution channels

    base   = ACCOUNT_BASE.get(ka_id, 150) * sku_volume_scale(sku_id)
    season = SEASONALITY.get(cat_id, np.ones(12))
    seas   = season[month - 1]
    growth = (1 + YOY_GROWTH.get(div_id, 0.10)) ** max(0, year - 2020)
    spike  = get_spike_mult(div_id, year, month, ka_id)

    units  = base * ramp * seas * growth * spike
    units *= random.uniform(0.90, 1.10)
    return max(0.0, units)


# ---------------------------------------------------------------------------
# Data quality score per site  (models ERP migration wave effect)
# ---------------------------------------------------------------------------

def site_data_quality(site_id: str, period_date: date) -> float:
    """
    Pre-cutover: SAP data has missing/delayed records, duplicate GL entries,
    and no formal SIOP tie-out. Score degrades toward cutover.
    Post-cutover: JDE data quality visibly improves (real, dateable level shift).
    This is a teaching example: legitimate level shift vs. timing artifact.
    """
    cutover = SITE_CUTOVER[site_id]
    status  = SITE_STATUS[site_id]

    if status == "live_on_target":
        base = 0.92 if period_date >= cutover else 0.55
    elif status == "in_flight":
        if period_date >= cutover:
            base = 0.88
        else:
            # Degrades in the 3 months before cutover (data freeze prep)
            days_to_cutover = (cutover - period_date).days
            if days_to_cutover <= 90:
                base = max(0.40, 0.62 - (90 - days_to_cutover) * 0.002)
            else:
                base = 0.62
    else:  # legacy
        base = 0.50

    return round(min(1.0, max(0.20, base + random.uniform(-0.05, 0.05))), 3)


# ---------------------------------------------------------------------------
# WFA-calibrated noise  (54% baseline at LAG1, improving toward 75% by 2026)
#
# WFA ≈ 1 - MAPE.  E[|X|] ≈ std * 0.798 for normal distribution.
# To get WFA=54% (MAPE=46%): std ≈ 0.46/0.798 ≈ 0.576
# To get WFA=75% (MAPE=25%): std ≈ 0.25/0.798 ≈ 0.313
# ---------------------------------------------------------------------------

def lag_noise(lag: int, year: int) -> float:
    """Year-dependent noise standard deviation to model 54%→75% WFA improvement."""
    # Base noise at LAG1 by year; higher lags add proportional noise
    lag1_by_year = {2020: 0.56, 2021: 0.54, 2022: 0.51, 2023: 0.48,
                    2024: 0.45, 2025: 0.38, 2026: 0.32}
    base = lag1_by_year.get(year, 0.45)
    # Each additional lag adds ~0.03 noise (less improvement available at longer horizons)
    return max(0.05, base + (lag - 1) * 0.03)


# ---------------------------------------------------------------------------
# Channel rollup + underlying demand  (TASK_09)
#
# Facts are stored at Channel grain (not key account). Key-account detail
# stays a dimension concern; demand is rolled up over each SKU's assigned
# accounts per channel type.
# ---------------------------------------------------------------------------

SELLTHROUGH_CHANNELS = ("CHN-02", "CHN-03")   # Distributor, OEM Contract only


def build_channel_pairs(pairs):
    """Roll SKU×KA assignments up to SKU×Channel, keeping the KA list."""
    chan = {}
    for sku_id, ka_id in pairs:
        chan.setdefault((sku_id, KA_CHANNEL[ka_id]), []).append(ka_id)
    return chan


def build_demand(sku_rows, chan_pairs):
    """Underlying monthly sell-in demand: (sku, channel, year, month) -> units.

    Generated for the full 2020–2026 horizon. Rows after ACTUALS_THROUGH
    exist only as the 'truth' that forecasts are noisy versions of — they
    are never written to the actuals tables.
    """
    sku_map = {s["sku_id"]: s for s in sku_rows}
    demand  = {}
    for (sku_id, ch), kas in chan_pairs.items():
        s = sku_map[sku_id]
        for year in range(2020, 2027):
            for month in range(1, 13):
                units = sum(
                    base_units(sku_id, ka, s["category_id"], s["division_id"],
                               year, month, s)
                    for ka in kas
                )
                if units > 0:
                    demand[(sku_id, ch, year, month)] = units
    return demand


def sellthrough_base(demand, sku_id, ch, year, month):
    """Sell-through lags sell-in via the intermediary's inventory buffer."""
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    cur  = demand.get((sku_id, ch, year, month), 0.0)
    prev = demand.get((sku_id, ch, prev_y, prev_m), 0.0)
    if cur == 0 and prev == 0:
        return 0.0
    return 0.55 * cur + 0.45 * prev


def channel_spike_mult(div_id, year, month, kas):
    """Spike multiplier at channel grain = strongest spike among its accounts."""
    return max(get_spike_mult(div_id, year, month, ka) for ka in kas)


def forecast_units_for(actual, lag, year, is_new_launch, spike):
    """One forecast draw. Noise grows with lag → longer-lag forecasts are
    systematically less accurate (verification checklist requirement)."""
    if is_new_launch:
        bias = 1.18                      # new launches: over-forecast
    elif spike > 1.5:
        bias = 1.0 / spike * 1.2         # demand spikes: miss the surge
    else:
        bias = 1.0
    noise = lag_noise(lag, year)
    return max(0.0, actual * bias * (1 + random.gauss(0, noise)))


# ---------------------------------------------------------------------------
# The six fact tables — nothing pre-merged, no stored version/lag columns.
# ---------------------------------------------------------------------------

def gen_fact_sellin_actuals(sku_rows, demand):
    print("Generating fact_sellin_actuals...")
    sku_map = {s["sku_id"]: s for s in sku_rows}
    rows = []
    for (sku_id, ch, year, month), units in sorted(demand.items()):
        period = date(year, month, 1)
        if period > ACTUALS_THROUGH:
            continue
        rows.append({
            "sku_id":          sku_id,
            "site_id":         DIV_PRIMARY_SITE[sku_map[sku_id]["division_id"]],
            "channel_type_id": ch,
            "period_date":     period.isoformat(),
            "actual_units":    round(units, 1),
        })
    path = FACT_DIR / "fact_sellin_actuals.csv"
    write_csv(path, rows)
    upload(path)


def gen_fact_sellthrough_actuals(sku_rows, demand, chan_pairs):
    print("Generating fact_sellthrough_actuals...")
    rows = []
    for (sku_id, ch) in sorted(chan_pairs):
        if ch not in SELLTHROUGH_CHANNELS:
            continue   # Direct Sales / CDMO have no intermediary layer: no rows
        for year in range(2020, 2027):
            for month in range(1, 13):
                period = date(year, month, 1)
                if period > ACTUALS_THROUGH:
                    continue
                base = sellthrough_base(demand, sku_id, ch, year, month)
                if base <= 0:
                    continue
                rows.append({
                    "sku_id":          sku_id,
                    "channel_type_id": ch,
                    "period_date":     period.isoformat(),
                    "actual_units":    round(base * random.uniform(0.92, 1.06), 1),
                })
    path = FACT_DIR / "fact_sellthrough_actuals.csv"
    write_csv(path, rows)
    upload(path)


def gen_fact_forecast_sellin_snapshot(sku_rows, demand, chan_pairs):
    print("Generating fact_forecast_sellin_snapshot...")
    sku_map = {s["sku_id"]: s for s in sku_rows}
    rows = []
    for (sku_id, ch), kas in sorted(chan_pairs.items()):
        s      = sku_map[sku_id]
        launch = date.fromisoformat(s["launch_date"])
        div_id = s["division_id"]
        site   = DIV_PRIMARY_SITE[div_id]
        for year in range(2020, 2027):
            is_new_launch = (launch.year == year)
            for month in range(1, 13):
                actual = demand.get((sku_id, ch, year, month), 0.0)
                if actual == 0:
                    continue
                target = date(year, month, 1)
                spike  = channel_spike_mult(div_id, year, month, kas)
                for snap in snapshots_for_target(year, month):
                    lag = lag_between(snap, target)
                    fcst = forecast_units_for(actual, lag, year, is_new_launch, spike)
                    rows.append({
                        "sku_id":             sku_id,
                        "site_id":            site,
                        "channel_type_id":    ch,
                        "target_period_date": target.isoformat(),
                        "snapshot_date":      snap.isoformat(),
                        "forecast_units":     round(fcst, 1),
                    })
    path = FACT_DIR / "fact_forecast_sellin_snapshot.csv"
    write_csv(path, rows)
    upload(path)


def gen_fact_forecast_sellthrough_snapshot(sku_rows, demand, chan_pairs):
    print("Generating fact_forecast_sellthrough_snapshot...")
    sku_map = {s["sku_id"]: s for s in sku_rows}
    rows = []
    for (sku_id, ch), kas in sorted(chan_pairs.items()):
        if ch not in SELLTHROUGH_CHANNELS:
            continue
        s      = sku_map[sku_id]
        launch = date.fromisoformat(s["launch_date"])
        div_id = s["division_id"]
        for year in range(2020, 2027):
            is_new_launch = (launch.year == year)
            for month in range(1, 13):
                base = sellthrough_base(demand, sku_id, ch, year, month)
                if base <= 0:
                    continue
                target = date(year, month, 1)
                spike  = channel_spike_mult(div_id, year, month, kas)
                for snap in snapshots_for_target(year, month):
                    # Sell-through visibility is worse than sell-in: the
                    # intermediary's reporting adds noise on top of lag noise.
                    lag  = lag_between(snap, target)
                    fcst = forecast_units_for(base, lag, year, is_new_launch, spike)
                    fcst *= random.uniform(0.97, 1.03)
                    rows.append({
                        "sku_id":             sku_id,
                        "channel_type_id":    ch,
                        "target_period_date": target.isoformat(),
                        "snapshot_date":      snap.isoformat(),
                        "forecast_units":     round(fcst, 1),
                    })
    path = FACT_DIR / "fact_forecast_sellthrough_snapshot.csv"
    write_csv(path, rows)
    upload(path)


# ---------------------------------------------------------------------------
# Financial tables — finance's own coarser grain (Division × Channel ×
# Category). No SKU, no units, anywhere. Dollars only.
# ---------------------------------------------------------------------------

def build_financial(sku_rows, demand):
    """Aggregate underlying demand to finance grain: (div, ch, cat, y, m) -> [rev, cost]."""
    sku_map = {s["sku_id"]: s for s in sku_rows}
    fin = {}
    for (sku_id, ch, year, month), units in demand.items():
        s = sku_map[sku_id]
        key = (s["division_id"], ch, s["category_id"], year, month)
        acc = fin.setdefault(key, [0.0, 0.0])
        acc[0] += units * s["unit_price"]
        acc[1] += units * s["unit_cost"]
    return fin


def fin_noise(lag: int) -> float:
    """Financial plan noise by lag — coarser grain, lower relative noise than
    SKU-level demand, but still monotonically worse at longer horizons."""
    return 0.03 + 0.012 * lag


def gen_fact_financial_actuals(fin):
    print("Generating fact_financial_actuals...")
    rows = []
    for (div, ch, cat, year, month), (rev, cost) in sorted(fin.items()):
        period = date(year, month, 1)
        if period > ACTUALS_THROUGH:
            continue
        # Small GL-level adjustments: financial actuals never tie perfectly
        # to demand units × list price (rebates, accruals, FX).
        rev_a  = round(rev  * random.uniform(0.97, 1.01), 2)
        cost_a = round(cost * random.uniform(0.98, 1.02), 2)
        rows.append({
            "division_id":     div,
            "channel_type_id": ch,
            "category_id":     cat,
            "period_date":     period.isoformat(),
            "revenue":         rev_a,
            "cost":            cost_a,
            "margin":          round(rev_a - cost_a, 2),
        })
    path = FACT_DIR / "fact_financial_actuals.csv"
    write_csv(path, rows)
    upload(path)


def gen_fact_financial_snapshot(fin):
    print("Generating fact_financial_snapshot...")
    rows = []
    for (div, ch, cat, year, month), (rev, cost) in sorted(fin.items()):
        target = date(year, month, 1)
        for snap in snapshots_for_target(year, month):
            lag   = lag_between(snap, target)
            noise = fin_noise(lag)
            # Budget cycle (December snapshot) carries planning optimism.
            optimism = 1.06 if snap.month == 12 else 1.0
            rev_f  = round(max(0.0, rev  * optimism * (1 + random.gauss(0, noise))), 2)
            cost_f = round(max(0.0, cost * optimism * (1 + random.gauss(0, noise * 0.85))), 2)
            rows.append({
                "division_id":        div,
                "channel_type_id":    ch,
                "category_id":        cat,
                "target_period_date": target.isoformat(),
                "snapshot_date":      snap.isoformat(),
                "revenue":            rev_f,
                "cost":               cost_f,
                "margin":             round(rev_f - cost_f, 2),
            })
    path = FACT_DIR / "fact_financial_snapshot.csv"
    write_csv(path, rows)
    upload(path)


# ---------------------------------------------------------------------------
# fact_site_data_quality — ops domain, NOT one of the six demand/financial
# tables. Keeps the Act-4 ERP-migration story alive after data_quality_score
# was removed from the fact tables (they carry exactly their spec'd fields).
# ---------------------------------------------------------------------------

def gen_fact_site_data_quality():
    print("Generating fact_site_data_quality...")
    rows = []
    for site_id, *_ in SITES:
        for year in range(2020, 2027):
            for month in range(1, 13):
                period = date(year, month, 1)
                if period > ACTUALS_THROUGH:
                    continue
                rows.append({
                    "site_id":            site_id,
                    "period_date":        period.isoformat(),
                    "data_quality_score": site_data_quality(site_id, period),
                })
    path = FACT_DIR / "fact_site_data_quality.csv"
    write_csv(path, rows)
    upload(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== SIGNAL mock data generator v6 — TASK_09 data model fixes ===")

    print("\n[1/16] dim_time")
    gen_dim_time()

    print("\n[2/16] dim_division  (Business Lines)")
    rows = [{"division_id": d[0], "division_name": d[1]} for d in DIVISIONS]
    p = DIM_DIR / "dim_division.csv"; write_csv(p, rows); upload(p)

    print("\n[3/16] dim_brand  (Product Families)")
    rows = [{"brand_id": b[0], "brand_name": b[1], "division_id": b[2]} for b in BRANDS]
    p = DIM_DIR / "dim_brand.csv"; write_csv(p, rows); upload(p)

    print("\n[4/16] dim_product_line  (Platform / Series)")
    rows = [{"product_line_id": pl[0], "product_line_name": pl[1], "brand_id": pl[2]} for pl in PRODUCT_LINES]
    p = DIM_DIR / "dim_product_line.csv"; write_csv(p, rows); upload(p)

    print("\n[5/16] dim_sub_product_line  (Fine classification)")
    rows = [{"sub_product_line_id": s[0], "sub_product_line_name": s[1], "product_line_id": s[2]} for s in SUB_PRODUCT_LINES]
    p = DIM_DIR / "dim_sub_product_line.csv"; write_csv(p, rows); upload(p)

    print("\n[6/16] dim_major_category")
    rows = [{"major_category_id": m[0], "major_category_name": m[1]} for m in MAJOR_CATEGORIES]
    p = DIM_DIR / "dim_major_category.csv"; write_csv(p, rows); upload(p)

    print("\n[7/16] dim_category")
    rows = [{"category_id": c[0], "category_name": c[1], "major_category_id": c[2]} for c in CATEGORIES]
    p = DIM_DIR / "dim_category.csv"; write_csv(p, rows); upload(p)

    print("\n[8/16] dim_subcategory")
    rows = [{"subcategory_id": s[0], "subcategory_name": s[1], "category_id": s[2]} for s in SUBCATEGORIES]
    p = DIM_DIR / "dim_subcategory.csv"; write_csv(p, rows); upload(p)

    print("\n[9/16] dim_channel_type  (PLACEHOLDER — not yet validated vs. FSD CRM)")
    rows = [{"channel_type_id": c[0], "channel_type_name": c[1]} for c in CHANNEL_TYPES]
    p = DIM_DIR / "dim_channel_type.csv"; write_csv(p, rows); upload(p)

    print("\n[10/16] dim_market  (End-Markets — PLACEHOLDER)")
    rows = [{"market_id": m[0], "market_name": m[1], "channel_type_id": m[2]} for m in MARKETS]
    p = DIM_DIR / "dim_market.csv"; write_csv(p, rows); upload(p)

    print("\n[11/16] dim_customer_group")
    rows = [{"customer_group_id": c[0], "customer_group_name": c[1], "market_id": c[2]} for c in CUSTOMER_GROUPS]
    p = DIM_DIR / "dim_customer_group.csv"; write_csv(p, rows); upload(p)

    print("\n[12/16] dim_key_account")
    rows = [{"key_account_id": k[0], "key_account_name": k[1], "customer_group_id": k[2], "channel_type_id": k[3]} for k in KEY_ACCOUNTS]
    p = DIM_DIR / "dim_key_account.csv"; write_csv(p, rows); upload(p)

    print("\n[13/16] dim_sku")
    sku_rows = build_skus()
    p = DIM_DIR / "dim_sku.csv"; write_csv(p, sku_rows); upload(p)
    print(f"  Total SKUs: {len(sku_rows)}")

    # dim_version is intentionally GONE in v6 (TASK_09): version labels
    # (Budget/LE01-LE11) and lag_months are derived from snapshot_date vs
    # target_period_date in views/DAX, never stored.

    print("\n[14/16] dim_promotion")
    rows = gen_promotions()
    p = DIM_DIR / "dim_promotion.csv"; write_csv(p, rows); upload(p)

    print("\n[15/16] dim_site  (Manufacturing sites — 3 real + 2 placeholder)")
    site_rows = []
    for s in SITES:
        site_rows.append({
            "site_id":                s[0],
            "site_name":              s[1],
            "city":                   s[2],
            "state_or_region":        s[3],
            "country":                s[4],
            "business_lines_served":  s[5],
            "legacy_erp":             s[6],
            "target_erp":             s[7],
            "migration_wave":         s[8],
            "planned_cutover_date":   s[9],
            "migration_status":       s[10],
            "is_placeholder_site":    s[11],
        })
    p = DIM_DIR / "dim_site.csv"; write_csv(p, site_rows); upload(p)

    print("\n[16/16] SKU-account pairs -> channel rollup -> underlying demand")
    pairs      = build_sku_account_pairs(sku_rows)
    chan_pairs = build_channel_pairs(pairs)
    demand     = build_demand(sku_rows, chan_pairs)
    print(f"  KA pairs: {len(pairs)} | SKU-channel combos: {len(chan_pairs)} | demand cells: {len(demand)}")

    print("\n[FACT 1/6] fact_forecast_sellin_snapshot")
    gen_fact_forecast_sellin_snapshot(sku_rows, demand, chan_pairs)

    print("\n[FACT 2/6] fact_forecast_sellthrough_snapshot  (Distributor/OEM only)")
    gen_fact_forecast_sellthrough_snapshot(sku_rows, demand, chan_pairs)

    print("\n[FACT 3/6] fact_sellin_actuals")
    gen_fact_sellin_actuals(sku_rows, demand)

    print("\n[FACT 4/6] fact_sellthrough_actuals  (Distributor/OEM only)")
    gen_fact_sellthrough_actuals(sku_rows, demand, chan_pairs)

    print("\n[FACT 5/6 + 6/6] financial snapshot + actuals  (Division × Channel × Category, dollars only)")
    fin = build_financial(sku_rows, demand)
    gen_fact_financial_snapshot(fin)
    gen_fact_financial_actuals(fin)

    print("\n[OPS] fact_site_data_quality  (ERP migration story — not one of the six)")
    gen_fact_site_data_quality()

    print("\n=== v6 complete ===")
    new_skus = [s for s in sku_rows if s["is_new_sku"]]
    print(f"Post-acquisition new SKUs: {len(new_skus)}, Total SKUs: {len(sku_rows)}, "
          f"SKU-channel combos: {len(chan_pairs)}")
    print("NOTE: supply/inventory facts intentionally NOT generated — separate follow-up task.")


if __name__ == "__main__":
    main()
