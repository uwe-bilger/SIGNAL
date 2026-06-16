"""
SIGNAL mock data generator — v4 (based on verified Relatable interview facts)
Generates all dimension and fact CSVs, uploads to gs://signal-raw-data/raw/
"""

import csv
import math
import os
import random
import uuid
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
# ---------------------------------------------------------------------------

WEEKS_PER_MONTH = [4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5]  # 12 fiscal months


def fiscal_year_start(year: int) -> date:
    feb1 = date(year, 2, 1)
    days_until_monday = (7 - feb1.weekday()) % 7
    return feb1 + timedelta(days=days_until_monday)


def build_fiscal_week_map(year_range=range(2019, 2028)):
    """Returns dict: date -> (fiscal_year, fiscal_quarter, fiscal_month, fiscal_week)"""
    result = {}
    for yr in year_range:
        start = fiscal_year_start(yr)
        week_num = 0
        for m_idx, wk_count in enumerate(WEEKS_PER_MONTH):
            for w in range(wk_count):
                week_num += 1
                fq = m_idx // 3 + 1
                fm = m_idx + 1
                fw = week_num
                for d in range(7):
                    day = start + timedelta(weeks=(week_num - 1), days=d)
                    if day not in result:
                        result[day] = (yr, fq, fm, fw)
    return result


FISCAL_MAP = build_fiscal_week_map()


def date_to_fiscal(d: date):
    if d in FISCAL_MAP:
        return FISCAL_MAP[d]
    return (d.year, (d.month - 1) // 3 + 1, d.month, 1)


# ---------------------------------------------------------------------------
# dim_time
# ---------------------------------------------------------------------------

def gen_dim_time():
    print("Generating dim_time...")
    # Build per-fiscal-week bounds: (fy, fq, fm, fw) -> (start_date, end_date)
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
    month_names = ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"]

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

        pattern = str(WEEKS_PER_MONTH[(fm - 1)])

        iso_week = d.isocalendar()[1]

        rows.append({
            "date_id": d.isoformat(),
            "calendar_year": d.year,
            "calendar_quarter": (d.month - 1) // 3 + 1,
            "calendar_month": d.month,
            "calendar_month_name": month_names[d.month - 1],
            "calendar_week_of_year": iso_week,
            "day_of_week": d.isoweekday(),
            "is_weekend": d.isoweekday() >= 6,
            "fiscal_year": fy,
            "fiscal_quarter": fq,
            "fiscal_month": fm,
            "fiscal_week": fw,
            "fiscal_period_name": f"FY{fy}-Q{fq}-P{fm:02d}-W{fw:02d}",
            "fiscal_445_pattern": pattern,
            "is_partial_week": is_partial,
            "partial_week_prior_month_days": prior_month_days,
            "partial_week_current_month_days": curr_month_days,
            "partial_week_proration_factor": proration,
        })
        d += timedelta(days=1)

    path = DIM_DIR / "dim_time.csv"
    write_csv(path, rows)
    upload(path)
    return rows


# ---------------------------------------------------------------------------
# Dimension tables
# ---------------------------------------------------------------------------

DIVISIONS = [
    ("DIV-01", "Games & Play"),
    ("DIV-02", "Lifestyle & Comfort"),
    ("DIV-03", "Hugimals World"),
]

BRANDS = [
    ("BRD-01", "What Do You Meme?", "DIV-01"),
    ("BRD-02", "Buzzed", "DIV-01"),
    ("BRD-03", "Relatable Originals", "DIV-01"),
    ("BRD-04", "Bee Street Games", "DIV-01"),
    ("BRD-05", "Hunt A Killer", "DIV-01"),
    ("BRD-06", "Lifestyle & Comfort", "DIV-02"),
    ("BRD-07", "Hugimals World", "DIV-03"),
]

PRODUCT_LINES = [
    ("PL-01", "WDYM Core & Family", "BRD-01"),
    ("PL-02", "WDYM Expansion Packs", "BRD-01"),
    ("PL-03", "WDYM Licensed & Collab", "BRD-01"),
    ("PL-04", "WDYM Party & Social", "BRD-01"),
    ("PL-05", "Buzzed Core & Expansions", "BRD-02"),
    ("PL-06", "Buzzed Accessories", "BRD-02"),
    ("PL-07", "Relatable Party Games", "BRD-03"),
    ("PL-08", "Relatable Family & Kids", "BRD-03"),
    ("PL-09", "Relatable Outdoor & Novelty", "BRD-03"),
    ("PL-10", "Relatable Wellness", "BRD-03"),
    ("PL-11", "Bee Street Games", "BRD-04"),
    ("PL-12", "Hunt A Killer", "BRD-05"),
    ("PL-13", "Emotional Support Pals", "BRD-06"),
    ("PL-14", "Cozy Concepts", "BRD-06"),
    ("PL-15", "Hugimals Classic", "BRD-07"),
    ("PL-16", "Hugarounds", "BRD-07"),
    ("PL-17", "Hugimals Mini & Accessories", "BRD-07"),
]

SUB_PRODUCT_LINES = [
    ("SPL-01", "WDYM Core Games", "PL-01"),
    ("SPL-02", "WDYM Family Games", "PL-01"),
    ("SPL-03", "WDYM NSFW & Adult Expansions", "PL-02"),
    ("SPL-04", "WDYM Pop Culture Expansions", "PL-02"),
    ("SPL-05", "WDYM Licensed Brand Collabs", "PL-03"),
    ("SPL-06", "WDYM Creator Series", "PL-03"),
    ("SPL-07", "WDYM Social & Drinking", "PL-04"),
    ("SPL-08", "Buzzed Core", "PL-05"),
    ("SPL-09", "Buzzed Expansions", "PL-05"),
    ("SPL-10", "Buzzed Accessories", "PL-06"),
    ("SPL-11", "Relatable Adult Party", "PL-07"),
    ("SPL-12", "Relatable Relationship Games", "PL-07"),
    ("SPL-13", "Relatable Family Games", "PL-08"),
    ("SPL-14", "Relatable Kids Toys", "PL-08"),
    ("SPL-15", "Pool & Outdoor", "PL-09"),
    ("SPL-16", "Novelty Gifts", "PL-09"),
    ("SPL-17", "Wellness & Self-Care", "PL-10"),
    ("SPL-18", "Blind Box & Collectibles", "PL-10"),
    ("SPL-19", "Bee Street Core Games", "PL-11"),
    ("SPL-20", "Hunt A Killer Series", "PL-12"),
    ("SPL-21", "ESP Characters", "PL-13"),
    ("SPL-22", "ESP Accessories", "PL-13"),
    ("SPL-23", "Cozy Blankets", "PL-14"),
    ("SPL-24", "Hugimals Classic Characters", "PL-15"),
    ("SPL-25", "Hugaround Characters", "PL-16"),
    ("SPL-26", "Hug Babies & Bundles", "PL-17"),
    ("SPL-27", "Hugimals Accessories", "PL-17"),
]

MAJOR_CATEGORIES = [
    ("MCAT-01", "Games & Entertainment"),
    ("MCAT-02", "Lifestyle & Home"),
    ("MCAT-03", "Wellness & Comfort"),
]

CATEGORIES = [
    ("CAT-01", "Adult Party Games", "MCAT-01"),
    ("CAT-02", "Family & Kids Games", "MCAT-01"),
    ("CAT-03", "Mystery & Strategy Games", "MCAT-01"),
    ("CAT-04", "Outdoor & Novelty", "MCAT-02"),
    ("CAT-05", "Home Comfort", "MCAT-02"),
    ("CAT-06", "Licensed & Collectible", "MCAT-02"),
    ("CAT-07", "Emotional Wellness", "MCAT-03"),
    ("CAT-08", "Therapeutic Plush", "MCAT-03"),
    ("CAT-09", "Self-Care & Accessories", "MCAT-03"),
]

SUBCATEGORIES = [
    ("SCAT-01", "Meme & Card Games", "CAT-01"),
    ("SCAT-02", "Drinking & Social Games", "CAT-01"),
    ("SCAT-03", "Family Card Games", "CAT-02"),
    ("SCAT-04", "Kids Toys", "CAT-02"),
    ("SCAT-05", "Mystery Box Games", "CAT-03"),
    ("SCAT-06", "Subscription Games", "CAT-03"),
    ("SCAT-07", "Pool & Outdoor", "CAT-04"),
    ("SCAT-08", "Novelty Gifts", "CAT-04"),
    ("SCAT-09", "Blankets & Throws", "CAT-05"),
    ("SCAT-10", "Lifestyle Accessories", "CAT-05"),
    ("SCAT-11", "Brand Collabs", "CAT-06"),
    ("SCAT-12", "Creator Series", "CAT-06"),
    ("SCAT-13", "Support Characters", "CAT-07"),
    ("SCAT-14", "Plush Accessories", "CAT-07"),
    ("SCAT-15", "Weighted Plush", "CAT-08"),
    ("SCAT-16", "Warmable Plush", "CAT-08"),
    ("SCAT-17", "Self-Care Kits", "CAT-09"),
    ("SCAT-18", "Wellness Accessories", "CAT-09"),
]

CHANNEL_TYPES = [
    ("CHN-01", "Retail"),
    ("CHN-02", "E-commerce"),
    ("CHN-03", "DTC"),
    ("CHN-04", "TikTok Shop"),
    ("CHN-05", "Distributor"),
]

MARKETS = [
    ("MKT-01", "Northeast Retail", "CHN-01"),
    ("MKT-02", "Southeast Retail", "CHN-01"),
    ("MKT-03", "Midwest Retail", "CHN-01"),
    ("MKT-04", "West Retail", "CHN-01"),
    ("MKT-05", "Southwest Retail", "CHN-01"),
    ("MKT-06", "Amazon US", "CHN-02"),
    ("MKT-07", "Walmart.com", "CHN-02"),
    ("MKT-08", "Target.com", "CHN-02"),
    ("MKT-09", "Relatable.com Direct", "CHN-03"),
    ("MKT-10", "Subscribe & Save DTC", "CHN-03"),
    ("MKT-11", "TikTok Shop US", "CHN-04"),
    ("MKT-12", "UNFI Distribution", "CHN-05"),
    ("MKT-13", "KeHE Distribution", "CHN-05"),
]

CUSTOMER_GROUPS = [
    ("CG-01", "Mass Retail Northeast", "MKT-01"),
    ("CG-02", "Drug & Specialty Northeast", "MKT-01"),
    ("CG-03", "Mass Retail Southeast", "MKT-02"),
    ("CG-04", "Mass Retail Midwest", "MKT-03"),
    ("CG-05", "Mass Retail West", "MKT-04"),
    ("CG-06", "Specialty West", "MKT-04"),
    ("CG-07", "Mass Retail Southwest", "MKT-05"),
    ("CG-08", "Amazon Vendor Central", "MKT-06"),
    ("CG-09", "Amazon 3P Sellers", "MKT-06"),
    ("CG-10", "Walmart.com Digital", "MKT-07"),
    ("CG-11", "Target.com Digital", "MKT-08"),
    ("CG-12", "Relatable DTC Customers", "MKT-09"),
    ("CG-13", "Subscription Customers", "MKT-10"),
    ("CG-14", "TikTok Shop Buyers", "MKT-11"),
    ("CG-15", "UNFI Retail Partners", "MKT-12"),
    ("CG-16", "KeHE Retail Partners", "MKT-13"),
]

KEY_ACCOUNTS = [
    ("KA-01", "Walmart", "CG-01", "CHN-01"),
    ("KA-02", "Target", "CG-03", "CHN-01"),
    ("KA-03", "CVS", "CG-02", "CHN-01"),
    ("KA-04", "Walgreens", "CG-02", "CHN-01"),
    ("KA-05", "Kroger", "CG-04", "CHN-01"),
    ("KA-06", "Five Below", "CG-01", "CHN-01"),
    ("KA-07", "GameStop", "CG-05", "CHN-01"),
    ("KA-08", "Barnes & Noble", "CG-05", "CHN-01"),
    ("KA-09", "Urban Outfitters", "CG-06", "CHN-01"),
    ("KA-10", "TJ Maxx", "CG-04", "CHN-01"),
    ("KA-11", "Albertsons", "CG-07", "CHN-01"),
    ("KA-12", "HEB", "CG-07", "CHN-01"),
    ("KA-13", "Amazon 1P", "CG-08", "CHN-02"),
    ("KA-14", "Amazon 3P", "CG-09", "CHN-02"),
    ("KA-15", "Walmart.com", "CG-10", "CHN-02"),
    ("KA-16", "Target.com", "CG-11", "CHN-02"),
    ("KA-17", "Relatable.com", "CG-12", "CHN-03"),
    ("KA-18", "Subscribe & Save", "CG-13", "CHN-03"),
    ("KA-19", "TikTok Shop US", "CG-14", "CHN-04"),
    ("KA-20", "UNFI East", "CG-15", "CHN-05"),
    ("KA-21", "UNFI West", "CG-15", "CHN-05"),
    ("KA-22", "KeHE", "CG-16", "CHN-05"),
]

KA_CHANNEL = {ka[0]: ka[3] for ka in KEY_ACCOUNTS}


# ---------------------------------------------------------------------------
# SKU data
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

    # WDYM Core & Family
    sku("WDYM-CORE-001","What Do You Meme? Core Game","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2019-01-01")
    sku("WDYM-CORE-002","What Do You Meme? GIF Edition","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2019-06-01")
    sku("WDYM-CORE-003","What Do You Meme? Family Edition","DIV-01","BRD-01","PL-01","SPL-02","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2020-01-01")
    sku("WDYM-FMLY-001","New Phone Who Dis?","DIV-01","BRD-01","PL-01","SPL-02","MCAT-01","CAT-02","SCAT-03",21.99,8.50,"2019-06-01")
    sku("WDYM-FMLY-002","New Phone Who Dis? Family Edition","DIV-01","BRD-01","PL-01","SPL-02","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2020-06-01")
    sku("WDYM-FMLY-003","Guess The Gibberish Family Game","DIV-01","BRD-01","PL-01","SPL-02","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2021-03-01")
    sku("WDYM-CRSR-001","What Do You Meme? Career Series: Teachers","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2022-07-01")
    sku("WDYM-CRSR-002","What Do You Meme? Career Series: Nurses","DIV-01","BRD-01","PL-01","SPL-01","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2022-09-01")

    # WDYM Expansions
    sku("WDYM-XPAK-001","WDYM NSFW Expansion Pack","DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-01",9.99,3.50,"2019-01-01")
    sku("WDYM-XPAK-002","WDYM Fresh Memes #1 Expansion","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",11.99,4.25,"2020-03-01")
    sku("WDYM-XPAK-003","WDYM Fresh Memes #2 Expansion","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",11.99,4.25,"2021-03-01")
    sku("WDYM-XPAK-004","WDYM After Hours Expansion","DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-01",14.99,5.50,"2020-06-01")
    sku("WDYM-XPAK-005","WDYM Trisha Paytas Expansion","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",9.99,3.50,"2021-09-01")
    sku("WDYM-XPAK-006","New Phone Who Dis? Expansion","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",12.99,4.75,"2020-01-01")
    sku("WDYM-XPAK-007","WDYM Pop Culture Pack Vol 1","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",11.99,4.25,"2021-06-01")
    sku("WDYM-XPAK-008","WDYM Pop Culture Pack Vol 2","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",11.99,4.25,"2022-06-01")
    sku("WDYM-XPAK-009","WDYM Holiday Edition Expansion","DIV-01","BRD-01","PL-02","SPL-03","MCAT-01","CAT-01","SCAT-01",14.99,5.50,"2020-10-01")
    sku("WDYM-XPAK-010","WDYM Gen Z Edition Expansion","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",11.99,4.25,"2022-03-01")
    sku("WDYM-XPAK-011","WDYM Sports Fan Expansion","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",11.99,4.25,"2023-01-01")
    sku("WDYM-XPAK-012","WDYM Gaming Edition Expansion","DIV-01","BRD-01","PL-02","SPL-04","MCAT-01","CAT-01","SCAT-01",11.99,4.25,"2023-06-01")

    # Licensed
    sku("LIC-PTRT-001","What Do You Meme? x Pop-Tarts Edition","DIV-01","BRD-01","PL-03","SPL-05","MCAT-02","CAT-06","SCAT-11",24.99,10.50,"2022-09-01")
    sku("LIC-PTRT-002","Pop-Tarts x Relatable Party Pack","DIV-01","BRD-01","PL-03","SPL-05","MCAT-02","CAT-06","SCAT-11",19.99,8.00,"2023-03-01")
    sku("LIC-CRTR-001","Hunt A Killer: Sam & Colby Edition","DIV-01","BRD-05","PL-12","SPL-05","MCAT-02","CAT-06","SCAT-12",34.99,14.00,"2023-06-01")
    sku("LIC-CRTR-002","WDYM Creator Series Vol 1","DIV-01","BRD-01","PL-03","SPL-06","MCAT-02","CAT-06","SCAT-12",24.99,9.50,"2022-06-01")
    sku("LIC-CRTR-003","WDYM Creator Series Vol 2","DIV-01","BRD-01","PL-03","SPL-06","MCAT-02","CAT-06","SCAT-12",24.99,9.50,"2023-06-01")
    sku("LIC-CRTR-004","WDYM TikTok Edition","DIV-01","BRD-01","PL-03","SPL-06","MCAT-02","CAT-06","SCAT-12",21.99,8.50,"2023-01-01")

    # Relatable Party Games
    sku("REL-PRTY-001","Incohearent","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",21.99,8.50,"2019-06-01")
    sku("REL-PRTY-002","Incohearent Family Edition","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2020-06-01")
    sku("REL-PRTY-003","Incohearent Fresh Phrases Expansion","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",12.99,4.75,"2021-01-01")
    sku("REL-PRTY-004","For the Girls","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",21.99,8.50,"2021-03-01")
    sku("REL-PRTY-005","For the Girls Expansion","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",14.99,5.50,"2022-01-01")
    sku("REL-PRTY-006","InQueeries","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",19.99,7.50,"2022-06-01")
    sku("REL-PRTY-007","Stir The Pot","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",19.99,7.50,"2022-09-01")
    sku("REL-PRTY-008","Live Laugh Lose","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",19.99,7.50,"2022-09-01")
    sku("REL-PRTY-009","Over-Rated","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",19.99,7.50,"2023-03-01")
    sku("REL-PRTY-010","Asking For A Friend","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",21.99,8.50,"2023-06-01")
    sku("REL-PRTY-011","Who Killed Mia?","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",29.99,11.00,"2021-06-01")
    sku("REL-PRTY-012","Kollide","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2023-09-01")
    sku("REL-TSCK-001","Tower Stack","DIV-01","BRD-03","PL-08","SPL-13","MCAT-01","CAT-02","SCAT-04",19.99,7.50,"2020-06-01")
    sku("REL-PRTY-013","Naughty or Nice","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",19.99,7.50,"2021-09-01")
    sku("REL-PRTY-014","Hot Takes","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",22.99,8.75,"2022-03-01")
    sku("REL-PRTY-015","Roast Battle Card Game","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2022-06-01")
    sku("REL-PRTY-016","This or That: Adult Edition","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",17.99,6.75,"2022-09-01")
    sku("REL-PRTY-017","Conspiracy: The Game","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2023-01-01")
    sku("REL-PRTY-018","Would You Rather? Party Edition","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",17.99,6.50,"2023-03-01")
    sku("REL-PRTY-019","Sip Sip Hooray","DIV-01","BRD-03","PL-07","SPL-07","MCAT-01","CAT-01","SCAT-02",19.99,7.50,"2023-06-01")
    sku("REL-PRTY-020","Double Date Card Game","DIV-01","BRD-03","PL-07","SPL-12","MCAT-01","CAT-01","SCAT-01",21.99,8.50,"2023-09-01")
    sku("REL-PRTY-021","Trauma Dump","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",22.99,8.75,"2024-01-01")
    sku("REL-PRTY-022","Group Chat: The Game","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",19.99,7.50,"2024-03-01")
    sku("REL-PRTY-023","Boundary Issues","DIV-01","BRD-03","PL-07","SPL-12","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2024-06-01")

    # Buzzed
    sku("BUZZ-CORE-001","Buzzed Core Game","DIV-01","BRD-02","PL-05","SPL-08","MCAT-01","CAT-01","SCAT-02",19.99,7.50,"2019-01-01")
    sku("BUZZ-XPAK-001","Buzzed Expansion Pack #1","DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-01","SCAT-02",14.99,5.50,"2020-01-01")
    sku("BUZZ-XPAK-002","Buzzed Expansion Pack #2","DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-01","SCAT-02",14.99,5.50,"2021-01-01")
    sku("BUZZ-XPAK-003","Buzzed Holiday Edition","DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-01","SCAT-02",19.99,7.50,"2020-10-01")
    sku("BUZZ-DXED-001","Buzzed Deluxe Edition","DIV-01","BRD-02","PL-05","SPL-08","MCAT-01","CAT-01","SCAT-02",29.99,11.00,"2022-06-01")
    sku("BUZZ-SHOT-001","Lil Cheers Shot Glass Set","DIV-01","BRD-02","PL-06","SPL-10","MCAT-02","CAT-04","SCAT-08",14.99,4.50,"2021-06-01")
    sku("BUZZ-SHOT-002","Lil Cheers Mini Bottle Set","DIV-01","BRD-02","PL-06","SPL-10","MCAT-02","CAT-04","SCAT-08",12.99,3.75,"2022-01-01")
    sku("BUZZ-SHOT-003","Lil Cheers Party Pack","DIV-01","BRD-02","PL-06","SPL-10","MCAT-02","CAT-04","SCAT-08",19.99,6.50,"2022-09-01")
    sku("BUZZ-GAME-001","Buzz'd Out: Bar Edition","DIV-01","BRD-02","PL-05","SPL-08","MCAT-01","CAT-01","SCAT-02",24.99,9.50,"2023-01-01")
    sku("BUZZ-GAME-002","Shots & Dares","DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-01","SCAT-02",17.99,6.75,"2023-06-01")
    sku("BUZZ-GAME-003","Tipsy Trivia","DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-01","SCAT-02",19.99,7.50,"2024-01-01")
    sku("BUZZ-GAME-004","Last Drink Standing","DIV-01","BRD-02","PL-05","SPL-09","MCAT-01","CAT-01","SCAT-02",22.99,8.75,"2024-06-01")

    # Relationship / Family
    sku("REL-RLSH-001","Let's Get Deep","DIV-01","BRD-03","PL-07","SPL-12","MCAT-01","CAT-01","SCAT-01",21.99,8.50,"2019-06-01")
    sku("REL-RLSH-002","Let's Get Deep Expansion","DIV-01","BRD-03","PL-07","SPL-12","MCAT-01","CAT-01","SCAT-01",14.99,5.50,"2020-06-01")
    sku("REL-FMLY-001","Cows in Space","DIV-01","BRD-03","PL-08","SPL-13","MCAT-01","CAT-02","SCAT-04",24.99,9.50,"2024-01-01")
    sku("REL-FMLY-002","Silly Poopy's Hide & Seek","DIV-01","BRD-03","PL-08","SPL-14","MCAT-01","CAT-02","SCAT-04",12.99,5.00,"2023-06-01")
    sku("REL-FMLY-003","Grounded for Life","DIV-01","BRD-03","PL-08","SPL-13","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2023-01-01")
    sku("REL-FMLY-004","All of Us","DIV-01","BRD-03","PL-08","SPL-13","MCAT-01","CAT-02","SCAT-03",17.99,6.50,"2024-06-01")

    # Outdoor
    sku("REL-OUTD-001","Iconic Float Giant Ramen Pool Float","DIV-01","BRD-03","PL-09","SPL-15","MCAT-02","CAT-04","SCAT-07",29.99,11.00,"2020-03-01")
    sku("REL-OUTD-002","Iconic Float Giant Pizza Pool Float","DIV-01","BRD-03","PL-09","SPL-15","MCAT-02","CAT-04","SCAT-07",29.99,11.00,"2020-03-01")
    sku("REL-OUTD-003","Iconic Float Giant Taco Pool Float","DIV-01","BRD-03","PL-09","SPL-15","MCAT-02","CAT-04","SCAT-07",34.99,13.00,"2021-03-01")
    sku("REL-OUTD-004","Iconic Float Giant Avocado","DIV-01","BRD-03","PL-09","SPL-15","MCAT-02","CAT-04","SCAT-07",29.99,11.00,"2022-03-01")

    # Wellness
    sku("REL-WLNS-001","Happy Helpers Menstruation Crustacean Heating Pad","DIV-02","BRD-06","PL-10","SPL-17","MCAT-03","CAT-09","SCAT-17",24.99,9.00,"2022-01-01")
    sku("REL-WLNS-002","Happy Helpers Anxiety Relief Kit","DIV-02","BRD-06","PL-10","SPL-17","MCAT-03","CAT-09","SCAT-17",19.99,7.50,"2022-06-01")
    sku("REL-WLNS-003","Chill Pill Stress Relief Kit","DIV-02","BRD-06","PL-10","SPL-17","MCAT-03","CAT-09","SCAT-17",22.99,8.50,"2023-06-01")

    # Collectibles
    sku("REL-WBSB-001","WabiSabi Kitty Club Blind Box","DIV-02","BRD-06","PL-10","SPL-18","MCAT-02","CAT-06","SCAT-11",14.99,5.00,"2023-01-01")
    sku("REL-WBSB-002","WabiSabi Kitty Club Series 2","DIV-02","BRD-06","PL-10","SPL-18","MCAT-02","CAT-06","SCAT-11",16.99,5.75,"2024-06-01")
    sku("REL-PETS-001","Relatable Pets Pawty Time Game","DIV-01","BRD-03","PL-08","SPL-13","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2023-09-01")

    # More originals
    sku("REL-PRTY-024","Burn Book: The Game","DIV-01","BRD-03","PL-07","SPL-11","MCAT-01","CAT-01","SCAT-01",22.99,8.75,"2024-09-01")
    sku("REL-FMLY-005","Dino Dig: Kids Edition","DIV-01","BRD-03","PL-08","SPL-14","MCAT-01","CAT-02","SCAT-04",17.99,6.75,"2024-03-01")
    sku("REL-RLSH-003","Couple Vibes","DIV-01","BRD-03","PL-07","SPL-12","MCAT-01","CAT-01","SCAT-01",21.99,8.50,"2024-01-01")
    sku("REL-FMLY-006","Family Drama: The Game","DIV-01","BRD-03","PL-08","SPL-13","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2024-09-01")

    # Bee Street Games
    sku("BSG-CORE-001","Bee Street Games Flagship","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-01","SCAT-01",24.99,9.50,"2021-06-01")
    sku("BSG-CORE-002","Bee Street Buzz Edition","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-01","SCAT-01",22.99,8.75,"2022-01-01")
    sku("BSG-CORE-003","Bee Street Family Hive","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2022-06-01")
    sku("BSG-CORE-004","Bee Street Party Pack","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-01","SCAT-01",27.99,10.50,"2022-09-01")
    sku("BSG-CARD-001","Bee Street Card Duel","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-01","SCAT-01",17.99,6.75,"2023-01-01")
    sku("BSG-CARD-002","Bee Street Expansion Vol 1","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-01","SCAT-01",12.99,4.75,"2023-06-01")
    sku("BSG-CARD-003","Bee Street Strategy Edition","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-01","SCAT-01",29.99,11.00,"2023-09-01")
    sku("BSG-CARD-004","Bee Street Kids Quest","DIV-01","BRD-04","PL-11","SPL-19","MCAT-01","CAT-02","SCAT-03",19.99,7.50,"2024-03-01")

    # Hunt A Killer
    sku("HAK-CORE-001","Hunt A Killer Season 1","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-05",29.99,12.00,"2019-01-01")
    sku("HAK-CORE-002","Hunt A Killer Season 2","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-05",29.99,12.00,"2020-01-01")
    sku("HAK-CORE-003","Hunt A Killer Season 3","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-05",29.99,12.00,"2021-01-01")
    sku("HAK-SUBS-001","Hunt A Killer Subscription Box","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-06",29.99,11.00,"2019-06-01")
    sku("HAK-MINI-001","Hunt A Killer Mini Mystery","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-05",14.99,5.50,"2022-01-01")
    sku("HAK-MINI-002","Hunt A Killer Holiday Special","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-05",19.99,7.50,"2022-10-01")
    sku("HAK-MINI-003","Hunt A Killer: Beach House","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-05",24.99,9.50,"2023-06-01")
    sku("HAK-MINI-004","Hunt A Killer: Cold Case Files","DIV-01","BRD-05","PL-12","SPL-20","MCAT-01","CAT-03","SCAT-05",29.99,11.00,"2024-01-01")

    # ESP — original trio
    sku("REL-ESP-001","Emotional Support Pals — French Fries","DIV-02","BRD-06","PL-13","SPL-21","MCAT-03","CAT-07","SCAT-13",24.99,8.50,"2020-01-01")
    sku("REL-ESP-002","Emotional Support Pals — Flowers","DIV-02","BRD-06","PL-13","SPL-21","MCAT-03","CAT-07","SCAT-13",24.99,8.50,"2020-01-01")
    sku("REL-ESP-003","Emotional Support Pals — Mushroom","DIV-02","BRD-06","PL-13","SPL-21","MCAT-03","CAT-07","SCAT-13",24.99,8.50,"2020-01-01")

    # ESP expansion — 27 more
    esp_chars = [
        ("004","Axolotl",24.99,8.50,"2021-01-01"),("005","Ghost",24.99,8.50,"2021-03-01"),
        ("006","Frog",24.99,8.50,"2021-06-01"),("007","Cactus",24.99,8.50,"2021-06-01"),
        ("008","Cloud",22.99,7.75,"2021-09-01"),("009","Avocado",24.99,8.50,"2021-09-01"),
        ("010","Rainbow",27.99,9.50,"2021-12-01"),("011","Pizza Slice",24.99,8.50,"2022-01-01"),
        ("012","Taco",24.99,8.50,"2022-03-01"),("013","Sushi",27.99,9.50,"2022-03-01"),
        ("014","Dinosaur",29.99,10.00,"2022-06-01"),("015","Crab",24.99,8.50,"2022-06-01"),
        ("016","Jellyfish",27.99,9.50,"2022-09-01"),("017","Succulent",22.99,7.75,"2022-09-01"),
        ("018","Croissant",24.99,8.50,"2022-12-01"),("019","Boba Tea",27.99,9.50,"2023-01-01"),
        ("020","Hot Dog",22.99,7.75,"2023-03-01"),("021","Strawberry",24.99,8.50,"2023-03-01"),
        ("022","Donut",24.99,8.50,"2023-06-01"),("023","Narwhal",29.99,10.00,"2023-06-01"),
        ("024","Sloth",27.99,9.50,"2023-09-01"),("025","Cactus Deluxe",34.99,12.00,"2023-09-01"),
        ("026","Penguin",24.99,8.50,"2023-12-01"),("027","Bear",27.99,9.50,"2024-01-01"),
        ("028","Shark",29.99,10.00,"2024-03-01"),("029","Flamingo",27.99,9.50,"2024-06-01"),
        ("030","Bunny",24.99,8.50,"2024-09-01"),
    ]
    for num, name, price, cost, launch in esp_chars:
        sku(f"REL-ESP-{num}", f"Emotional Support Pals — {name}",
            "DIV-02","BRD-06","PL-13","SPL-21","MCAT-03","CAT-07","SCAT-13",
            price, cost, launch)

    # Cozy Concepts
    sku("REL-COZY-001","Cozy Concepts Blanket Classic","DIV-02","BRD-06","PL-14","SPL-23","MCAT-02","CAT-05","SCAT-09",39.99,14.00,"2021-09-01")
    sku("REL-COZY-002","Cozy Concepts Meme Edition","DIV-02","BRD-06","PL-14","SPL-23","MCAT-02","CAT-05","SCAT-09",44.99,15.50,"2022-06-01")
    sku("REL-COZY-003","Cozy Concepts Holiday Blanket","DIV-02","BRD-06","PL-14","SPL-23","MCAT-02","CAT-05","SCAT-09",44.99,15.50,"2022-10-01")
    sku("REL-COZY-004","Cozy Concepts Weighted Blanket","DIV-02","BRD-06","PL-14","SPL-23","MCAT-02","CAT-05","SCAT-09",59.99,21.00,"2023-06-01")
    sku("REL-COZY-005","Cozy Concepts Mini Throw","DIV-02","BRD-06","PL-14","SPL-23","MCAT-02","CAT-05","SCAT-09",29.99,10.50,"2024-01-01")

    # Hugimals World (all is_new_sku=True)
    sku("HUG-CLAS-001","Sam the Sloth","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-002","Harper the Pig","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-003","Forrest the Fox","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-004","Bowie the Panda","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-005","Berkeley the Bear","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-006","Luna the Bunny","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-007","Charlie the Cat","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-008","Mochi the Panda Cub","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-009","Finn the Seal","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-CLAS-010","Daisy the Cow","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",68.00,22.00,"2024-07-01",is_new=True)
    sku("HUG-RND-001","Pax the Penguin Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-RND-002","Ollie the Orangutan Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-RND-003","Sawyer the Sloth Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-RND-004","Indigo the Octopus Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-RND-005","Ruby the Raccoon Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-RND-006","Theo the Tiger Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-RND-007","Ivy the Iguana Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-RND-008","Cleo the Chameleon Hugaround","DIV-03","BRD-07","PL-16","SPL-25","MCAT-03","CAT-08","SCAT-16",48.00,16.00,"2024-07-01",is_new=True)
    sku("HUG-BERK-001","Berkeley the Bat","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",45.00,15.00,"2024-07-01",is_new=True)
    sku("HUG-BERK-002","Berkeley the Bat Glow Edition","DIV-03","BRD-07","PL-15","SPL-24","MCAT-03","CAT-08","SCAT-15",49.00,16.50,"2024-10-01",is_new=True)
    sku("HUG-BABY-001","Hug Baby Bowie the Panda","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",12.00,4.00,"2024-10-01",is_new=True)
    sku("HUG-BABY-002","Hug Baby Sam the Sloth","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",12.00,4.00,"2024-10-01",is_new=True)
    sku("HUG-BABY-003","Hug Baby Forrest the Fox","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",12.00,4.00,"2024-10-01",is_new=True)
    sku("HUG-BABY-004","Hug Baby Luna the Bunny","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",12.00,4.00,"2024-10-01",is_new=True)
    sku("HUG-BNDL-001","Sloth With Heart Bundle","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",104.00,34.00,"2024-10-01",is_new=True)
    sku("HUG-BNDL-002","Red and Rose Hearts Bundle","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",126.00,41.00,"2024-10-01",is_new=True)
    sku("HUG-BNDL-003","Black and White Hearts Bundle","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",126.00,41.00,"2024-10-01",is_new=True)
    sku("HUG-BNDL-004","Hugaround + Classic Bundle","DIV-03","BRD-07","PL-17","SPL-26","MCAT-03","CAT-08","SCAT-15",110.00,36.00,"2024-11-01",is_new=True)
    sku("HUG-ACCS-001","Weighted Hug Sweatshirt","DIV-03","BRD-07","PL-17","SPL-27","MCAT-03","CAT-08","SCAT-15",128.00,42.00,"2024-11-01",is_new=True)
    sku("HUG-ACCS-002","Hugimals Travel Bag","DIV-03","BRD-07","PL-17","SPL-27","MCAT-03","CAT-08","SCAT-15",24.99,8.50,"2024-11-01",is_new=True)

    return rows


# ---------------------------------------------------------------------------
# dim_version
# ---------------------------------------------------------------------------

def gen_versions():
    rows = [
        {"version_id":"BUDGET","version_name":"Annual Budget","version_type":"Financial","version_order":1,"lag_months":""},
        {"version_id":"OP_PLAN","version_name":"Operating Plan","version_type":"Financial","version_order":2,"lag_months":""},
        {"version_id":"LE1","version_name":"Latest Estimate 1","version_type":"Financial","version_order":3,"lag_months":""},
        {"version_id":"LE2","version_name":"Latest Estimate 2","version_type":"Financial","version_order":4,"lag_months":""},
        {"version_id":"LE3","version_name":"Latest Estimate 3","version_type":"Financial","version_order":5,"lag_months":""},
        {"version_id":"LATEST_EST","version_name":"Latest Estimate","version_type":"Financial","version_order":6,"lag_months":""},
    ]
    for i in range(1, 11):
        rows.append({
            "version_id": f"LAG{i}",
            "version_name": f"Lag {i} Forecast",
            "version_type": "ForecastAccuracy",
            "version_order": 6 + i,
            "lag_months": i,
        })
    return rows


# ---------------------------------------------------------------------------
# dim_promotion
# ---------------------------------------------------------------------------

PROMO_TEMPLATES = [
    ("Holiday Party Games Feature — Walmart", "Feature",      "KA-01", 11, 12, 0.35, 0.50),
    ("Back to School WDYM Display — Target",  "Display",      "KA-02",  8,  9, 0.20, 0.35),
    ("Valentine's Day Let's Get Deep — Amazon","TPR",         "KA-13",  1,  2, 0.15, 0.30),
    ("Prime Day Games Deal — Amazon 1P",       "TPR",         "KA-13",  7,  7, 0.25, 0.40),
    ("Super Bowl Buzzed Promo — Retail",       "Feature",     "KA-01",  1,  2, 0.20, 0.35),
    ("Summer Pool Float Launch — Target & Walmart","Launch",  "KA-02",  5,  6, 0.15, 0.30),
    ("TikTok Viral Boost — Tower Stack",       "TikTok_Boost","KA-19", None,None,0.40,0.60),
    ("ESP Holiday Gift Push — Multi-Channel",  "Holiday",     "KA-01", 11, 12, 0.30, 0.45),
    ("Pop-Tarts Collab Launch",                "Launch",      "KA-02",  9, 10, 0.20, 0.40),
]

PROMO_SKUS = {
    "Holiday Party Games Feature — Walmart":     ["WDYM-CORE-001","WDYM-CORE-002","REL-PRTY-001","BUZZ-CORE-001"],
    "Back to School WDYM Display — Target":      ["WDYM-CORE-001","WDYM-FMLY-001","REL-PRTY-004"],
    "Valentine's Day Let's Get Deep — Amazon":   ["REL-RLSH-001","REL-PRTY-004","REL-ESP-002"],
    "Prime Day Games Deal — Amazon 1P":          ["WDYM-CORE-001","BUZZ-CORE-001","REL-PRTY-001","HAK-CORE-001"],
    "Super Bowl Buzzed Promo — Retail":          ["BUZZ-CORE-001","BUZZ-XPAK-001","BUZZ-SHOT-001"],
    "Summer Pool Float Launch — Target & Walmart":["REL-OUTD-001","REL-OUTD-002","REL-OUTD-003"],
    "TikTok Viral Boost — Tower Stack":          ["REL-TSCK-001"],
    "ESP Holiday Gift Push — Multi-Channel":     ["REL-ESP-001","REL-ESP-002","REL-ESP-003","REL-ESP-011"],
    "Pop-Tarts Collab Launch":                   ["LIC-PTRT-001","LIC-PTRT-002"],
}


def gen_promotions():
    rows = []
    pid = 1
    for year in range(2020, 2027):
        for tmpl in PROMO_TEMPLATES:
            name_base, ptype, ka, m1, m2, lift_lo, lift_hi = tmpl
            name = f"{name_base} {year}"
            if m1 is None:
                m1 = random.randint(3, 9)
                m2 = m1 + random.randint(0, 1)
            end_m = min(m2, 12)
            start = date(year, m1, 1)
            end = date(year, end_m, 28 if end_m == 2 else 30)
            skus = PROMO_SKUS.get(name_base, ["WDYM-CORE-001"])
            for sku_id in skus:
                rows.append({
                    "promotion_id": f"PROMO-{pid:04d}",
                    "promotion_name": name,
                    "promotion_type": ptype,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "sku_id": sku_id,
                    "key_account_id": ka,
                    "expected_lift_pct": round(random.uniform(lift_lo, lift_hi), 3),
                })
                pid += 1
    return rows


# ---------------------------------------------------------------------------
# SKU-account assignment
# ---------------------------------------------------------------------------

def build_sku_account_pairs(sku_rows):
    retail_kas = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-01"]
    ecom_kas   = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-02"]
    dtc_kas    = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-03"]
    tiktok_kas = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-04"]
    dist_kas   = [ka[0] for ka in KEY_ACCOUNTS if ka[3] == "CHN-05"]

    pairs = []
    for s in sku_rows:
        sid = s["sku_id"]
        div = s["division_id"]
        assigned = set()

        if div == "DIV-03":
            assigned.update(["KA-13", "KA-17"])
            assigned.update(tiktok_kas)
            assigned.update(["KA-02", "KA-01"])
        elif div == "DIV-02":
            assigned.update(random.sample(retail_kas, k=min(6, len(retail_kas))))
            assigned.update(ecom_kas)
            assigned.update(dtc_kas)
            assigned.update(tiktok_kas)
        else:
            assigned.add("KA-01")
            other_retail = [k for k in retail_kas if k != "KA-01"]
            assigned.update(random.sample(other_retail, k=random.randint(3, 6)))
            assigned.update(random.sample(ecom_kas, k=random.randint(2, len(ecom_kas))))
            assigned.update(dtc_kas[:1])

        for ka_id in assigned:
            pairs.append((sid, ka_id))

    return pairs


# ---------------------------------------------------------------------------
# Volume & seasonality
# ---------------------------------------------------------------------------

SEASONALITY = {
    "CAT-01": np.array([0.60,0.55,0.65,0.70,0.75,0.80,0.90,1.00,1.10,1.20,2.50,2.80]),
    "CAT-02": np.array([0.50,0.45,0.55,0.60,0.70,0.80,0.85,0.90,1.00,1.10,2.80,3.50]),
    "CAT-03": np.array([0.80,0.75,0.80,0.85,0.90,0.95,0.95,1.00,1.00,1.05,1.80,2.20]),
    "CAT-04": np.array([0.20,0.20,0.40,0.80,1.60,2.20,2.50,2.20,1.20,0.40,0.30,0.20]),
    "CAT-05": np.array([1.00,0.90,0.85,0.80,0.85,0.90,0.95,0.95,1.00,1.10,1.80,2.00]),
    "CAT-06": np.array([0.70,0.80,0.85,0.90,0.90,0.95,1.10,1.00,1.10,1.00,1.50,1.80]),
    "CAT-07": np.array([1.30,1.10,0.90,0.85,0.85,0.90,0.95,1.00,1.05,1.10,2.20,2.80]),
    "CAT-08": np.array([1.20,1.00,0.85,0.80,0.80,0.85,0.90,0.95,1.00,1.10,2.50,3.00]),
    "CAT-09": np.array([1.20,1.10,0.90,0.85,0.85,0.90,0.95,1.00,1.05,1.10,1.80,2.20]),
}

ACCOUNT_BASE = {
    "KA-01": 5000, "KA-02": 3500, "KA-03": 400,  "KA-04": 350,
    "KA-05": 600,  "KA-06": 500,  "KA-07": 300,  "KA-08": 250,
    "KA-09": 200,  "KA-10": 400,  "KA-11": 300,  "KA-12": 350,
    "KA-13": 2500, "KA-14": 800,  "KA-15": 1200, "KA-16": 900,
    "KA-17": 600,  "KA-18": 200,  "KA-19": 400,
    "KA-20": 300,  "KA-21": 250,  "KA-22": 200,
}

YOY_GROWTH = {"DIV-01": 0.09, "DIV-02": 0.22, "DIV-03": 0.0}

VIRAL_SPIKES = [
    ("REL-TSCK-001", 2021, 3,  6.0, ["KA-19"]),
    ("REL-TSCK-001", 2021, 4,  4.0, ["KA-19","KA-13"]),
    ("REL-TSCK-001", 2021, 5,  2.5, ["KA-19","KA-13","KA-01"]),
    ("REL-TSCK-001", 2023, 8,  7.0, ["KA-19"]),
    ("REL-TSCK-001", 2023, 9,  5.0, ["KA-19","KA-13"]),
    ("REL-TSCK-001", 2023, 10, 3.0, ["KA-19","KA-13","KA-02"]),
    ("REL-ESP-003",  2022, 5,  4.5, ["KA-19"]),
    ("REL-ESP-003",  2022, 6,  3.0, ["KA-19","KA-13"]),
    ("WDYM-CORE-001",2024, 2,  3.5, ["KA-19","KA-13"]),
    ("REL-PRTY-004", 2024, 9,  4.0, ["KA-19"]),
    ("REL-PRTY-004", 2024, 10, 3.0, ["KA-19","KA-13"]),
    ("LIC-CRTR-004", 2023, 4,  5.0, ["KA-19"]),
]


def get_spike_mult(sku_id, year, month, ka_id):
    for sid, yr, mo, mult, channels in VIRAL_SPIKES:
        if sid == sku_id and yr == year and mo == month and ka_id in channels:
            return mult
    return 1.0


def sku_volume_scale(sku_id):
    if sku_id in ("WDYM-CORE-001","WDYM-CORE-002","BUZZ-CORE-001","REL-PRTY-001",
                   "REL-ESP-001","REL-ESP-002","REL-ESP-003"):
        return 1.0
    if sku_id in ("REL-TSCK-001","REL-PRTY-004","REL-RLSH-001","WDYM-FMLY-001"):
        return 0.80
    if "XPAK" in sku_id:
        return 0.30
    if sku_id.startswith("HUG-CLAS"):
        return 0.35
    if sku_id.startswith("HUG-RND"):
        return 0.25
    if sku_id.startswith("HUG-BABY"):
        return 0.15
    if sku_id.startswith("HUG-BNDL"):
        return 0.10
    if sku_id.startswith(("HUG-ACCS","HUG-BERK")):
        return 0.08
    if "COZY" in sku_id:
        return 0.40
    if "ESP" in sku_id:
        return 0.55
    return 0.45


def base_units(sku_id, ka_id, cat_id, div_id, year, month, sku_info):
    launch = date.fromisoformat(sku_info["launch_date"])
    months_since = (year - launch.year) * 12 + (month - launch.month)
    if months_since < 0:
        return 0.0

    if div_id == "DIV-01":
        if months_since == 0:      ramp = 1.8
        elif months_since <= 2:    ramp = 1.4
        elif months_since <= 5:    ramp = 1.0
        elif months_since <= 11:   ramp = 0.75
        elif sku_volume_scale(sku_id) >= 0.80:
            ramp = 0.70
        else:
            ramp = max(0.35, 0.70 - (months_since - 11) * 0.008)
    elif div_id == "DIV-02":
        if months_since == 0:      ramp = 1.5
        elif months_since <= 3:    ramp = 1.2
        else:                      ramp = 1.0
    else:  # DIV-03 Hugimals
        if months_since < 3:       ramp = 0.6
        elif months_since < 6:     ramp = 0.85
        elif months_since < 12:    ramp = 1.0
        else:                      ramp = 1.2

    # Hugimals channel restrictions
    if div_id == "DIV-03":
        chn = KA_CHANNEL.get(ka_id, "")
        if chn == "CHN-01" and (year < 2025):
            return 0.0
        if chn == "CHN-04" and (year == 2024 and month < 10):
            return 0.0

    base = ACCOUNT_BASE.get(ka_id, 200) * sku_volume_scale(sku_id)
    season = SEASONALITY.get(cat_id, np.ones(12))
    seas_mult = season[month - 1]
    growth_mult = (1 + YOY_GROWTH.get(div_id, 0.09)) ** max(0, year - 2020)
    spike = get_spike_mult(sku_id, year, month, ka_id)

    units = base * ramp * seas_mult * growth_mult * spike
    units *= random.uniform(0.88, 1.12)
    return max(0.0, units)


# ---------------------------------------------------------------------------
# fact_financial_plan
# ---------------------------------------------------------------------------

VERSION_NOISE = {
    "BUDGET": 0.15, "OP_PLAN": 0.10, "LE1": 0.07,
    "LE2": 0.04, "LE3": 0.02, "LATEST_EST": 0.01,
}

LAG_NOISE = {i: max(0.03, 0.22 - i * 0.02) for i in range(1, 11)}


def gen_fact_financial_plan(sku_rows, pairs):
    sku_map = {s["sku_id"]: s for s in sku_rows}
    now_ts = "2026-06-16 00:00:00 UTC"

    for year in range(2020, 2027):
        rows = []
        print(f"  Generating financial plan {year}...")
        for sku_id, ka_id in pairs:
            s = sku_map[sku_id]
            launch = date.fromisoformat(s["launch_date"])
            if launch.year > year:
                continue

            cat_id = s["category_id"]
            div_id = s["division_id"]
            price = s["unit_price"]

            actuals = {m: base_units(sku_id, ka_id, cat_id, div_id, year, m, s) for m in range(1, 13)}

            for version_id, v_noise in VERSION_NOISE.items():
                for month in range(1, 13):
                    actual = actuals[month]
                    if actual == 0:
                        continue

                    is_new_launch = (launch.year == year)
                    bias = 1.20 if (version_id == "BUDGET" and is_new_launch) else (1.05 if version_id == "BUDGET" else 1.0)

                    stat_noise = random.gauss(0, v_noise)
                    stat_fcst = max(0.0, actual * bias * (1 + stat_noise))

                    manual_override = 0.0
                    if random.random() < 0.05 and stat_fcst > 0:
                        manual_override = round(stat_fcst * random.uniform(-0.15, 0.15), 1)

                    total_fcst = max(0.0, stat_fcst + manual_override)
                    sell_in = round(actual, 1)
                    sell_thru = round(actual * random.uniform(0.88, 1.05), 1)
                    inv_on_hand = round(sell_in * random.uniform(0.8, 2.0), 1)
                    wos = round(inv_on_hand / max(sell_in / 4, 1), 2)

                    rows.append({
                        "record_id": str(uuid.uuid4()),
                        "sku_id": sku_id,
                        "key_account_id": ka_id,
                        "fiscal_year": year,
                        "fiscal_month": month,
                        "version_id": version_id,
                        "sell_in_units": sell_in,
                        "sell_in_dollars": round(sell_in * price, 2),
                        "sell_through_units": sell_thru,
                        "sell_through_dollars": round(sell_thru * price, 2),
                        "corrected_history_units": round(actual * random.uniform(0.95, 1.02), 1),
                        "stat_forecast_units": round(stat_fcst, 1),
                        "manual_override_units": round(manual_override, 1),
                        "promo_uplift_units": 0.0,
                        "total_forecast_units": round(total_fcst, 1),
                        "total_forecast_dollars": round(total_fcst * price, 2),
                        "inventory_on_hand_units": inv_on_hand,
                        "weeks_of_supply": wos,
                        "loaded_at": now_ts,
                    })

        path = FACT_DIR / f"fact_financial_plan_{year}.csv"
        write_csv(path, rows)
        upload(path)
        yield path


# ---------------------------------------------------------------------------
# fact_pos_weekly
# ---------------------------------------------------------------------------

def gen_fact_pos_weekly(sku_rows, pairs):
    sku_map = {s["sku_id"]: s for s in sku_rows}
    now_ts = "2026-06-16 00:00:00 UTC"
    rows = []
    print("Generating fact_pos_weekly...")

    d = date(2020, 1, 6)
    weekly_dates = []
    while d <= date(2025, 12, 31):
        weekly_dates.append(d)
        d += timedelta(weeks=1)

    for sku_id, ka_id in pairs:
        s = sku_map[sku_id]
        launch = date.fromisoformat(s["launch_date"])
        cat_id = s["category_id"]
        div_id = s["division_id"]
        price = s["unit_price"]

        for wk_start in weekly_dates:
            if wk_start < launch:
                continue
            fy, fq, fm, fw = date_to_fiscal(wk_start)
            wk_end = wk_start + timedelta(days=6)
            is_partial = wk_start.month != wk_end.month

            month_units = base_units(sku_id, ka_id, cat_id, div_id, wk_start.year, wk_start.month, s)
            pos = round(month_units / 4.3 * random.uniform(0.85, 1.15), 1)
            inv = round(pos * random.uniform(2.5, 6.0), 1)
            wos = round(inv / max(pos, 0.1), 2)

            rows.append({
                "record_id": str(uuid.uuid4()),
                "sku_id": sku_id,
                "key_account_id": ka_id,
                "date_id": wk_start.isoformat(),
                "fiscal_year": fy,
                "fiscal_week": fw,
                "is_partial_week": is_partial,
                "pos_units": pos,
                "pos_dollars": round(pos * price, 2),
                "inventory_on_hand_units": inv,
                "weeks_of_supply": wos,
                "loaded_at": now_ts,
            })

    path = FACT_DIR / "fact_pos_weekly.csv"
    write_csv(path, rows)
    upload(path)
    return path


# ---------------------------------------------------------------------------
# fact_forecast_snapshot
# ---------------------------------------------------------------------------

def gen_fact_forecast_snapshot(sku_rows, pairs):
    sku_map = {s["sku_id"]: s for s in sku_rows}
    now_ts = "2026-06-16 00:00:00 UTC"
    rows = []
    print("Generating fact_forecast_snapshot...")

    for sku_id, ka_id in pairs:
        s = sku_map[sku_id]
        launch = date.fromisoformat(s["launch_date"])
        cat_id = s["category_id"]
        div_id = s["division_id"]

        for year in range(2020, 2026):
            for month in range(1, 13):
                if date(year, month, 1) < launch:
                    continue
                actual = base_units(sku_id, ka_id, cat_id, div_id, year, month, s)
                if actual == 0:
                    continue

                for lag in range(1, 11):
                    snap_month = month - lag
                    snap_year = year
                    while snap_month < 1:
                        snap_month += 12
                        snap_year -= 1
                    if snap_year < 2019:
                        continue

                    noise = LAG_NOISE[lag]
                    is_new_launch = (launch.year == year)
                    if is_new_launch:
                        bias_factor = 1.20
                    elif get_spike_mult(sku_id, year, month, ka_id) > 2.0:
                        bias_factor = 0.45
                    else:
                        bias_factor = 1.0

                    forecast = max(0.0, actual * bias_factor * (1 + random.gauss(0, noise)))
                    error_units = round(actual - forecast, 1)
                    error_pct = round(error_units / max(actual, 1), 4) if actual > 0 else ""

                    rows.append({
                        "record_id": str(uuid.uuid4()),
                        "sku_id": sku_id,
                        "key_account_id": ka_id,
                        "fiscal_year": year,
                        "fiscal_month": month,
                        "version_id": f"LAG{lag}",
                        "snapshot_date": date(snap_year, snap_month, 1).isoformat(),
                        "forecast_units": round(forecast, 1),
                        "actual_units": round(actual, 1),
                        "forecast_error_units": error_units,
                        "forecast_error_pct": error_pct,
                        "loaded_at": now_ts,
                    })

    path = FACT_DIR / "fact_forecast_snapshot.csv"
    write_csv(path, rows)
    upload(path)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== SIGNAL mock data generator v4 ===")

    print("\n[1/15] dim_time")
    gen_dim_time()

    print("\n[2/15] dim_division")
    rows = [{"division_id": d[0], "division_name": d[1]} for d in DIVISIONS]
    p = DIM_DIR / "dim_division.csv"; write_csv(p, rows); upload(p)

    print("\n[3/15] dim_brand")
    rows = [{"brand_id": b[0], "brand_name": b[1], "division_id": b[2]} for b in BRANDS]
    p = DIM_DIR / "dim_brand.csv"; write_csv(p, rows); upload(p)

    print("\n[4/15] dim_product_line")
    rows = [{"product_line_id": pl[0], "product_line_name": pl[1], "brand_id": pl[2]} for pl in PRODUCT_LINES]
    p = DIM_DIR / "dim_product_line.csv"; write_csv(p, rows); upload(p)

    print("\n[5/15] dim_sub_product_line")
    rows = [{"sub_product_line_id": s[0], "sub_product_line_name": s[1], "product_line_id": s[2]} for s in SUB_PRODUCT_LINES]
    p = DIM_DIR / "dim_sub_product_line.csv"; write_csv(p, rows); upload(p)

    print("\n[6/15] dim_major_category")
    rows = [{"major_category_id": m[0], "major_category_name": m[1]} for m in MAJOR_CATEGORIES]
    p = DIM_DIR / "dim_major_category.csv"; write_csv(p, rows); upload(p)

    print("\n[7/15] dim_category")
    rows = [{"category_id": c[0], "category_name": c[1], "major_category_id": c[2]} for c in CATEGORIES]
    p = DIM_DIR / "dim_category.csv"; write_csv(p, rows); upload(p)

    print("\n[8/15] dim_subcategory")
    rows = [{"subcategory_id": s[0], "subcategory_name": s[1], "category_id": s[2]} for s in SUBCATEGORIES]
    p = DIM_DIR / "dim_subcategory.csv"; write_csv(p, rows); upload(p)

    print("\n[9/15] dim_channel_type")
    rows = [{"channel_type_id": c[0], "channel_type_name": c[1]} for c in CHANNEL_TYPES]
    p = DIM_DIR / "dim_channel_type.csv"; write_csv(p, rows); upload(p)

    print("\n[10/15] dim_market")
    rows = [{"market_id": m[0], "market_name": m[1], "channel_type_id": m[2]} for m in MARKETS]
    p = DIM_DIR / "dim_market.csv"; write_csv(p, rows); upload(p)

    print("\n[11/15] dim_customer_group")
    rows = [{"customer_group_id": c[0], "customer_group_name": c[1], "market_id": c[2]} for c in CUSTOMER_GROUPS]
    p = DIM_DIR / "dim_customer_group.csv"; write_csv(p, rows); upload(p)

    print("\n[12/15] dim_key_account")
    rows = [{"key_account_id": k[0], "key_account_name": k[1], "customer_group_id": k[2], "channel_type_id": k[3]} for k in KEY_ACCOUNTS]
    p = DIM_DIR / "dim_key_account.csv"; write_csv(p, rows); upload(p)

    print("\n[13/15] dim_sku")
    sku_rows = build_skus()
    p = DIM_DIR / "dim_sku.csv"; write_csv(p, sku_rows); upload(p)
    print(f"  Total SKUs: {len(sku_rows)}")

    print("\n[14/15] dim_version")
    rows = gen_versions()
    p = DIM_DIR / "dim_version.csv"; write_csv(p, rows); upload(p)

    print("\n[15/15] dim_promotion")
    rows = gen_promotions()
    p = DIM_DIR / "dim_promotion.csv"; write_csv(p, rows); upload(p)

    print("\nBuilding SKU-account pairs...")
    pairs = build_sku_account_pairs(sku_rows)
    print(f"  Total pairs: {len(pairs)}")

    print("\n[FACT] fact_financial_plan (2020-2026)...")
    for _ in gen_fact_financial_plan(sku_rows, pairs):
        pass

    print("\n[FACT] fact_pos_weekly...")
    gen_fact_pos_weekly(sku_rows, pairs)

    print("\n[FACT] fact_forecast_snapshot...")
    gen_fact_forecast_snapshot(sku_rows, pairs)

    print("\n=== TASK_02 complete ===")
    hugimals = [s for s in sku_rows if s["is_new_sku"]]
    print(f"Hugimals SKUs: {len(hugimals)}, Total SKUs: {len(sku_rows)}, Pairs: {len(pairs)}")


if __name__ == "__main__":
    main()
