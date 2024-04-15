from django.db import models


class WeatherData(models.Model):
    timestamp = models.DateTimeField()
    temperature_2m = models.FloatField()
    wind_speed_10m = models.FloatField()
    wind_direction_10m = models.FloatField()
    uv_index = models.FloatField()
    is_day = models.BooleanField()

    def __str__(self):
        return f"{self.timestamp} - Temperature: {self.temperature_2m}, Wind Speed: {self.wind_speed_10m}"
