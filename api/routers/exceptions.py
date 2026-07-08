from fastapi import APIRouter
from typing import Optional
from db.bigquery_client import run_query, q

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])

# TASK_09: exception flags come from v_exception_flags — short-lag forecast
# accuracy (bias / MAPE), derived at query time from the forecast-vs-actuals
# join. The old stock-risk / weeks-of-supply flags are GONE: supply/inventory
# is out of scope for this model and returns in its own follow-up task.


@router.get("")
def get_exceptions(
    fiscal_year: int,
    division:    Optional[str] = None,
):
    div_filter = f"AND e.division_id = '{division}'" if division else ""
    sql = f"""
        SELECT
            e.sku_id,
            e.sku_name,
            e.division_id,
            e.is_new_sku,
            e.fiscal_year,
            e.mean_bias,
            e.mape,
            e.bias_flag,
            e.accuracy_flag,
            e.new_sku_flag
        FROM {q('v_exception_flags')} e
        WHERE e.fiscal_year = {int(fiscal_year)}
          {div_filter}
          AND (e.bias_flag = 1 OR e.accuracy_flag = 1 OR e.new_sku_flag = 1)
        ORDER BY e.accuracy_flag DESC, ABS(e.mean_bias) DESC
        LIMIT 500
    """
    return run_query(sql)
