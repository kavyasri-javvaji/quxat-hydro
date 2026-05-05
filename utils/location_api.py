import pandas as pd
import os
import requests

def load_cities():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "data", "india_cities.csv")

    df = pd.read_csv(path)
    return df["city"].dropna().unique().tolist()


def get_city_from_coords(lat, lon, api_key):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={api_key}"
        res = requests.get(url, timeout=5).json()

        if res:
            return res[0].get("name", "Your Location")

    except:
        pass

    return "Your Location"