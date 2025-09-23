from django.db.models import OuterRef, Subquery
from django.db.models import Q
from datetime import timedelta
from django.db.models import Avg
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework import viewsets
from .serializers import PollutantReadingSerializer
from .models import PollutantReading
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import WeatherRecord, AirQualityRecord
from .serializers import WeatherRecordSerializer, AirQualityRecordSerializer
from pprint import pprint
import requests
import random
from django.utils.dateparse import parse_datetime
from django.db import transaction

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
OPENAQ_BASE = "https://api.openaq.org/v3"


OPENAQ_API_KEY = "4bbcab70125f1879374ebb6caec02bb5018ab0ddf16f9bf4dc7cdabe0f6fda2f"


def cached_request(cache_key, url, timeout=900, headers=None):
    # Try to fetch from cache
    print('a')
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    print('b')

    # Inject OpenAQ header if needed
    req_headers = headers or {}
    if "api.openaq.org/v3" in url:
        req_headers["X-API-Key"] = OPENAQ_API_KEY
    print('c')

    try:
        response = requests.get(url, headers=req_headers, timeout=10)
        print('d', response)
        response.raise_for_status()
        print('e')
        data = response.json()
        print('f')

        # Cache result
        cache.set(cache_key, data, timeout)
        return data
    except Exception as e:
        print(f"cached_request error for {url}: {e}")
        return None


# def cached_request(cache_key, url, timeout=300):
#     try:
#         print(100)
#         # Try cache
#         data = cache.get(cache_key)
#         if data:
#             return data
#         print(200, data)

#         # Fetch API
#         r = requests.get(url, timeout=10)
#         print(300, r)
#         r.raise_for_status()
#         print(400)
#         data = r.json()
#         print(500)

#         # Save cache
#         cache.set(cache_key, data, timeout=timeout)
#         print(600)
#         return data
#     except Exception:
#         # fallback to cache if available
#         return cache.get(cache_key, {"error": "API unavailable and no cache"})


@api_view(['GET'])
def weather_forecast(request):
    lat = request.GET.get("lat", "6.5244")
    lon = request.GET.get("lon", "3.3792")
    city = request.GET.get("city", "lagos")

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    cache_key = f"weather_{lat}_{lon}"

    raw = cached_request(cache_key, url, timeout=600)
    print("raw", raw)

    # Shape data
    if "hourly" in raw:
        shaped = {
            "city": city,
            "latitude": lat,
            "longitude": lon,
            "temperature": raw["hourly"]["temperature_2m"][:24],  # next 24h
            "humidity": raw["hourly"]["relative_humidity_2m"][:24],
            "wind_speed": raw["hourly"]["wind_speed_10m"][:24],
            "timestamps": raw["hourly"]["time"][:24]
        }

        # Save snapshot
        WeatherRecord.objects.create(
            city=city,
            latitude=lat,
            longitude=lon,
            temperature=shaped["temperature"][0],
            humidity=shaped["humidity"][0],
            wind_speed=shaped["wind_speed"][0],
        )
    else:
        shaped = {"error": "No data"}

    return Response(shaped)


@api_view(["GET"])
def air_quality(request):
    city = request.GET.get("city", "Lagos")
    # Step 1: find a location_id for that city via /locations?city=...

    # url = f"https://api.openaq.org/v3/measurements?city={city}&limit=100"
    print(1000)
    cache_key = f"air_quality_{city}"
    url = f"https://api.openaq.org/v3/locations?city={city}&limit=1"
    loc_raw = cached_request(cache_key, url, timeout=900)
    if not loc_raw or not loc_raw.get("results"):
        data_instance = AirQualityRecord.objects.first()
        try:
            from django.forms.models import model_to_dict
            aq_dict = model_to_dict(data_instance)

        except:
            aq_dict = {}
            return Response({"error": "No air quality data"}, status=500)

        # pollutants[param] = 2 not needed here
        aq_dict['city']
        shaped_list.append({
            "name": param,
            "value": 2,
            "unit": unit,
            "timestamp": ts,
            "location": m.get("locationId"),
        })
        {
            "city": city,
            "pollutants": shaped_list,
        }
        # handle missing
    location = loc_raw["results"][0]
    location_id = location["id"]

    latest_url = f"https://api.openaq.org/v3/locations/{location_id}"

    raw = cached_request(cache_key, latest_url, timeout=900)
    print(2000, 'am i in the right')
    # pprint(raw)

    if not raw or "results" not in raw or not raw["results"]:
        return Response({"error": "No air quality data"}, status=500)
    print(3000)

    # Collect pollutants (normalize to lowercase)
    pollutants = {}
    shaped_list = []

    for res in raw["results"]:
        for m in res['sensors']:
            # sensor_id = m['id']
            # sensor_name = m['name']
            # param_id = m['parameter']['id']
            # thepollutant = m['parameter']['displayname']
            unit = m['parameter']['units']
            param = m['parameter']['name']  # "pm25", "pm10"

            # param = m["parameter"].lower()   # "pm25", "pm10"
            # value = m.get("value")
            # unit = m.get("unit")
            ts = parse_datetime(res["datetimeLast"]["utc"]
                                ) if "date" in m else None

            pollutants[param] = 2
            shaped_list.append({
                "name": param,
                "value": 2,
                "unit": unit,
                "timestamp": ts,
                "location": m.get("locationId"),
            })

        if ts:
            PollutantReading.objects.update_or_create(
                name=param,
                timestamp=ts,
                defaults={
                    "value": 2,
                    "unit": unit,
                    "location": m.get("locationId"),
                },
            )

    # Save city-level snapshot (use None for missing)
    print(4000)

    AirQualityRecord.objects.create(
        city=city,
        pm25=pollutants.get("pm25"),
        pm10=pollutants.get("pm10"),
        o3=pollutants.get("o3"),
        no2=pollutants.get("no2"),
        so2=pollutants.get("so2"),
        co=pollutants.get("co"),
    )
    print(5000)

    return Response({
        "city": city,
        "pollutants": shaped_list,
    })

# @api_view(['GET'])
# def air_quality(request):
#     city = request.GET.get("city", "Lagos")
#     # url = f"https://api.openaq.org/v3/latest?city={city}"
#     url = f"https://api.openaq.org/v3/locations?city={city}"

#     cache_key = f"air_quality_{city.lower()}"

#     raw = cached_request(cache_key, url, timeout=900)

#     # Shape data
#     print()
#     print()
#     print()
#     print('RAAAA', raw)
#     print()
#     print()
#     print()
#     print()
#     shaped = {"city": city, "measurements": {}}
#     if "results" in raw and raw["results"]:
#         measurements = raw["results"][0].get("measurements", [])
#         for m in measurements:
#             shaped["measurements"][m["parameter"]] = m["value"]

    #     # Save snapshot
    #     AirQualityRecord.objects.create(
    #         city=city,
    #         pm25=shaped["measurements"].get("pm25"),
    #         pm10=shaped["measurements"].get("pm10"),
    #         o3=shaped["measurements"].get("o3"),
    #         no2=shaped["measurements"].get("no2"),
    #         so2=shaped["measurements"].get("so2"),
    #         co=shaped["measurements"].get("co"),
    #     )
    # else:
    #     shaped["error"] = "No data"

    # return Response(shaped)


@api_view(['GET'])
def weather_history(request):
    city = request.GET.get("city", "Lagos")
    limit = int(request.GET.get("limit", 24))  # default last 24 entries

    records = WeatherRecord.objects.filter(
        city__iexact=city).order_by("-timestamp")[:limit]
    serializer = WeatherRecordSerializer(records, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def air_quality_history(request):
    city = request.GET.get("city", "Lagos")
    limit = int(request.GET.get("limit", 24))  # default last 24 entries

    records = AirQualityRecord.objects.filter(
        city__iexact=city).order_by("-timestamp")[:limit]
    serializer = AirQualityRecordSerializer(records, many=True)
    return Response(serializer.data)


class PollutantReadingViewSet(viewsets.ModelViewSet):
    queryset = PollutantReading.objects.all().order_by('-timestamp')
    serializer_class = PollutantReadingSerializer

    serializer_class = PollutantReadingSerializer
    queryset = PollutantReading.objects.all()

    @action(detail=False, methods=['get'])
    def latest(self, request):
        city = request.GET.get("city", "Lagos")
        # url = f"https://api.openaq.org/v3/latest?city={city}"
        url = f"https://api.openaq.org/v3/locations?city={city}&limit=100"
        # https://api.openaq.org/v3/locations?city={city_name}
        cache_key = f"air_quality_latest_{city}"

        print(1)
        # Fetch data (with cache wrapper)
        raw = cached_request(cache_key, url, timeout=900)
        print(2)
        if not raw or "results" not in raw:
            return Response({"error": "No data from OpenAQ"}, status=500)

        print(3)
        measurements = []
        with transaction.atomic():
            for loc in raw["results"]:
                location = loc.get("location")
                for m in loc.get("latest", []):
                    reading = {
                        "name": m.parameter,  # e.g., pm25, no2
                        "value": m.value,
                        "unit": m.unit,
                        "location": location,
                        # or parse m["lastUpdated"]
                        "timestamp": m.lastUpdated,
                    }

                    # Save into DB
                    obj, _ = PollutantReading.objects.update_or_create(
                        name=reading["name"],
                        timestamp=reading["timestamp"],
                        defaults=reading,
                    )
                    measurements.append(obj)
        print(4)

        # Serialize and return
        serializer = self.get_serializer(measurements, many=True)
        return Response(serializer.data)

    # latest readings for dashboard
    # @action(detail=False, methods=['get'])
    # # def latest(self, request):
    # #     latest_qs = PollutantReading.objects.filter(
    # #         name=OuterRef("name")).order_by("-timestamp")
    # #     latest_readings = (
    # #         PollutantReading.objects
    # #         .filter(pk=Subquery(latest_qs.values("pk")[:1]))
    # #     )
    # #     serializer = self.get_serializer(latest_readings, many=True)
    # #     return Response(serializer.data)
    # # # history by pollutant name

    @action(detail=False, methods=['get'])
    def history(self, request):
        # name = request.query_params.get('name')
        # days = int(request.query_params.get('days', 7))
        # since = timezone.now() - timedelta(days=days)

        city = request.GET.get("city", "Lagos")
        parameter = request.GET.get("parameter", "pm25")
        date_from = request.GET.get("date_from")  # optional
        date_to = request.GET.get("date_to")      # optional

        url = f"https://api.openaq.org/v3/measurements?city={city}&parameter={parameter}&limit=100"

        if date_from:
            url += f"&date_from={date_from}"
        if date_to:
            url += f"&date_to={date_to}"

        cache_key = f"air_quality_history_{city}_{parameter}"
        raw = cached_request(cache_key, url, timeout=900)

        if not raw or "results" not in raw:
            return Response({"error": "No history data"}, status=500)

        records = []
        for m in raw["results"]:
            records.append({
                "name": m["parameter"],
                "value": m["value"],
                "unit": m["unit"],
                "timestamp": m["date"]["utc"],
                "location": m.get("locationId"),
            })
            # optional: save to DB just like in latest()
            records = []
            with transaction.atomic():
                for m in raw["results"]:
                    # convert string → datetime
                    ts = parse_datetime(m["date"]["utc"])

                    reading_data = {
                        "name": m["parameter"],
                        "value": m["value"],
                        "unit": m["unit"],
                        "location": m.get("locationId"),
                        "timestamp": ts,
                    }

                    obj, _ = PollutantReading.objects.update_or_create(
                        name=reading_data["name"],
                        timestamp=reading_data["timestamp"],
                        defaults=reading_data,
                    )
                    records.append(obj)
        return Response(records)
    # daily average (optional)

    @action(detail=False, methods=['get'])
    def daily_avg(self, request):
        name = request.query_params.get('name')
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)

        qs = (
            PollutantReading.objects
            .filter(name=name, timestamp__gte=since)
            .extra({'day': "date(timestamp)"})
            .values('day')
            .annotate(avg_value=Avg('value'))
            .order_by('day')
        )
        return Response(qs)

    @action(detail=False, methods=['get'])
    def multi_history(self, request):
        city = request.GET.get("city", "Lagos")
        parameters = request.GET.get("parameters", "pm25,no2").split(",")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        combined = {}

        for parameter in parameters:
            url = f"https://api.openaq.org/v3/measurements?city={city}&parameter={parameter}&limit=100"
            if date_from:
                url += f"&date_from={date_from}"
            if date_to:
                url += f"&date_to={date_to}"

            cache_key = f"multi_history_{city}_{parameter}_{date_from}_{date_to}"
            raw = cached_request(cache_key, url, timeout=900)

            if not raw or "results" not in raw:
                continue

            with transaction.atomic():
                for m in raw["results"]:
                    ts = parse_datetime(m["date"]["utc"])
                    ts_key = ts.isoformat()

                    # Ensure timestamp bucket exists
                    if ts_key not in combined:
                        combined[ts_key] = {"timestamp": ts}

                    # Add pollutant value
                    combined[ts_key][parameter] = m["value"]

                    # Save to DB
                    PollutantReading.objects.update_or_create(
                        name=parameter,
                        timestamp=ts,
                        defaults={
                            "name": parameter,
                            "value": m["value"],
                            "unit": m["unit"],
                            "location": m.get("locationId"),
                            "timestamp": ts,
                        },
                    )

        # Convert dict → sorted list
        data = sorted(combined.values(), key=lambda x: x["timestamp"])
        return Response(data)

    # @action(detail=False, methods=['get'])
    # def multi_history(self, request):
    #     names = request.query_params.getlist(
    #         'names')  # e.g. ?names=PM2.5&names=NO2
    #     days = int(request.query_params.get('days', 7))
    #     since = timezone.now() - timedelta(days=days)

    #     qs = (
    #         PollutantReading.objects
    #         .filter(name__in=names, timestamp__gte=since)
    #         .order_by('timestamp')
    #     )

    #     serializer = self.get_serializer(qs, many=True)
    #     return Response(serializer.data)


# ✅ UV Index (Open-Meteo supports uv_index)
@api_view(["GET"])
def uv_index(request):
    lat = request.GET.get("lat", "6.5244")   # Lagos default
    lon = request.GET.get("lon", "3.3792")

    url = (
        f"{OPEN_METEO_BASE}?latitude={lat}&longitude={lon}&hourly=uv_index"
    )
    cache_key = f"uv_index_{lat}_{lon}"
    raw = cached_request(cache_key, url, timeout=900)

    if not raw or "hourly" not in raw:
        return Response({"error": "UV data unavailable"}, status=500)

    uv_values = raw["hourly"].get("uv_index", [])
    timestamps = raw["hourly"].get("time", [])
    latest = uv_values[-1] if uv_values else None
    ts = timestamps[-1] if timestamps else timezone.now()

    return Response({
        "uv_index": latest,
        "timestamp": ts,
    })


# ✅ Soil Moisture (Open-Meteo supports soil_moisture_0_7cm, etc.)
@api_view(["GET"])
def soil_moisture(request):
    try:
        print(1)
        lat = request.GET.get("lat", "6.5244")
        lon = request.GET.get("lon", "3.3792")
        print(2)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=soil_moisture_0_1cm"

        # url = (
        #     f"{OPEN_METEO_BASE}?latitude={lat}&longitude={lon}&hourly=soil_moisture_0_7cm"
        # )
        print(3)

        cache_key = f"soil_moisture_{lat}_{lon}"
        raw = cached_request(cache_key, url, timeout=900)
        print(4, url)

        if not raw or "hourly" not in raw:
            return Response({"error": "Soil moisture data unavailable"}, status=500)
        print(5)

        values = raw["hourly"].get("soil_moisture_0_1cm", [])
        timestamps = raw["hourly"].get("time", [])
        latest = values[-1] if values else None
        ts = timestamps[-1] if timestamps else timezone.now()
        print(6)

        print()
        print()
        print('latest')
        print()
        print()
    except Exception as e:
        print()
        print('error', e)
        print()
    return Response({
        "soil_moisture": latest,
        "timestamp": ts,
    })


# ⚠️ Water Quality — OpenAQ & Open-Meteo don’t provide water quality
# → fallback mock, or plan future integration with another dataset
@api_view(["GET"])
def water_quality(request):
    return Response({
        "ph": 7.2,
        "turbidity": 1.5,
        "tds": 120,
        "timestamp": timezone.now(),
        "note": "Mock data — no water quality from OpenAQ/Open-Meteo"
    })


# ⚠️ Noise Pollution — also not available in OpenAQ/Open-Meteo
# → fallback mock (could connect to city IoT later)
@api_view(["GET"])
def noise_level(request):
    return Response({
        "decibel": 65,
        "timestamp": timezone.now(),
        "note": "Mock data — no noise data from OpenAQ/Open-Meteo"
    })


# @api_view(["GET"])
# def uv_index(request):
#     # TODO: replace with real API (Open-Meteo has UV index forecast)
#     data = {
#         "uv_index": round(random.uniform(0, 11), 1),  # WHO scale 0–11+
#         "timestamp": timezone.now(),
#     }
#     return Response(data)

# @api_view(["GET"])
# def soil_moisture(request):
#     # TODO: connect to Open-Meteo soil moisture if needed
#     data = {
#         "soil_moisture": round(random.uniform(0.1, 0.5), 3),  # m³/m³
#         "timestamp": timezone.now(),
#     }
#     return Response(data)

# @api_view(["GET"])
# def water_quality(request):
#     # TODO: integrate with water quality data source if available
#     data = {
#         "ph": round(random.uniform(6.5, 8.5), 1),
#         "turbidity": round(random.uniform(0, 5), 2),   # NTU
#         "tds": random.randint(50, 500),                # ppm
#         "timestamp": timezone.now(),
#     }
#     return Response(data)

# @api_view(["GET"])
# def noise_level(request):
#     # TODO: integrate with IoT sensors or city noise data
#     data = {
#         "decibel": random.randint(40, 90),  # typical range
#         "timestamp": timezone.now(),
#     }
#     return Response(data)
