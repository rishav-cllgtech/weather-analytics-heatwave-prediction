from flask import Flask, render_template, request
import os
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

FEATURES = [
    "avg_temp", "min_temp", "max_temp", "wind_speed",
    "air_pressure", "rainfall", "month"
]

MODEL = None

def db():
    return psycopg2.connect(DATABASE_URL)

def heatwave_level(temp):
    if temp is None:
        return "Unknown"
    temp = float(temp)
    if temp >= 44:
        return "Extreme"
    if temp >= 41:
        return "High"
    if temp >= 38:
        return "Moderate"
    return "Normal"

def train_model():
    """Train a small demonstration classifier from the project's weather data.
    The project label is a simple academic risk classification based on maximum
    temperature; it is not an official meteorological heatwave declaration.
    """
    global MODEL
    try:
        data = pd.read_csv("weather_dataset_5000.csv")
        # month is stored as a name ("April"); convert to a number so the model can use it
        data["month"] = pd.to_datetime(data["month"], format="%B").dt.month
        for col in ["avg_temp", "min_temp", "max_temp", "wind_speed", "air_pressure", "rainfall", "month"]:
            data[col] = pd.to_numeric(data[col], errors="coerce")
        data = data.dropna(subset=["avg_temp", "min_temp", "max_temp"])
        data["wind_speed"] = data["wind_speed"].fillna(data["wind_speed"].median())
        data["air_pressure"] = data["air_pressure"].fillna(data["air_pressure"].median())
        data["rainfall"] = data["rainfall"].fillna(data["rainfall"].median())
        data["risk"] = data["max_temp"].apply(heatwave_level)
        data = data[data["risk"] != "Unknown"]
        X = data[FEATURES]
        y = data["risk"]
        MODEL = RandomForestClassifier(n_estimators=150, random_state=42, class_weight="balanced")
        MODEL.fit(X, y)
    except Exception as exc:
        print("Model training skipped:", exc)

@app.route("/")
def index():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT COUNT(*) AS total,
               COUNT(DISTINCT station_id) AS stations,
               COUNT(*) FILTER (WHERE max_temp >= 41) AS high,
               MIN(EXTRACT(YEAR FROM date_of_record))::int AS first_year,
               MAX(EXTRACT(YEAR FROM date_of_record))::int AS last_year
        FROM weather_observation
    """)
    stats = cur.fetchone()

    cur.execute("""
        SELECT s.station_name, o.max_temp, o.date_of_record
        FROM weather_observation o
        JOIN weather_station s ON s.station_id = o.station_id
        WHERE o.max_temp IS NOT NULL
        ORDER BY o.max_temp DESC
        LIMIT 1
    """)
    hottest = cur.fetchone()

    # Peak max temperature per station, for the 3D map
    cur.execute("""
        SELECT s.station_name, s.latitude, s.longitude, MAX(o.max_temp) AS peak
        FROM weather_station s
        JOIN weather_observation o ON o.station_id = s.station_id
        WHERE o.max_temp IS NOT NULL
        GROUP BY s.station_id
    """)
    stations = [[r["station_name"], float(r["latitude"]), float(r["longitude"]), float(r["peak"])]
                for r in cur.fetchall()]
    conn.close()
    return render_template("index.html", stats=stats, hottest=hottest, stations=stations)

@app.route("/monitoring")
def monitoring():
    station = request.args.get("station", "").strip()
    limit = min(int(request.args.get("limit", 25)), 100)
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    stations = cur.execute("SELECT station_id, station_name, district, state FROM weather_station ORDER BY station_name") or []
    cur.execute("SELECT station_id, station_name, district, state FROM weather_station ORDER BY station_name")
    station_rows = cur.fetchall()

    query = """
        SELECT o.observation_id, o.date_of_record, s.station_name, s.district, s.state,
               o.avg_temp, o.min_temp, o.max_temp, o.wind_speed, o.air_pressure, o.rainfall
        FROM weather_observation o
        JOIN weather_station s ON s.station_id = o.station_id
    """
    params = []
    if station:
        query += " WHERE s.station_id = %s"
        params.append(int(station))
    query += " ORDER BY o.date_of_record DESC LIMIT %s"
    params.append(limit)
    cur.execute(query, params)
    rows = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE max_temp >= 41) AS high,
               COUNT(*) FILTER (WHERE max_temp >= 44) AS extreme,
               ROUND(AVG(max_temp)::numeric, 2) AS avg_max
        FROM weather_observation
    """)
    stats = cur.fetchone()
    conn.close()
    return render_template("monitoring.html", rows=rows, stations=station_rows,
                           selected_station=station, stats=stats)

@app.route("/prediction", methods=["GET", "POST"])
def prediction():
    result = None
    probability = None
    if request.method == "POST":
        values = {}
        for f in FEATURES:
            values[f] = float(request.form.get(f) or 0)
        x = pd.DataFrame([values], columns=FEATURES)

        if MODEL is not None:
            result = MODEL.predict(x)[0]
            probability = max(MODEL.predict_proba(x)[0]) * 100
        else:
            result = heatwave_level(values["max_temp"])
            probability = None

    return render_template("prediction.html", result=result, probability=probability)

@app.route("/warnings")
def warnings():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
    WITH warning_data AS (
        SELECT
            s.station_name,
            s.district,
            s.state,
            o.date_of_record,
            o.max_temp,
            CASE
                WHEN o.max_temp >= 44 THEN 'Extreme'
                WHEN o.max_temp >= 41 THEN 'High'
                WHEN o.max_temp >= 38 THEN 'Moderate'
            END AS risk
        FROM weather_observation o
        JOIN weather_station s ON s.station_id = o.station_id
        WHERE o.max_temp >= 38
    ),
    ranked_warnings AS (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY risk
                ORDER BY max_temp DESC
            ) AS risk_rank
        FROM warning_data
    )
    SELECT station_name, district, state, date_of_record, max_temp, risk
    FROM ranked_warnings
    WHERE risk_rank <= 10
    ORDER BY
        CASE risk
            WHEN 'Extreme' THEN 1
            WHEN 'High' THEN 2
            WHEN 'Moderate' THEN 3
        END,
        max_temp DESC
""")
    rows = cur.fetchall()
    conn.close()
    return render_template("warnings.html", rows=rows)

if __name__ == "__main__":
    train_model()
    app.run(debug=True)
