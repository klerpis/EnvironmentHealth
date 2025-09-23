from .views import PollutantReadingViewSet
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views


router = DefaultRouter()
router.register(r'pollutants', PollutantReadingViewSet, basename='pollutants')

urlpatterns = [
    path('', include(router.urls)),
    path('weather/', views.weather_forecast, name='weather'),
    path('air-quality/', views.air_quality, name='air_quality'),
    path("history/weather/", views.weather_history, name="weather_history"),
    path("history/air-quality/", views.air_quality_history,
         name="air_quality_history"),
    # Minor Metrics
    path("uv-index/", views.uv_index, name="uv_index"),
    path("soil-moisture/", views.soil_moisture, name="soil_moisture"),
    path("water-quality/", views.water_quality, name="water_quality"),
    path("noise-level/", views.noise_level, name="noise_level"),
]
