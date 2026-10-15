-- CREATE DATABASE climate_intelligence;

-- Connect to climate_intelligence before running the remaining statements.

CREATE TABLE IF NOT EXISTS weather_station (
    station_id SERIAL PRIMARY KEY,
    station_name VARCHAR(150) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    elevation NUMERIC(8,2),
    latitude NUMERIC(9,5),
    longitude NUMERIC(9,5),
    UNIQUE(station_name, district, state)
);

CREATE TABLE IF NOT EXISTS weather_observation (
    observation_id SERIAL PRIMARY KEY,
    station_id INT NOT NULL REFERENCES weather_station(station_id),
    date_of_record DATE NOT NULL,
    month INT NOT NULL,
    season VARCHAR(30),
    avg_temp NUMERIC(6,2),
    min_temp NUMERIC(6,2),
    max_temp NUMERIC(6,2),
    wind_speed NUMERIC(7,2),
    air_pressure NUMERIC(8,2),
    rainfall NUMERIC(8,2)
);

CREATE TABLE IF NOT EXISTS heatwave_prediction (
    prediction_id SERIAL PRIMARY KEY,
    station_id INT REFERENCES weather_station(station_id),
    prediction_date DATE NOT NULL,
    predicted_max_temp NUMERIC(6,2),
    risk_level VARCHAR(20) NOT NULL,
    model_confidence NUMERIC(5,2)
);

CREATE TABLE IF NOT EXISTS early_warning (
    warning_id SERIAL PRIMARY KEY,
    prediction_id INT REFERENCES heatwave_prediction(prediction_id),
    warning_level VARCHAR(20) NOT NULL,
    advisory TEXT NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_observation_station_date
ON weather_observation(station_id, date_of_record);

CREATE INDEX IF NOT EXISTS idx_observation_max_temp
ON weather_observation(max_temp);
