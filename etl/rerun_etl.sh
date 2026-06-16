#!/bin/bash
export GOOGLE_APPLICATION_CREDENTIALS=./secrets/signal-key.json
python etl/generate_mock_data.py
python etl/load_to_bigquery.py
echo "ETL complete."
