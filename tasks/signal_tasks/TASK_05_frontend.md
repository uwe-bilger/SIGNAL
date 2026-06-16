# TASK_05 — React Frontend

## Objective
Build the SIGNAL React dashboard with four acts, connected to the FastAPI backend.

## Prerequisites
- TASK_04 complete and API running locally on port 8080

## Project setup
```bash
cd frontend
npx create-react-app . --template typescript
npm install recharts axios react-router-dom @types/react-router-dom
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

## Design system
- Font: Inter (Google Fonts)
- Colors:
  - Background: #0F1117 (near black)
  - Surface: #1A1D27
  - Border: #2A2D3A
  - Primary accent: #6366F1 (indigo)
  - Success: #10B981
  - Warning: #F59E0B
  - Danger: #EF4444
  - Text primary: #F1F5F9
  - Text secondary: #94A3B8
- No default chart library colors — use the palette above consistently
- Cards: rounded-xl, bg surface, 1px border
- No shadows — use borders for depth

## App structure
```
./frontend/src/
├── App.tsx
├── api/
│   └── client.ts          (axios instance pointing to API_URL env var)
├── components/
│   ├── Layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── FilterBar.tsx
│   ├── Charts/
│   │   ├── WaterfallChart.tsx
│   │   ├── LineCompareChart.tsx
│   │   ├── BarStackChart.tsx
│   │   ├── HeatmapTable.tsx
│   │   └── SparkLine.tsx
│   └── Badges/
│       ├── ExceptionBadge.tsx
│       └── VersionBadge.tsx
├── pages/
│   ├── Act1_CurrentState.tsx
│   ├── Act2_Challenger.tsx
│   ├── Act3_Reconciliation.tsx
│   └── Act4_Acquisition.tsx
└── hooks/
    ├── usePlan.ts
    ├── useExceptions.ts
    └── useDimensions.ts
```

## Global filter bar (persistent across all acts)
Dropdowns: Division | Brand | Channel Type | Key Account | Fiscal Year | Version
Filters apply to all charts on the current act.
"Clear filters" button resets to defaults.

## Act 1 — Current state (bottoms-up demand plan)
**What Sales has today.**

Components:
1. **Summary KPI row** — 4 cards: Total Forecast Units, Total Forecast $, vs Budget %, vs Prior Year %
2. **SKU × Retailer matrix** — heatmap table, rows=SKUs, cols=key accounts, values=forecast units, color intensity = volume
3. **Monthly trend** — line chart showing sell-in units by month, current version vs prior year
4. **Top 10 SKUs** — bar chart by total forecast units, colored by division
5. **Exception badges** — surface any flagged SKUs inline (stock risk, override flags)

Filters active: all global filters apply.

## Act 2 — Challenger pack (top-down view)
**The thing that doesn't exist yet at Relatable.**

Components:
1. **Gap analysis** — waterfall chart: Budget → LE → Bottom-up → Gap
2. **Top-down vs bottom-up** — side by side bar chart by division, showing delta
3. **Exception table** — all SKUs with override flags, sorted by override magnitude
4. **Forward exception layer** — next 3 months: which SKUs are at risk (WOS < 4, accuracy flag)
5. **Override drill-down** — click any SKU to see stat forecast vs manual override vs total

## Act 3 — Reconciliation
**Plan vs. LE vs. Budget. Forecast accuracy over time.**

Components:
1. **Version comparison waterfall** — Budget → OP Plan → LE1 → LE2 → LE3 → Latest Est
   Show delta between each version with + / - callouts
2. **LE over time line chart** — all LE versions as separate lines on same chart
   X axis = fiscal months, Y axis = total forecast units
3. **Lag accuracy chart** — MAPE by lag version (LAG1 through LAG10)
   Bar chart: x=lag, y=MAPE%. Lower is better. Benchmark line at 10%.
4. **Forecast evolution** — for a selected SKU, show how the forecast changed
   each month (LAG10 → LAG1 → Actual). Spaghetti line chart.
5. **Bias analysis** — are we consistently over or under forecasting?
   Show mean error (not absolute) by division

## Act 4 — M&A integration (Hugmoals acquisition)
**No history. How do we plan these SKUs?**

Components:
1. **Acquisition overview card** — # of new SKUs, divisions affected, go-live date
2. **New SKU list** — table of all Hugmoals SKUs with category, initial stocking recommendation
   Recommendation logic: median of comparable SKUs in same subcategory
3. **Comparable SKU analysis** — for selected new SKU, show 3 most similar existing SKUs
   with their first-12-months sales curve
4. **Supply risk flags** — SKUs with no demand signal, supplier not yet onboarded
   Show as red flag badges with recommended action
5. **Transition timeline** — horizontal Gantt-style chart showing:
   SKU onboarding → First PO → First Ship → First POS data expected

## Environment variables
```
REACT_APP_API_URL=http://localhost:8080
```
For production this will be the Cloud Run URL.

## Routing
```
/ → Act 1 (default)
/challenger → Act 2
/reconciliation → Act 3
/acquisition → Act 4
```

Left sidebar navigation between acts. Active act highlighted.

## Responsive behavior
- Desktop (>1024px): sidebar + main content
- Mobile (<768px): bottom tab navigation, stacked charts
- All charts use ResponsiveContainer from Recharts

## Verification Checklist
- [ ] `npm start` runs without errors
- [ ] All four acts render without console errors
- [ ] Global filter bar populates from /api/dimensions
- [ ] Act 1 KPI cards show real numbers from API
- [ ] Act 1 SKU × Retailer heatmap renders with data
- [ ] Act 2 waterfall chart renders gap analysis
- [ ] Act 3 version comparison waterfall renders all 6 versions
- [ ] Act 3 lag accuracy chart shows MAPE for LAG1-LAG10
- [ ] Act 4 new SKU list shows all 20 Hugmoals SKUs
- [ ] Filters update charts when changed
- [ ] App renders correctly on mobile viewport (375px)
- [ ] No hardcoded data — everything comes from API
