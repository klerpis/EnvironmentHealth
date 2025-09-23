from .models import PollutantReading
from rest_framework import serializers
from .models import WeatherRecord, AirQualityRecord


class WeatherRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherRecord
        fields = "__all__"


class AirQualityRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirQualityRecord
        fields = "__all__"


class PollutantReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollutantReading
        fields = "__all__"
