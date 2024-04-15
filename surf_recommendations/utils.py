import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry
import numpy as np
import requests


def fetch_open_meteo_data(latitude, longitude, forecast_days):
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": [
            "temperature_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "uv_index",
            "is_day",
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": forecast_days,
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]

    hourly = response.Hourly()
    # local_timezone = response.TimezoneAbbreviation()
    timezone_difference = response.UtcOffsetSeconds()

    hourly_data = {
        "timestamp": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True)
            + pd.Timedelta(seconds=timezone_difference),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True)
            + pd.Timedelta(seconds=timezone_difference),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }
    hourly_data["temperature_2m"] = hourly.Variables(0).ValuesAsNumpy()
    hourly_data["wind_speed_10m"] = hourly.Variables(1).ValuesAsNumpy()
    hourly_data["wind_direction_10m"] = hourly.Variables(2).ValuesAsNumpy()
    hourly_data["uv_index"] = hourly.Variables(3).ValuesAsNumpy()
    hourly_data["is_day"] = hourly.Variables(4).ValuesAsNumpy()

    hourly_dataframe = pd.DataFrame(data=hourly_data)
    return hourly_dataframe


def surfability_score(row):
    temperature_score = row["temperature_2m"]  # Higher temperature is better
    wind_speed_score = 1 / (1 + row["wind_speed_10m"])  # Lower wind speed is better
    daytime_score = row["is_day"]  # Must be day time

    total_score = (0.4 * temperature_score + 0.4 * wind_speed_score) * daytime_score

    return total_score


def degrees_to_cardinal(direction_in_degrees):
    cardinal_directions = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    index = round(direction_in_degrees / 22.5) % 16
    return cardinal_directions[index]


def fetch_location_data(place):
    url = 'https://api.mapbox.com/geocoding/v5/mapbox.places/' + place + '.json'
    params = {
        'access_token': 'pk.eyJ1IjoibWFnZ2llY3NjaHVsdHoiLCJhIjoiY2x0ZGRiZWpwMDNjbTJsc2R5eHQ4YnMzYiJ9.ALy4ULirb8PPUAFyY-f4uw'
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print('Error fetching location data:', response.status_code)
        return None
