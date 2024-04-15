# surf_recommendations/urls.py
from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings


app_name = "surf_recommendations"

urlpatterns = [
    path(
        "fetch_and_save_weather_data_api/<str:latitude>/<str:longitude>/<int:forecast_days>/",
        views.fetch_and_save_weather_data_api,
        name="fetch_and_save_weather_data_api",
    ),
    path("home/", views.home, name="home"),
    path("", views.home, name="home"),
    path("inputs", views.get_input, name="inputs"),
    path("results", views.display_forecast, name="forecast"),
    path(
        "results/<str:place_name>/<str:latitude>/<str:longitude>/<int:forecast_days>/",
        views.display_forecast,
        name="forecast",
    ),
]
