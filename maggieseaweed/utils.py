import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry
import numpy as np
import requests
import arrow

# import geopandas as gpd
# from shapely.wkt import loads
# from shapely.geometry import shape, Polygon


# import pyarrow.parquet as pq
# import geopandas as gpd
# from shapely.wkt import loads
# from shapely.geometry import shape, Polygon
# import geopandas as gpd
# from shapely.ops import nearest_points
# from shapely.geometry import Point, MultiLineString


OCEANS_FP = "/Users/mschultz3/Documents/projects/temporary/sandbox_exposure/untracked/data/ocean_land_boundaries.parquet"


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
            "cloud_cover"
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": forecast_days,
    }
    responses = openmeteo.weather_api(url, params=params)

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
    hourly_data["cloud_cover"] = hourly.Variables(5).ValuesAsNumpy()

    hourly_dataframe = pd.DataFrame(data=hourly_data)
    return hourly_dataframe


def surfability_score_old(row):
    temperature_score = row["temperature_2m"]  # Higher temperature is better
    wind_speed_score = 1 / (1 + row["wind_speed_10m"])  # Lower wind speed is better
    daytime_score = row["is_day"]  # Must be day time

    total_score = (0.4 * temperature_score + 0.4 * wind_speed_score) * daytime_score

    return total_score

def format_time(timestamp):
    time_str = timestamp.strftime("%I:%M %p")
    if time_str.startswith('0'):
        time_str = time_str[1:]
    return time_str

def surfability_score(row):
    temperature_score = row["waterTemperature"]  # Higher temperature is better
    wave_height_score = row["waveHeight"]  # Lower wave height is better for beginners
    wave_period_score = row["wavePeriod"]  # Longer wave period is generally better
    wave_direction_score = row["waveDirection"]  # Favorable wave direction is better
    wind_speed_score = 1 / (1 + row["wind_speed_10m"])  # Lower wind speed is better
    daytime_score = row["is_day"]  # Must be daytime

    temperature_weight = 0.2
    wave_height_weight = 0.2
    wave_period_weight = 0.2
    wave_direction_weight = 0.2
    wind_speed_weight = 0.2

    total_score = (
        temperature_weight * temperature_score +
        wave_height_weight * wave_height_score +
        wave_period_weight * wave_period_score +
        wave_direction_weight * wave_direction_score +
        wind_speed_weight * wind_speed_score
    ) * daytime_score

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
    url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + place + ".json"
    params = {
        "access_token": "pk.eyJ1IjoibWFnZ2llY3NjaHVsdHoiLCJhIjoiY2x0ZGRiZWpwMDNjbTJsc2R5eHQ4YnMzYiJ9.ALy4ULirb8PPUAFyY-f4uw"
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print("Error fetching location data:", response.status_code)
        return None


def celsius_to_fahrenheit(celsius):
    fahrenheit = celsius * 9/5 + 32
    return fahrenheit


def fetch_wave_data(latitude, longitude, forecast_days):
    start = arrow.now().floor('day')
    end = arrow.now().shift(days=forecast_days).ceil('day')

    features = ["waveHeight", "waveDirection", "wavePeriod", "waterTemperature"]

    response = requests.get(
        "https://api.stormglass.io/v2/weather/point",
        params={
            "lat": latitude,
            "lng": longitude,
            "start": start.to("UTC").timestamp(),
            "end": end.to("UTC").timestamp(),
            "params": ",".join(features),
            "source": "sg",
        },
        headers={
            "Authorization": "ff70e62c-fb22-11ee-bd8e-0242ac130002-ff70e6d6-fb22-11ee-bd8e-0242ac130002"
        },
    )

    json_data = response.json()

    wave_df = pd.DataFrame(data=json_data["hours"])


    for column in features:
        wave_df[column] = wave_df[column].apply(
            lambda d: d.get("sg") if isinstance(d, dict) else None
        )

    wave_df['waterTemperature'] = wave_df['waterTemperature'].apply(celsius_to_fahrenheit)

    return wave_df




def join_feature_df(weather, wave):

    wave["time_utc"] = pd.to_datetime(wave["time"])
    weather["time_utc"] = pd.to_datetime(weather["timestamp"])
    weather["time_utc"] = weather["time_utc"].dt.tz_convert("UTC")
    merged_df = pd.merge(wave, weather, on="time_utc", how="inner")

    merged_df = merged_df.drop(columns=["time", "time_utc"])

    return merged_df

def get_closest_beach(lat, lon, data_path = OCEANS_FP):
    input_point = Point(lat, lon)
    ocean_boundaries = pq.read_table(data_path).to_pandas()
    ocean_boundaries['geojson'] = (
        ocean_boundaries['geojson']
        .apply(lambda x: shape(eval(x)))
    )
    ocean_boundaries = gpd.GeoDataFrame(ocean_boundaries, geometry='geojson', crs="EPSG:4326")

    ocean_boundaries['distance'] = ocean_boundaries.geometry.distance(input_point)
    closest_multiline = ocean_boundaries.loc[ocean_boundaries['distance'].idxmin()]
    boundary = closest_multiline.geojson
    closest_point_on_boundary = boundary.interpolate(boundary.project(input_point))
    return closest_point_on_boundary
