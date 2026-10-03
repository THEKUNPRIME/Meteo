"""Open-Meteo geocoding and forecast requests."""

import logging
from datetime import date

import httpx2 as httpx

log = logging.getLogger("app.weather_api")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEEKDAYS_FR = ("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim")


class WeatherAPIError(Exception):
    """A readable error returned by the weather service."""


def _at(values, index, default=None):
    if not isinstance(values, list) or index >= len(values):
        return default
    return values[index]


def _number(value):
    if value is None:
        return None
    try:
        return round(value)
    except (TypeError, ValueError):
        return None


def _time(value):
    if not value:
        return None
    return str(value).split("T")[-1][:5]


def _condition(code):
    if code is None:
        return "-"
    if code == 0:
        return "Ciel dégagé"
    if code in (1, 2, 3):
        return "Peu nuageux" if code == 1 else "Partiellement nuageux" if code == 2 else "Couvert"
    if code in (45, 48):
        return "Brouillard"
    if code in (51, 53, 55, 56, 57):
        return "Bruine"
    if code in (61, 63, 65, 66, 67):
        return "Pluie"
    if code in (71, 73, 75, 77, 85, 86):
        return "Neige"
    if code in (80, 81, 82):
        return "Averses"
    if code in (95, 96, 99):
        return "Orage"
    return "-"


def _icon_name(code):
    if code == 0:
        return "WB_SUNNY"
    if code in (45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99):
        return "WATER_DROP" if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82) else "CLOUD"
    return "CLOUD"


async def fetch_weather(city):
    """Find a city and return current, hourly and five-day weather data."""
    query = city.strip()
    if not query:
        raise WeatherAPIError("Saisissez le nom d’une ville.")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            geo_response = await client.get(
                GEOCODING_URL,
                params={"name": query, "count": 1, "language": "fr", "format": "json"},
            )
            geo_response.raise_for_status()
            places = geo_response.json().get("results") or []
            if not places:
                raise WeatherAPIError(f"Ville introuvable : {query}.")

            place = places[0]
            forecast_response = await client.get(
                FORECAST_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                    "hourly": "temperature_2m,weather_code,uv_index",
                    "daily": "temperature_2m_max,temperature_2m_min,weather_code,sunrise,sunset",
                    "forecast_days": 5,
                    "timezone": "auto",
                },
            )
            forecast_response.raise_for_status()
            payload = forecast_response.json()
    except WeatherAPIError:
        raise
    except httpx.HTTPError as exc:
        log.warning("Weather request failed for %s: %s", query, exc)
        raise WeatherAPIError("Impossible de joindre le service météo. Réessayez.") from exc
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("Unexpected weather response for %s: %s", query, exc)
        raise WeatherAPIError("La réponse météo est momentanément invalide.") from exc

    current = payload.get("current") or {}
    hourly = payload.get("hourly") or {}
    daily = payload.get("daily") or {}
    times = hourly.get("time") or []
    current_time = current.get("time")
    start = next((i for i, item in enumerate(times) if item[:13] == (current_time or "")[:13]), 0)

    hour_items = []
    for i in range(start, min(start + 6, len(times))):
        timestamp = _at(times, i)
        hour_items.append({
            "label": "Maintenant" if i == start else _time(timestamp),
            "temperature": _number(_at(hourly.get("temperature_2m"), i)),
            "code": _at(hourly.get("weather_code"), i),
            "icon": _icon_name(_at(hourly.get("weather_code"), i)),
        })

    day_items = []
    for i, timestamp in enumerate(daily.get("time") or []):
        try:
            day_label = "Aujourd’hui" if i == 0 else WEEKDAYS_FR[date.fromisoformat(timestamp).weekday()]
        except (ValueError, TypeError):
            day_label = "-"
        day_items.append({
            "label": day_label,
            "high": _number(_at(daily.get("temperature_2m_max"), i)),
            "low": _number(_at(daily.get("temperature_2m_min"), i)),
            "code": _at(daily.get("weather_code"), i),
            "icon": _icon_name(_at(daily.get("weather_code"), i)),
        })

    location_parts = [place.get("name"), place.get("admin1"), place.get("country")]
    location = ", ".join(dict.fromkeys(part for part in location_parts if part)) or query
    return {
        "location": location,
        "temperature": _number(current.get("temperature_2m")),
        "feels_like": _number(current.get("apparent_temperature")),
        "condition": _condition(current.get("weather_code")),
        "code": current.get("weather_code"),
        "icon": _icon_name(current.get("weather_code")),
        "humidity": _number(current.get("relative_humidity_2m")),
        "wind": _number(current.get("wind_speed_10m")),
        "uv": _number(_at(hourly.get("uv_index"), start)), 
        "sunrise": _time(_at(daily.get("sunrise"), 0)),
        "sunset": _time(_at(daily.get("sunset"), 0)),
        "high": _number(_at(daily.get("temperature_2m_max"), 0)),
        "low": _number(_at(daily.get("temperature_2m_min"), 0)),
        "hourly": hour_items,
        "daily": day_items,
    }
