# NEXT

A running snapshot of where SIGNAL stands. Update this at the end of every
working session (chat or Claude Code) before closing the tab. Keep it
short — this file's only job is to exist, not to be smart.

## Now

Connect Power BI Desktop to BigQuery `signal_dw` (native connector) and
explore the data as it currently stands — no build work yet, just
connecting and looking around to get a feel for the shape of it.

## Next

- **The React/Cloudflare web visualization is paused, not abandoned.**
  It was the right call for Relatable specifically (non-Microsoft shop,
  needed a public shareable URL); Thermo Fisher is a different
  environment and likely already has Power BI in its stack, so a custom
  web app isn't the priority here. No need to interrupt or check on
  Claude Code's current TASK_08 run — whatever it produces on the
  frontend side is fine to let finish or sit as-is. Just no *new* web
  visualization work from here.
- **Active visualization work shifts to Power BI, supported by Claude
  Code.** Reasons: more control over visualization and data, and Uwe
  wants to stay hands-on with Power BI skills rather than have it fully
  automated. The BigQuery/ETL/schema portions of TASK_08 remain fully
  relevant regardless of which tool renders the data.
- Soften Act 4's "no history" framing to "partial/degraded history":
  some sites have deep legacy data, some have gaps around their ERP
  migration wave, none are a hard zero. More realistic than a clean
  acquisition cutoff, and a richer teaching case ("how much do you trust
  this SKU's history" beats "does it have history").
- Once the data's been explored in Power BI, revisit the Shewhart
  detection engine question in its new form: precompute control limits
  and pattern classification as a BigQuery view, or build it as DAX
  measures inside Power BI. Same underlying design question as before,
  different implementation target.
- Build the labeled mock-data pattern library (true bias run, genuine
  level shift tied to a site's JDE cutover date, single one-time shock,
  trend/drift, increased noise, and the timing-boundary false-positive
  case) — still relevant regardless of visualization tool.

## Parked

- MCP angle (renewed interest after Bas's content) — no concrete plan
  yet, keep as a live interest to revisit
- Channel/geography taxonomy (Direct Sales / Distributor / OEM Contract /
  CDMO Key Account) is a placeholder — validate against real FSD
  CRM/channel data once Uwe has system access
- European FSD site names are placeholders (Germany/Ireland guesses) —
  swap for real site names once confirmed
- Process-maturity attribute per site (Stage 1–5, FSD vs. CSD comparison)
  — stretch goal, not blocking anything
- Original "diagnostics view: inline vs. dedicated page vs. both"
  question — superseded by the Power BI pivot, but the same underlying
  choice (in-context flags vs. a dedicated exploration report) will
  resurface as a Power BI report-design decision later
