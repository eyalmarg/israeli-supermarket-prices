#!/usr/bin/env bash
# מריץ את כל תהליך ה-ETL: הורדה -> טעינה ל-Postgres
set -e
cd "$(dirname "$0")"

echo "== שלב 1/2: הורדת קובצי סניפים ומחירים מלאים =="
python etl/download.py

echo "== שלב 2/2: טעינה ל-PostgreSQL =="
python etl/load.py

echo "הושלם! אפשר להריץ את השרת עם: ./run_server.sh"
