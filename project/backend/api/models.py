# api/models.py
from django.db import models
from django.utils import timezone


class WeatherRecord(models.Model):
    city = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    wind_speed = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    # def __str__(self):
    #     return f'city'


class AirQualityRecord(models.Model):
    city = models.CharField(max_length=100)
    aqi = models.IntegerField(null=True, blank=True)
    pm25 = models.FloatField(null=True, blank=True)
    pm10 = models.FloatField(null=True, blank=True)
    o3 = models.FloatField(null=True, blank=True)
    no2 = models.FloatField(null=True, blank=True)
    so2 = models.FloatField(null=True, blank=True)
    co = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class PollutantReading(models.Model):
    name = models.CharField(max_length=50)  # e.g. PM2.5
    value = models.FloatField()
    unit = models.CharField(max_length=20)  # µg/m³, ppm, ppb
    status = models.CharField(max_length=20, default="Good")
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - {self.value} {self.unit}"
