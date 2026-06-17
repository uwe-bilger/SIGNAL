import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./secrets/signal-key.json"
from google.cloud import bigquery
client = bigquery.Client(project="signal-499604")
ds = "signal-499604.signal_dw"

sql = """
    SELECT p.sku_id, p.key_account_id, t.calendar_year, t.calendar_month, t.calendar_month_name,
           SUM(p.pos_units * CAST(t.partial_week_proration_factor AS FLOAT64))   AS pos_units_monthly,
           SUM(p.pos_dollars * CAST(t.partial_week_proration_factor AS FLOAT64)) AS pos_dollars_monthly,
           AVG(p.inventory_on_hand_units)                       AS avg_inventory,
           AVG(p.weeks_of_supply)                               AS avg_wos
    FROM `signal-499604.signal_dw.fact_pos_weekly` p
    JOIN `signal-499604.signal_dw.dim_time` t ON p.date_id = CAST(t.date_id AS DATE)
    GROUP BY 1,2,3,4,5
"""
vt = bigquery.Table(f"{ds}.v_pos_monthly")
vt.view_query = sql
client.delete_table(f"{ds}.v_pos_monthly", not_found_ok=True)
client.create_table(vt)
print("v_pos_monthly created")
rows = list(client.query(f"SELECT COUNT(*) AS n FROM `{ds}.v_pos_monthly`").result())
print("v_pos_monthly rows:", rows[0]["n"])
