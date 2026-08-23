#!/usr/bin/env bash
# מריץ את כל תהליך ה-ETL: הורדה -> פירסור -> טעינה ל-Postgres
set -e

echo "== שלב 1/3: הורדת קבצים גולמיים =="
python etl/download.py

echo "== שלב 2/3: פירסור ל-CSV =="
python etl/parse.py

echo "== שלב 3/3: טעינה ל-PostgreSQL =="
python etl/load_to_postgres.py

echo "הושלם! אפשר להריץ את השרת עם: ./run_server.sh"
