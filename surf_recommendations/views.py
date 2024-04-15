# surf_recommendations/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import WeatherData
from .utils import (
    fetch_open_meteo_data,
    surfability_score,
    degrees_to_cardinal,
    fetch_location_data,
)

from django.http import JsonResponse
from django.utils import timezone


def fetch_and_save_weather_data_api(request, latitude, longitude, forecast_days):
    latitude = float(latitude)
    longitude = float(longitude)
    forecast_days = int(forecast_days)
    preferred_time = request.POST.get("preferredTime", "anytime")
    print(preferred_time)

    raw_data = fetch_open_meteo_data(latitude, longitude, forecast_days)

    if preferred_time == "morning":
        data = raw_data[raw_data["timestamp"].dt.hour < 10]
    elif preferred_time == "afternoon":
        data = raw_data[
            (raw_data["timestamp"].dt.hour >= 10) & (raw_data["timestamp"].dt.hour < 17)
        ]
    elif preferred_time == "evening":
        data = raw_data[raw_data["timestamp"].dt.hour >= 17]
    else:
        data = raw_data  # No filtering, consider all times

    data["surfability_score"] = data.apply(surfability_score, axis=1)

    best_time_to_surf = data.loc[data["surfability_score"].idxmax()]

    timestamp = best_time_to_surf.get("timestamp")

    formatted_timestamp = timestamp.strftime(
        "%B %d, %Y %I:%M %p"
    )  # Changed strftime format

    wind_direction_degrees = best_time_to_surf.get("wind_direction_10m")
    wind_direction_cardinal = degrees_to_cardinal(wind_direction_degrees)

    response_data = {
        "timestamp": str(formatted_timestamp),
        "temperature_2m": str(round(best_time_to_surf.get("temperature_2m"))),
        "wind_direction_10m": wind_direction_cardinal,
        "wind_speed_10m": str(round(best_time_to_surf.get("wind_speed_10m"))),
        "uv_index": str(round(best_time_to_surf.get("uv_index"))),
        "is_day": str(best_time_to_surf.get("is_day")),
    }

    return JsonResponse(response_data)


def home(request):
    return render(request, "surf_recommendations/home.html")


def get_input(request):
    return render(request, "surf_recommendations/try_bootstrap.html")


# def forecast(request):
#     return render(request, "surf_recommendations/bootstrap_forecast.html")


def display_forecast(request, place_name, latitude, longitude, forecast_days):
    latitude = float(latitude)
    longitude = float(longitude)
    location_name = str(place_name)

    forecast_days = int(forecast_days)
    preferred_time = request.POST.get("preferredTime", "anytime")

    raw_data = fetch_open_meteo_data(latitude, longitude, forecast_days)

    if preferred_time == "morning":
        data = raw_data[raw_data["timestamp"].dt.hour < 10]
    elif preferred_time == "afternoon":
        data = raw_data[
            (raw_data["timestamp"].dt.hour >= 10) & (raw_data["timestamp"].dt.hour < 17)
        ]
    elif preferred_time == "evening":
        data = raw_data[raw_data["timestamp"].dt.hour >= 17]
    else:
        data = raw_data  # No filtering, consider all times

    data["surfability_score"] = data.apply(surfability_score, axis=1)

    best_time_to_surf = data.loc[data["surfability_score"].idxmax()]

    timestamp = best_time_to_surf.get("timestamp")

    formatted_timestamp = timestamp.strftime(
        "%B %d, %Y %I:%M %p"
    )  # Changed strftime format

    wind_direction_degrees = best_time_to_surf.get("wind_direction_10m")
    wind_direction_cardinal = degrees_to_cardinal(wind_direction_degrees)
    around_best_time = data.loc[
        data["surfability_score"].idxmax() - 2 : data["surfability_score"].idxmax() + 2
    ]
    around_best_time["temperature_2m"] = round(around_best_time["temperature_2m"], 0).astype(int)
    around_best_time["hour"] = around_best_time["timestamp"].dt.strftime("%I:%M")
    around_best_time["am_pm"] = around_best_time["timestamp"].dt.strftime("%p")
    around_best_time["best"] = around_best_time.index.to_series().apply(lambda idx: 1 if idx == data["surfability_score"].idxmax() else 0)


    response_data = {
        "timestamp": str(formatted_timestamp),
        "date": str(timestamp.strftime("%B %d, %Y")),
        "time": str(timestamp.strftime("%I:%M %p")),
        "temperature_2m": str(round(best_time_to_surf.get("temperature_2m"))),
        "wind_direction_10m": wind_direction_cardinal,
        "wind_speed_10m": str(round(best_time_to_surf.get("wind_speed_10m"))),
        "uv_index": str(round(best_time_to_surf.get("uv_index"))),
        "is_day": str(best_time_to_surf.get("is_day")),
        "surfability_score": str(round(best_time_to_surf.get("surfability_score"))),
        "latitude": latitude,
        "longitude": longitude,
        "location_name": location_name,
        "around_best_time": around_best_time.to_dict("records"),
    }

    return render(
        request, "surf_recommendations/bootstrap_forecast.html", response_data
    )
