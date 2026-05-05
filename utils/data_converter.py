import random

def get_city_water_data(city, weather=None):
    base = sum(ord(c) for c in city) % 10

    data = {
        "pH": round(6.5 + base * 0.1 + random.uniform(-0.3, 0.3), 2),
        "turbidity": round(2 + base * 0.6 + random.uniform(0, 1.5), 2),
        "tds": round(150 + base * 20 + random.uniform(0, 50), 2),
        "dissolved_oxygen": round(6 + random.uniform(-1, 1), 2),
    }

    if weather and "rain" in weather.lower():
        data["turbidity"] += 2

    return data


def evaluate_water_quality(data):
    score = 100
    breakdown = {}
    health = []

    if data["pH"] < 6.5 or data["pH"] > 8.5:
        score -= 20
        breakdown["pH"] = "Out of safe range"
        health.append("Skin irritation risk")

    if data["turbidity"] > 5:
        score -= 20
        breakdown["turbidity"] = "Water not clear"
        health.append("Possible contamination")

    if data["tds"] > 300:
        score -= 20
        breakdown["tds"] = "High dissolved solids"
        health.append("Not suitable for drinking")

    if score > 80:
        result = "Safe"
    elif score > 50:
        result = "Moderate"
    else:
        result = "Unsafe"

    return score, result, breakdown, health