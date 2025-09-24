from django.contrib import admin
from .models import PollutantReading, AirQualityRecord, WeatherRecord


class WeatherRecordAdmin(admin.ModelAdmin):
    fields = ['city', 'latitude', 'longitude',
              'temperature', 'humidity', 'wind_speed', 'timestamp']
    list_display = ['city', 'latitude', 'longitude',
                    'temperature', 'humidity', 'wind_speed', 'timestamp']


class AirQualityRecordAdmin(admin.ModelAdmin):
    fields = ['city', 'aqi', 'pm25', 'pm10',
              'o3', 'no2', 'so2', 'co', 'timestamp']
    list_display = ['city', 'aqi', 'pm25', 'pm10']


admin.site.register(WeatherRecord, WeatherRecordAdmin)
admin.site.register(AirQualityRecord, AirQualityRecordAdmin)
admin.site.register(PollutantReading)
