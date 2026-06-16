import os
from functools import lru_cache
from google.cloud import bigquery

PROJECT = "signal-499604"
DATASET = "signal_dw"
DS = f"{PROJECT}.{DATASET}"


@lru_cache(maxsize=1)
def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


def run_query(sql: str) -> list[dict]:
    client = get_client()
    return [dict(row) for row in client.query(sql).result()]


def q(table: str) -> str:
    return f"`{DS}.{table}`"
