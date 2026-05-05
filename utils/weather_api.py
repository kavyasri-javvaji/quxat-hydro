import requests
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_weather_by_city(city):
    if not API_KEY:
        return None, None, "API key missing"

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()

        if res.get("cod") != 200:
            return None, None, res.get("message")

        return res["main"]["temp"], res["weather"][0]["description"], "City"

    except Exception as e:
        return None, None, str(e)


def get_weather_by_coords(lat, lon):
    if not API_KEY:
        return None, None, "API key missing"

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()

        if res.get("cod") != 200:
            return None, None, res.get("message")

        return res["main"]["temp"], res["weather"][0]["description"], "GPS"

    except Exception as e:
        return None, None, str(e)