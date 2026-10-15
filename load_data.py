import pandas as pd
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")
df = pd.read_csv("weather_dataset_5000.csv")

month_map = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

station_ids = {}
for _, r in df.drop_duplicates(["station_name","district","state"]).iterrows():
    cur.execute("""
        INSERT INTO weather_station
        (station_name, state, district, elevation, latitude, longitude)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (station_name, district, state)
        DO UPDATE SET station_name=EXCLUDED.station_name
        RETURNING station_id
    """, (
        r["station_name"], r["state"], r["district"],
        r["elevation"], r["latitude"], r["longitude"]
    ))
    station_ids[(r["station_name"], r["district"], r["state"])] = cur.fetchone()[0]

for _, r in df.iterrows():
    sid = station_ids[(r["station_name"], r["district"], r["state"])]
    vals = [
        sid, r["date_of_record"], month_map[str(r["month"]).strip()], r["season"],
        r["avg_temp"], r["min_temp"], r["max_temp"],
        r["wind_speed"], r["air_pressure"], r["rainfall"]
    ]
    vals = [None if pd.isna(v) else v for v in vals]
    cur.execute("""
        INSERT INTO weather_observation
        (station_id,date_of_record,month,season,avg_temp,min_temp,max_temp,
         wind_speed,air_pressure,rainfall)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, vals)

conn.commit()
cur.close()
conn.close()
print("Loaded", len(df), "weather observations.")
