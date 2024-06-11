# surf_recommendations/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from .utils import (
    fetch_open_meteo_data,
    fetch_wave_data,
    join_feature_df,
    surfability_score,
    degrees_to_cardinal,
    fetch_location_data,
    get_closest_beach,
    format_time,
    get_closest_surf_spot,
)

from django.http import JsonResponse
from django.utils import timezone

import pandas as pd
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse
import pandas as pd
import pandas as pd
from django.utils.dateparse import parse_datetime


def home(request):
    return render(request, "maggieseaweed/home.html")

def testing(request):
    return render(request, "maggieseaweed/search_bar.html")

def display_forecast(request, place_name, latitude, longitude, forecast_days):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        forecast_days = int(forecast_days)
    except ValueError:
        return HttpResponse("Invalid latitude, longitude, or forecast days", status=400)

    preferred_time = request.POST.get("preferredTime", "anytime")


    try:
        surf_spot_data = get_closest_surf_spot(latitude, longitude)
        lat, lon = surf_spot_data.get('latitude'), surf_spot_data.get('longitude')
        weather_data = fetch_open_meteo_data(lat, lon, forecast_days)
        wave_data = fetch_wave_data(lat, lon, forecast_days)
        raw_data = join_feature_df(weather_data, wave_data)
    except Exception as e:
        return HttpResponse(f"Error fetching data: {e}", status=500)

    raw_data['timestamp'] = pd.to_datetime(raw_data['timestamp'])
    data = filter_data_by_time(raw_data, preferred_time)
    data = calculate_surfability_scores(data)

    best_time_to_surf = data.loc[data['surfability_score'].idxmax()]
    # response_data = prepare_response_data(best_time_to_surf, data, place_name, surf_spot_data)
    response_data = load_response_data_from_json('response_data.json')

    #save_response_data_to_json(response_data, 'response_data.json')



    return render(request, "maggieseaweed/forecast.html", response_data)

def filter_data_by_time(data, preferred_time):
    if preferred_time == "morning":
        return data[data['timestamp'].dt.hour < 10]
    elif preferred_time == "afternoon":
        return data[(data['timestamp'].dt.hour >= 10) & (data['timestamp'].dt.hour < 17)]
    elif preferred_time == "evening":
        return data[data['timestamp'].dt.hour >= 17]
    return data

def calculate_surfability_scores(data):
    data['surfability_score'] = data.apply(surfability_score, axis=1)
    data['surfability_score'] = round(data['surfability_score']).astype(int)
    return data


def prepare_chart_data(data):
    chart_data = []
    for index, entry in data.iterrows():
        # Convert the timestamp to a JavaScript-friendly format (e.g., milliseconds since epoch)
        # Ensure that 'timestamp' is a datetime object
        if pd.notnull(entry['timestamp']) and hasattr(entry['timestamp'], 'isoformat'):
            timestamp = parse_datetime(entry['timestamp'].isoformat())
            if timestamp:
                timestamp_js = int(timestamp.timestamp() * 1000)  # convert to milliseconds
                # Include additional data points for tooltips
                chart_data.append({
                    'x': timestamp_js,
                    'y': entry['surfability_score'],
                    'water_temperature': round(entry['waterTemperature'],0),
                    'wave_height': round(entry['waveHeight'],0),
                    'air_temperature': round(entry['temperature_2m'],0),
                    'wind_direction_10m': degrees_to_cardinal(entry['wind_direction_10m']),
                    "wind_speed_10m": round(entry['wind_speed_10m'],0),
                    'uv_index': round(entry['uv_index'],0),
                    'cloud_cover': entry['cloud_cover']
                })
    return chart_data

def prepare_response_data(best_time_to_surf, data, input_name, beach_data):
    timestamp = best_time_to_surf['timestamp']
    return {
        "timestamp": timestamp.strftime("%B %d, %Y %I:%M %p"),
        "date": timestamp.strftime("%B %d, %Y"),
        "time": format_time(timestamp),
        "water_temperature": round(best_time_to_surf.get("waterTemperature")),
        "wave_height": round(best_time_to_surf.get("waveHeight")),
        "air_temperature": round(best_time_to_surf.get("temperature_2m")),
        "wind_direction_10m": degrees_to_cardinal(best_time_to_surf.get("wind_direction_10m")),
        "wind_speed_10m": round(best_time_to_surf.get("wind_speed_10m")),
        "uv_index": round(best_time_to_surf.get("uv_index")),
        "is_day": str(best_time_to_surf.get("is_day")),
        "surfability_score": str(best_time_to_surf.get("surfability_score")),
        "cloud_cover": round(best_time_to_surf.get("cloud_cover")),
        "water_temp": best_time_to_surf.get("waterTemperature"),
        "latitude": beach_data.get("latitude"),
        "longitude": beach_data.get("longitude"),
        "wave_direction": beach_data.get("wave_direction"),
        "wave_type": beach_data.get("wave_type"),
        "crowd_level": beach_data.get("crowd_level"),
        "location_name": beach_data.get("spot"),
        "input_location_name": input_name,
        "distance_to_input": beach_data.get("distance"),
        "chart_data_json": json.dumps(prepare_chart_data(data))
    }

def load_response_data_from_json(file_path):
    with open(file_path, 'r') as json_file:
        response_data = json.load(json_file)
    return response_data

def save_response_data_to_json(response_data, file_path):
    with open(file_path, 'w') as json_file:
        json.dump(response_data, json_file, indent=4)
