# Climate Intelligence — Heatwave Monitoring, Prediction & Early Warning

DBMS mini project: Flask + PostgreSQL + scikit-learn.

## Setup

1. Install Python 3.10+ and PostgreSQL.
2. In this folder:
   ```
   pip install -r requirements.txt
   ```
3. In pgAdmin, create a database named `climate_intelligence`, then run `schema.sql` in it
   (the CREATE DATABASE line is commented out).
4. Tell the app your PostgreSQL password (Windows Command Prompt):
   ```
   set DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/climate_intelligence
   ```
5. Load the data (run once only, or the rows get duplicated):
   ```
   python load_data.py
   ```
6. Start the app and open http://127.0.0.1:5000
   ```
   python app.py
   ```

## Pages

- **Overview** — stats and a 3D bar map of peak temperature per station (three.js, bundled in `static/vendor`).
- **Monitoring** — observations joined with stations, filterable by station.
- **Prediction** — Random Forest classifier (demonstration; risk is defined by max temperature).
- **Early warning** — top 10 hottest days per risk level (CTE + ROW_NUMBER window function).

Risk levels (academic, not official IMD): Normal < 38°C, Moderate 38–40.9, High 41–43.9, Extreme ≥ 44.
