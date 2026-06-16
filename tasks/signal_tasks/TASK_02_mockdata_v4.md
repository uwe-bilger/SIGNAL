# TASK_02 — Generate Mock Data (v3 — Verified from Interview Transcript)

## Objective
Generate all mock data using REAL Relatable product names, real SKU format,
real channel structure, and verified facts from Amit Bansal's interview.
Upload to GCS bucket `signal-raw-data`.

## Verified company facts (from interview transcript)
- Revenue target: ~$200M by end of 2026 (Amit's words: "going to be a $200M company")
- Fiscal year: January 1 – December 31 (Gregorian calendar, confirmed by Amit)
- Budget set: March/April of current year (LE-based, not prior year budget)
- Products: 150+ SKUs, single-buy (not replenishable — you buy it once)
- Lead times: 4 months total (60 days production + 45 days ocean + 15 days buffer)
- Sourcing: China primary, Vietnam/Cambodia/India secondary
- Air freight: Used on viral moments, sold at a loss strategically
- Tools: Alloy (POS/sell-through), NetSuite (orders), Excel/Google Sheets (planning)
- Data pain: Excel maxing out at 1M rows — SQL migration in progress
- KPIs: Exist but unused. 3-month bias tracking for POS and shipments exists.
- Forecast ownership: Sales does bottoms-up by SKU. Demand planning is challenger.
- TikTok Shop: Named active growth channel
- Claude Enterprise: Whole company is on Claude (Amit explicitly named this)
- Hugimals: Just acquired ("this past week"), e-commerce-first, weighted plush
- Emotional Support Pals: Started with 3 SKUs (fries, flowers, mushrooms), now 30+
  — described as #2 largest category and "just flying"

---

## SKU ID format
Mirror real Shopify/Alloy source data conventions:
```
{BRAND_CODE}-{PRODUCT_CODE}-{VARIANT}
Examples:
  WDYM-CORE-001    What Do You Meme? Core Game
  WDYM-NSFW-001    WDYM NSFW Expansion
  BUZZ-CORE-001    Buzzed Core Game
  REL-ESP-001      Emotional Support Pals Character 1
  REL-TSCK-001     Tower Stack (specific SKU Amit mentioned)
  HUG-CLAS-001     Hugimals Classic Character 1 (acquisition)
```

Brand codes:
- WDYM = What Do You Meme? franchise
- BUZZ = Buzzed franchise
- REL  = Relatable Originals (ESP, Cozy, lifestyle, wellness)
- BSG  = Bee Street Games
- HAK  = Hunt A Killer
- LIC  = Licensed products (Pop-Tarts, creator collabs)
- HUG  = Hugimals World (acquisition — no history)

---

## Divisions (3)
```
DIV-01: Games & Play
DIV-02: Lifestyle & Comfort  ← #2 category (ESP) is "flying" per Amit
DIV-03: Hugimals World       ← just acquired, e-commerce-first
```

---

## Brands (7)
```
BRD-01: What Do You Meme?   (DIV-01)
BRD-02: Buzzed              (DIV-01)
BRD-03: Relatable Originals (DIV-01) — party, relationship, family
BRD-04: Bee Street Games    (DIV-01)
BRD-05: Hunt A Killer       (DIV-01)
BRD-06: Lifestyle & Comfort (DIV-02) — ESP, Cozy, Outdoor, Wellness
BRD-07: Hugimals World      (DIV-03)
```

---

## Real SKUs — 150 Relatable + 30 Hugimals = 180 total

### WDYM Franchise — ~50 SKUs

**Core games (~8 SKUs):**
- WDYM-CORE-001: What Do You Meme? Core Game — MSRP $24.99, cost $9.50
- WDYM-CORE-002: What Do You Meme? GIF Edition — MSRP $24.99, cost $9.50
- WDYM-CORE-003: What Do You Meme? Family Edition — MSRP $19.99, cost $7.50
- WDYM-FMLY-001: New Phone Who Dis?™ — MSRP $21.99, cost $8.50
- WDYM-FMLY-002: New Phone Who Dis? Family Edition — MSRP $19.99, cost $7.50
- WDYM-FMLY-003: Guess The Gibberish Family Game — MSRP $19.99, cost $7.50
- WDYM-CRSR-001: What Do You Meme? Career Series: Teachers — MSRP $24.99, cost $9.50
- WDYM-CRSR-002: What Do You Meme? Career Series: Nurses — MSRP $24.99, cost $9.50

**WDYM Expansion packs (~12 SKUs):**
- WDYM-XPAK-001: WDYM NSFW Expansion Pack — MSRP $9.99, cost $3.50
- WDYM-XPAK-002: WDYM Fresh Memes #1 Expansion — MSRP $11.99, cost $4.25
- WDYM-XPAK-003: WDYM Fresh Memes #2 Expansion — MSRP $11.99, cost $4.25
- WDYM-XPAK-004: WDYM After Hours Expansion — MSRP $14.99, cost $5.50
- WDYM-XPAK-005: WDYM Trisha Paytas Expansion — MSRP $9.99, cost $3.50
- WDYM-XPAK-006: New Phone Who Dis? Expansion — MSRP $12.99, cost $4.75
- WDYM-XPAK-007: WDYM Pop Culture Pack Vol 1 — MSRP $11.99, cost $4.25
- WDYM-XPAK-008: WDYM Pop Culture Pack Vol 2 — MSRP $11.99, cost $4.25
- WDYM-XPAK-009: WDYM Holiday Edition Expansion — MSRP $14.99, cost $5.50
- WDYM-XPAK-010: WDYM Gen Z Edition Expansion — MSRP $11.99, cost $4.25
- WDYM-XPAK-011: WDYM Sports Fan Expansion — MSRP $11.99, cost $4.25
- WDYM-XPAK-012: WDYM Gaming Edition Expansion — MSRP $11.99, cost $4.25

**Licensed/collab SKUs (~6 SKUs):**
- LIC-PTRT-001: What Do You Meme? x Pop-Tarts Edition — MSRP $24.99, cost $10.50
- LIC-PTRT-002: Pop-Tarts x Relatable Party Pack — MSRP $19.99, cost $8.00
- LIC-CRTR-001: Hunt A Killer: Sam & Colby Edition — MSRP $34.99, cost $14.00
- LIC-CRTR-002: WDYM Creator Series Vol 1 — MSRP $24.99, cost $9.50
- LIC-CRTR-003: WDYM Creator Series Vol 2 — MSRP $24.99, cost $9.50
- LIC-CRTR-004: WDYM TikTok Edition — MSRP $21.99, cost $8.50

**More WDYM/party games (~24 SKUs):**
Include these real names confirmed in interview/brief:
- REL-PRTY-001: Incohearent™ — MSRP $21.99, cost $8.50
- REL-PRTY-002: Incohearent Family Edition — MSRP $19.99, cost $7.50
- REL-PRTY-003: Incohearent Fresh Phrases Expansion — MSRP $12.99, cost $4.75
- REL-PRTY-004: For the Girls™ — MSRP $21.99, cost $8.50
- REL-PRTY-005: For the Girls Expansion — MSRP $14.99, cost $5.50
- REL-PRTY-006: InQueeries — MSRP $19.99, cost $7.50
- REL-PRTY-007: Stir The Pot — MSRP $19.99, cost $7.50
- REL-PRTY-008: Live Laugh Lose — MSRP $19.99, cost $7.50
- REL-PRTY-009: Over-Rated™ — MSRP $19.99, cost $7.50
- REL-PRTY-010: Asking For A Friend — MSRP $21.99, cost $8.50
- REL-PRTY-011: Who Killed Mia? — MSRP $29.99, cost $11.00
- REL-PRTY-012: Kollide — MSRP $24.99, cost $9.50
- REL-TSCK-001: Tower Stack (Amit specifically named this SKU) — MSRP $19.99, cost $7.50
Generate 11 more realistic party/adult game SKUs in $17.99-$29.99 range.

---

### Buzzed Franchise — ~12 SKUs
- BUZZ-CORE-001: Buzzed™ Core Game — MSRP $19.99, cost $7.50
- BUZZ-XPAK-001: Buzzed™ Expansion Pack #1 — MSRP $14.99, cost $5.50
- BUZZ-XPAK-002: Buzzed™ Expansion Pack #2 — MSRP $14.99, cost $5.50
- BUZZ-XPAK-003: Buzzed™ Holiday Edition — MSRP $19.99, cost $7.50
- BUZZ-DXED-001: Buzzed™ Deluxe Edition — MSRP $29.99, cost $11.00
- BUZZ-SHOT-001: Lil Cheers Shot Glass Set — MSRP $14.99, cost $4.50
- BUZZ-SHOT-002: Lil Cheers Mini Bottle Set — MSRP $12.99, cost $3.75
- BUZZ-SHOT-003: Lil Cheers Party Pack — MSRP $19.99, cost $6.50
Generate 4 more Buzzed/drinking SKUs.

---

### Relatable Family/Relationship/Novelty — ~20 SKUs
- REL-RLSH-001: Let's Get Deep — MSRP $21.99, cost $8.50
- REL-RLSH-002: Let's Get Deep Expansion — MSRP $14.99, cost $5.50
- REL-FMLY-001: Cows in Space (2025 Toy of Year finalist) — MSRP $24.99, cost $9.50
- REL-FMLY-002: Silly Poopy's Hide & Seek™ — MSRP $12.99, cost $5.00
- REL-FMLY-003: Grounded for Life™ — MSRP $19.99, cost $7.50
- REL-FMLY-004: All of Us — MSRP $17.99, cost $6.50
- REL-OUTD-001: Iconic Float™ Giant Ramen Pool Float — MSRP $29.99, cost $11.00
- REL-OUTD-002: Iconic Float™ Giant Pizza Pool Float — MSRP $29.99, cost $11.00
- REL-OUTD-003: Iconic Float™ Giant Taco Pool Float — MSRP $34.99, cost $13.00
- REL-WLNS-001: Happy Helpers Menstruation Crustacean Heating Pad — MSRP $24.99, cost $9.00
- REL-WLNS-002: Happy Helpers Anxiety Relief Kit — MSRP $19.99, cost $7.50
- REL-WBSB-001: WabiSabi Kitty Club Blind Box — MSRP $14.99, cost $5.00
- REL-PETS-001: Relatable Pets Pawty Time Game — MSRP $19.99, cost $7.50
Generate 7 more Relatable originals SKUs.

---

### Bee Street Games — ~8 SKUs
- BSG-CORE-001: Bee Street Games Flagship — MSRP $24.99, cost $9.50
Generate 7 more BSG SKUs in $17.99-$29.99.

---

### Hunt A Killer — ~8 SKUs
- HAK-CORE-001: Hunt A Killer Season 1 — MSRP $29.99, cost $12.00
- HAK-SUBS-001: Hunt A Killer Subscription Box — MSRP $29.99/month, cost $11.00
Generate 6 more HAK titles.

---

### Emotional Support Pals + Lifestyle — ~32 SKUs
CRITICAL: Amit confirmed ESP started with 3 SKUs and is now 30+, #2 largest category.
Original 3 SKUs (earliest launch dates):
- REL-ESP-001: Emotional Support Pals — French Fries (original) — MSRP $24.99, cost $8.50, launch 2020
- REL-ESP-002: Emotional Support Pals — Flowers (original) — MSRP $24.99, cost $8.50, launch 2020
- REL-ESP-003: Emotional Support Pals — Mushroom (original) — MSRP $24.99, cost $8.50, launch 2020

Then generate 27 more ESP characters launched 2021-2024:
Examples: Axolotl, Ghost, Frog, Cactus, Cloud, Avocado, Rainbow, Pizza Slice,
Taco, Sushi, Dinosaur, Crab, Jellyfish, Succulent, Croissant, Boba Tea,
Hot Dog, Strawberry, Donut, Narwhal, Sloth, Cactus Deluxe, etc.
Pricing: $19.99-$34.99, cost $7.00-$12.00.
All REL-ESP-XXX format.

Cozy Concepts Blankets (~5 SKUs):
- REL-COZY-001: Cozy Concepts Blanket Classic — MSRP $39.99, cost $14.00
- REL-COZY-002: Cozy Concepts Meme Edition — MSRP $44.99, cost $15.50
- REL-COZY-003: Cozy Concepts Holiday Blanket — MSRP $44.99, cost $15.50
- REL-COZY-004: Cozy Concepts Weighted Blanket — MSRP $59.99, cost $21.00
- REL-COZY-005: Cozy Concepts Mini Throw — MSRP $29.99, cost $10.50

---

### Hugimals World — 30 SKUs (ALL is_new_sku=True, launch 2024-07+)
E-commerce-first (Amit confirmed: "mostly an ecom-based company").
Distribution starts narrow — Amazon 1P, DTC, then adds retail.

**Hugimals Classic — 4.5 lb weighted plush ($68):**
- HUG-CLAS-001: Sam the Sloth — MSRP $68.00, cost $22.00
- HUG-CLAS-002: Harper the Pig — MSRP $68.00, cost $22.00
- HUG-CLAS-003: Forrest the Fox — MSRP $68.00, cost $22.00
- HUG-CLAS-004: Bowie the Panda — MSRP $68.00, cost $22.00
- HUG-CLAS-005: Berkeley the Bear — MSRP $68.00, cost $22.00
- HUG-CLAS-006: Luna the Bunny — MSRP $68.00, cost $22.00
- HUG-CLAS-007: Charlie the Cat — MSRP $68.00, cost $22.00
- HUG-CLAS-008: Mochi the Panda Cub — MSRP $68.00, cost $22.00
- HUG-CLAS-009: Finn the Seal — MSRP $68.00, cost $22.00
- HUG-CLAS-010: Daisy the Cow — MSRP $68.00, cost $22.00

**Hugarounds — warmable/freezable 2.5 lb ($48):**
- HUG-RND-001: Pax the Penguin Hugaround — MSRP $48.00, cost $16.00
- HUG-RND-002: Ollie the Orangutan Hugaround — MSRP $48.00, cost $16.00
- HUG-RND-003: Sawyer the Sloth Hugaround — MSRP $48.00, cost $16.00
- HUG-RND-004: Indigo the Octopus Hugaround — MSRP $48.00, cost $16.00
- HUG-RND-005: Ruby the Raccoon Hugaround — MSRP $48.00, cost $16.00
- HUG-RND-006: Theo the Tiger Hugaround — MSRP $48.00, cost $16.00
- HUG-RND-007: Ivy the Iguana Hugaround — MSRP $48.00, cost $16.00
- HUG-RND-008: Cleo the Chameleon Hugaround — MSRP $48.00, cost $16.00

**Berkeley the Bat variant ($45):**
- HUG-BERK-001: Berkeley the Bat — MSRP $45.00, cost $15.00
- HUG-BERK-002: Berkeley the Bat Glow Edition — MSRP $49.00, cost $16.50

**Hug Babies mini ($12):**
- HUG-BABY-001: Hug Baby Bowie the Panda — MSRP $12.00, cost $4.00
- HUG-BABY-002: Hug Baby Sam the Sloth — MSRP $12.00, cost $4.00
- HUG-BABY-003: Hug Baby Forrest the Fox — MSRP $12.00, cost $4.00
- HUG-BABY-004: Hug Baby Luna the Bunny — MSRP $12.00, cost $4.00

**Bundles & Accessories:**
- HUG-BNDL-001: Sloth With Heart Bundle — MSRP $104.00, cost $34.00
- HUG-BNDL-002: Red and Rose Hearts Bundle — MSRP $126.00, cost $41.00
- HUG-BNDL-003: Black and White Hearts Bundle — MSRP $126.00, cost $41.00
- HUG-BNDL-004: Hugaround + Classic Bundle — MSRP $110.00, cost $36.00
- HUG-ACCS-001: Weighted Hug Sweatshirt — MSRP $128.00, cost $42.00
- HUG-ACCS-002: Hugimals Travel Bag — MSRP $24.99, cost $8.50

---

## Category Hierarchy

### Major Categories (3)
- MCAT-01: Games & Entertainment
- MCAT-02: Lifestyle & Home
- MCAT-03: Wellness & Comfort

### Categories (9)
Games & Entertainment:
- CAT-01: Adult Party Games
- CAT-02: Family & Kids Games
- CAT-03: Mystery & Strategy Games

Lifestyle & Home:
- CAT-04: Outdoor & Novelty
- CAT-05: Home Comfort
- CAT-06: Licensed & Collectible

Wellness & Comfort:
- CAT-07: Emotional Wellness (ESP — #2 category, fastest growing)
- CAT-08: Therapeutic Plush (Hugimals)
- CAT-09: Self-Care & Accessories

### Subcategories (18)
Adult Party Games: Meme & Card Games | Drinking & Social Games
Family & Kids Games: Family Card Games | Kids Toys
Mystery & Strategy: Mystery Box Games | Subscription Games
Outdoor & Novelty: Pool & Outdoor | Novelty Gifts
Home Comfort: Blankets & Throws | Lifestyle Accessories
Licensed & Collectible: Brand Collabs | Creator Series
Emotional Wellness: Support Characters | Plush Accessories
Therapeutic Plush: Weighted Plush | Warmable Plush
Self-Care: Self-Care Kits | Wellness Accessories

---

## Geography — 5 channel types (TikTok Shop confirmed by Amit)

### Channel Types
- CHN-01: Retail
- CHN-02: E-commerce
- CHN-03: DTC
- CHN-04: TikTok Shop (Amit: "TikTok Shop is a named active growth channel")
- CHN-05: Distributor

### Markets
Retail: Northeast, Southeast, Midwest, West, Southwest
E-commerce: Amazon US, Walmart.com, Target.com
DTC: Relatable.com, Subscribe & Save
TikTok Shop: TikTok Shop US
Distributor: UNFI, KeHE

### Key Accounts
Retail (named by Amit — Walmart is #1):
- Walmart (TOP account, top supplier since 2020 — highest volume)
- Target
- Amazon (cross-listed under e-commerce too)
- CVS, Walgreens, Kroger, Five Below, GameStop, Barnes & Noble
- Urban Outfitters, TJ Maxx, Albertsons, HEB

E-commerce:
- Amazon 1P (vendor central — primary)
- Amazon 3P (seller central)
- Walmart.com, Target.com

DTC: Relatable.com Direct, Subscribe & Save
TikTok Shop: TikTok Shop US
Distributors: UNFI East, UNFI West, KeHE

---

## Time dimension — DUAL CALENDAR (critical ETL requirement)

### Why both calendars are needed
Relatable's financial reporting (NetSuite, budget) runs Gregorian (Jan–Dec).
Alloy POS exports run on a 4-4-5 retail fiscal calendar.
SIGNAL must harmonize both — this is a real production ETL problem
and directly demonstrates value in the interview context.

The ETL harmonization (Alloy 4-4-5 → Gregorian) is what Relatable's
team currently does manually in Excel, maxing out at 1M rows.
SIGNAL solves this properly.

### Generate daily rows 2019-01-01 to 2026-12-31

Each row in dim_time has ALL of the following fields:

**Gregorian fields (financial/NetSuite side):**
- date_id (DATE, primary key)
- calendar_year (INT)
- calendar_quarter (INT, 1-4)
- calendar_month (INT, 1-12)
- calendar_month_name (STRING, e.g. "January")
- calendar_week_of_year (INT, ISO week)
- day_of_week (INT, 1=Mon, 7=Sun)
- is_weekend (BOOL)

**4-4-5 Fiscal fields (Alloy/POS side):**
Fiscal year starts on the first Monday of February each year.
Pattern: each quarter = 4 weeks + 4 weeks + 5 weeks = 13 weeks.
- fiscal_year (INT, e.g. 2024)
- fiscal_quarter (INT, 1-4)
- fiscal_month (INT, 1-12, within fiscal year)
- fiscal_week (INT, 1-52 or 53)
- fiscal_period_name (STRING, e.g. "FY2024-Q1-P01-W03")
- fiscal_445_pattern (STRING, "4", "4", or "5" — which week-count month)

**Partial week harmonization fields:**
A "partial week" is any fiscal week that crosses a Gregorian month boundary.
For example, if a fiscal week runs Mon Mar 28 – Sun Apr 3, it is partial:
3 days belong to March, 4 days belong to April.

- is_partial_week (BOOL, True if this fiscal week crosses a Gregorian month boundary)
- partial_week_prior_month_days (INT, days of this fiscal week in the prior Gregorian month, 0 if not partial)
- partial_week_current_month_days (INT, days of this fiscal week in the current Gregorian month)
- partial_week_proration_factor (FLOAT, fraction of week's volume attributable to current Gregorian month)
  Formula: partial_week_proration_factor = calendar_days_in_current_month / 7
  For non-partial weeks: 1.0

**ETL use of proration:**
When aggregating Alloy weekly POS to Gregorian months:
  monthly_pos = SUM(weekly_pos * partial_week_proration_factor)
This is what Relatable currently does in Excel manually.
SIGNAL automates it via dim_time.

### 4-4-5 algorithm
```python
# Pseudocode for 4-4-5 fiscal calendar generation
# Fiscal year N starts on the first Monday of February of year N

def get_fiscal_year_start(year):
    feb1 = date(year, 2, 1)
    # First Monday of February
    days_until_monday = (7 - feb1.weekday()) % 7
    return feb1 + timedelta(days=days_until_monday)

# Week pattern per quarter: [4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5]
# (12 months, alternating 4-4-5 per quarter)
WEEKS_PER_MONTH = [4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5]

# For each date, compute which fiscal year/quarter/month/week it falls in
# by counting weeks forward from fiscal_year_start
```

---

## Versions
Financial versions (budget set in March/April of current year per Amit):
- BUDGET (set March/April of same year)
- OP_PLAN
- LE1, LE2, LE3
- LATEST_EST

Forecast accuracy: LAG1 through LAG10

---

## Promotions — real Relatable-style names
8 promotions per year (2020-2026) = ~56 total:
- "Holiday Party Games Feature — Walmart" (Nov-Dec)
- "Back to School WDYM Display — Target" (Aug-Sep)
- "Valentine's Day Let's Get Deep — Amazon" (Jan-Feb)
- "Prime Day Games Deal — Amazon 1P" (Jul)
- "Super Bowl Buzzed Promo — Retail" (Jan-Feb)
- "Summer Pool Float Launch — Target & Walmart" (May-Jun)
- "TikTok Viral Boost — Tower Stack" (random months)
- "ESP Holiday Gift Push — Multi-Channel" (Nov-Dec)
- "Pop-Tarts Collab Launch" (varies)
Types: TPR, Display, BOGO, Holiday, Launch, Feature, TikTok_Boost
Lift: 15%-60% (TikTok boosts 40-60%)

---

## Fact data — critical business rules from interview

### Single-buy product logic
Amit: "You buy our product once, that's it."
This means NO replenishment curve. Sales pattern:
- Launch spike (months 1-3)
- Moderate ongoing (months 4-12, gift/discovery purchases)
- Long tail / decline (year 2+)
Exception: WDYM Core, Buzzed Core — true evergreen, steady replenishment

### Seasonality
Games: STRONG Q4 (Amit: "Q4 can be more than half of annual revenue")
- Adult Party Games: peak Nov-Dec (holiday), secondary Jul-Aug
- Drinking Games: peak Dec-Jan, Feb Super Bowl
- Family Games: peak Nov-Dec almost exclusively
- Pool/Outdoor: peak May-Aug, near zero Oct-Mar
- ESP/Comfort: peak Nov-Dec (gifting), strong Jan (wellness/new year)
- TikTok Shop: can spike ANY month — viral moments unpredictable

### Volume scale (calibrated to $200M revenue)
At ~$20 avg MSRP = ~10M units/year total.
Scale per channel/SKU:
- Walmart (top account): top SKUs 2000-15000 units/month Nov-Dec
- Target: 1500-10000 units/month peak
- Amazon 1P: 1000-8000 units/month peak
- TikTok Shop: 200-1000 normal, up to 10000 during viral spike
- DTC: 300-2000 units/month
- Smaller accounts: 100-800 units/month

### Viral spikes (Amit: "when it's viral you need to feed that moment")
Pick 3 SKUs/year (2021-2026) for TikTok viral spike:
- 3x-8x normal volume for 1-3 months
- Air freight implied (selling at a loss)
- TikTok Shop spikes first, then Amazon, then Retail (2-4 week lag)
- Post-spike: sharp reversion to baseline
- Tower Stack (REL-TSCK-001) should have at least 2 viral spikes

### ESP growth story (Amit: "started with 3, now 30+, #2 category, just flying")
- ESP-001/002/003 (fries/flowers/mushrooms): launched 2020, steady growth
- Each new ESP character: launch spike then settles to 30-50% of original trio volume
- Overall ESP category: 25% YoY growth from 2020-2024
- ESP becomes larger than Adult Party Games in total units by 2024

### Hugimals distribution ramp (e-commerce-first)
2024-07 to 2024-09: Amazon 1P + Relatable.com only, 100-400 units/SKU
2024-10 to 2024-12: Add TikTok Shop, holiday push 400-1500 units/SKU
2025-01 to 2025-06: Add Target + Walmart, 500-2000 units/SKU
2025-07+: Full distribution, 800-3000 units/SKU
Comparable SKU: REL-ESP line (for Act 4 recommendation engine)

### YoY growth
Games & Play: 8-10% YoY
ESP/Lifestyle: 20-25% YoY ("just flying")
Licensed: launch spike, -30% decay months 3-6, then stable
Hugimals: n/a (new)

### Bias flags (Amit has 3-month bias tracking for POS and shipments)
Build in systematic over-forecasting bias for launches:
- New game launches: sales overforecasts by 15-30% on average
- Viral SKUs: underforecast by 40-80% on viral months
This makes the bias analysis in Act 3 show real patterns.

---

## File naming
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
dimensions/dim_time.csv
dimensions/dim_version.csv
dimensions/dim_promotion.csv
facts/fact_financial_plan_2020.csv
facts/fact_financial_plan_2021.csv
facts/fact_financial_plan_2022.csv
facts/fact_financial_plan_2023.csv
facts/fact_financial_plan_2024.csv
facts/fact_financial_plan_2025.csv
facts/fact_financial_plan_2026.csv
facts/fact_pos_weekly.csv
facts/fact_forecast_snapshot.csv
```

---

## Verification Checklist
- [ ] `dim_sku.csv` has 180 rows (150 Relatable + 30 Hugimals)
- [ ] All SKU IDs follow BRAND-PROD-NNN format
- [ ] REL-TSCK-001 (Tower Stack) exists — Amit named this SKU
- [ ] REL-ESP-001/002/003 are fries/flowers/mushrooms with 2020 launch dates
- [ ] 30 Hugimals SKUs all have is_new_sku=True
- [ ] `dim_time.csv` has rows from 2019-01-01 to 2026-12-31 (~2922 rows)
- [ ] Both Gregorian AND 4-4-5 fiscal fields present in every row
- [ ] Fiscal year starts first Monday of February each year
- [ ] is_partial_week=True for weeks crossing Gregorian month boundaries
- [ ] partial_week_proration_factor sums correctly (spot check: one partial week)
- [ ] fiscal_445_pattern alternates 4,4,5,4,4,5,4,4,5,4,4,5 per fiscal year
- [ ] `dim_channel_type.csv` has 5 rows including TikTok Shop
- [ ] Walmart has highest unit volumes across all SKUs
- [ ] Q4 is visibly 2x-3x other quarters for Games division
- [ ] ESP category shows 25% YoY growth trajectory
- [ ] Tower Stack has 2+ visible viral spikes in TikTok Shop channel
- [ ] Launch bias: new games overforecast by ~20% on average
- [ ] Hugimals data starts 2024-07, e-commerce channels only initially
- [ ] Budget version timestamps reflect March/April of current year
- [ ] All files uploaded to `gs://signal-raw-data/raw/`
- [ ] Spot check: WDYM-CORE-001 at Walmart Nov-Dec = 3-5x vs Feb-Mar
