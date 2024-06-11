# maggieseaweed/urls.py
from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin


app_name = "maggieseaweed"

urlpatterns = [
    path('admin/', admin.site.urls),
    path("home/", views.home, name="home"),
    path("", views.home, name="home"),
    path("testing", views.testing, name="testing"),
    path("results", views.display_forecast, name="forecast"),
    path(
        "results/<str:place_name>/<str:latitude>/<str:longitude>/<int:forecast_days>/",
        views.display_forecast,
        name="forecast",
    ),
]
