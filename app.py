import streamlit as st
import pandas as pd
import numpy as np
import os
import time
import json
import requests
from datetime import datetime, timedelta
from streamlit_js_eval import get_geolocation
import streamlit.components.v1 as components
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from utils.weather_api import get_weather_by_city, get_weather_by_coords
from utils.location_api import load_cities, get_city_from_coords
from utils.data_converter import get_city_water_data, evaluate_water_quality

st.set_page_config(layout="wide", page_title="QuXAT Hydro", page_icon="💧")

# =========================
# SESSION STATE
# =========================
for key, val in {
    "logged_in": False, "users": {}, "history": [],
    "snapshots": [], "alert_timeline": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# =========================
# LOGIN PAGE
# =========================
def login():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg,#0f2027,#203a43,#2c5364); color: white; }
    .login-box { max-width: 400px; margin: 80px auto; background: rgba(255,255,255,0.07);
        backdrop-filter: blur(20px); border-radius: 20px; padding: 40px;
        border: 1px solid rgba(255,255,255,0.15); }
    </style>
    <div class="login-box">
    <h2 style="text-align:center;color:#00c6ff;">💧 QuXAT Hydro</h2>
    <p style="text-align:center;color:#aaa;">Water Quality Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Login", use_container_width=True):
            if u in st.session_state.users and st.session_state.users[u] == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid credentials")
    with c2:
        if st.button("Sign Up", use_container_width=True):
            if u and p:
                st.session_state.users[u] = p
                st.success("Account created! Please login.")
            else:
                st.warning("Enter username and password")

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================
# GLOBAL CSS
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600&display=swap');

.stApp {
    background: linear-gradient(135deg,#0a1628,#0d2137,#0f2b3d);
    color: white;
    font-family: 'Exo 2', sans-serif;
}

/* Floating particles background */
.particles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; overflow: hidden; }
.particle { position: absolute; border-radius: 50%; background: rgba(0,198,255,0.15); animation: drift linear infinite; }
@keyframes drift { 0%{transform:translateY(100vh) scale(0);opacity:0} 10%{opacity:1} 90%{opacity:0.5} 100%{transform:translateY(-100px) scale(1);opacity:0} }

.glass {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(16px);
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 12px;
    border: 1px solid rgba(0,198,255,0.2);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    transition: all 0.3s ease;
}
.glass:hover { border-color: rgba(0,198,255,0.5); transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,198,255,0.15); }

.metric-card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(16px);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    border: 1px solid rgba(0,198,255,0.2);
    transition: all 0.3s;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(0,198,255,0.05) 0%, transparent 70%);
    animation: rotate 8s linear infinite;
}
@keyframes rotate { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }

.metric-value {
    font-family: 'Orbitron', monospace;
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #00c6ff, #0072ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.metric-label { font-size: 0.85rem; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 2px; margin-top: 4px; }

.wqi-display {
    font-family: 'Orbitron', monospace;
    font-size: 3rem;
    font-weight: 900;
    text-align: center;
    padding: 20px;
    border-radius: 20px;
    background: linear-gradient(135deg,rgba(0,198,255,0.15),rgba(0,114,255,0.15));
    border: 2px solid rgba(0,198,255,0.3);
    text-shadow: 0 0 30px rgba(0,198,255,0.5);
}

.section-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    color: #00c6ff;
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-bottom: 12px;
    border-bottom: 1px solid rgba(0,198,255,0.3);
    padding-bottom: 8px;
}

.alert-item {
    padding: 10px 16px;
    border-radius: 10px;
    margin-bottom: 8px;
    border-left: 4px solid;
    animation: slideIn 0.5s ease;
}
@keyframes slideIn { from{transform:translateX(-20px);opacity:0} to{transform:translateX(0);opacity:1} }
.alert-warn { background: rgba(255,152,0,0.15); border-color: #ff9800; }
.alert-danger { background: rgba(244,67,54,0.15); border-color: #f44336; animation: pulse 1s infinite, slideIn 0.5s ease; }
@keyframes pulse { 50%{ box-shadow: 0 0 15px rgba(244,67,54,0.5); } }

.story-card {
    background: rgba(0,198,255,0.08);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(0,198,255,0.2);
    font-style: italic;
    line-height: 1.8;
    color: rgba(255,255,255,0.9);
    font-size: 1.05rem;
}

.activity-btn {
    padding: 12px 16px;
    border-radius: 12px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(0,198,255,0.3);
    color: white;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
    margin-bottom: 8px;
}
.activity-safe { background: rgba(76,175,80,0.2); border-color: #4caf50; }
.activity-caution { background: rgba(255,152,0,0.2); border-color: #ff9800; }
.activity-unsafe { background: rgba(244,67,54,0.2); border-color: #f44336; }

.rank-bar { height: 8px; border-radius: 4px; margin: 4px 0; background: linear-gradient(90deg, #00c6ff, #0072ff); }

.timeline-item {
    display: flex;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    animation: slideIn 0.4s ease;
}

.stButton button {
    background: linear-gradient(135deg,#00c6ff,#0072ff) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Exo 2', sans-serif !important;
    font-weight: 600 !important;
    transition: all 0.3s !important;
}
.stButton button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 20px rgba(0,198,255,0.3) !important; }

.big-drink button {
    background: linear-gradient(135deg,#ff416c,#ff4b2b) !important;
    font-size: 1.2rem !important;
    padding: 16px !important;
    width: 100% !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
::-webkit-scrollbar-thumb { background: rgba(0,198,255,0.4); border-radius: 3px; }
</style>

<!-- Floating particles -->
<div class="particles" id="particles"></div>
<script>
const p=document.getElementById('particles');
if(p){for(let i=0;i<20;i++){const d=document.createElement('div');d.className='particle';const s=Math.random()*12+4;d.style.cssText=`width:${s}px;height:${s}px;left:${Math.random()*100}%;animation-duration:${Math.random()*15+10}s;animation-delay:${Math.random()*10}s;`;p.appendChild(d);}}
</script>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
h1, h2, h3 = st.columns([6, 2, 1])
h1.markdown(f"""
<div style="font-family:'Orbitron',monospace;">
<span style="font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,#00c6ff,#0072ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">💧 QuXAT Hydro</span>
<span style="font-size:0.85rem;color:rgba(255,255,255,0.5);margin-left:12px;">Water Quality Intelligence</span>
</div>
""", unsafe_allow_html=True)
h2.markdown(f"<div style='padding-top:8px;color:rgba(255,255,255,0.7);font-size:0.9rem;'>👤 {st.session_state.user}</div>", unsafe_allow_html=True)
if h3.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.markdown("<hr style='border-color:rgba(0,198,255,0.2);margin:8px 0 16px;'>", unsafe_allow_html=True)

# =========================
# LOCATION
# =========================
cities = load_cities()
api = os.getenv("OPENWEATHER_API_KEY")

col_loc, col_date = st.columns([3, 1])
with col_loc:
    sel = st.selectbox("📍 Select Location", ["📍 My Location"] + cities)
with col_date:
    st.markdown(f"<div style='padding-top:28px;color:rgba(255,255,255,0.6);font-size:0.85rem;'>🗓 {datetime.now().strftime('%d %b %Y, %I:%M %p')}</div>", unsafe_allow_html=True)

lat, lon, city = None, None, None
if sel == "📍 My Location":
    loc = get_geolocation()
    if loc:
        lat = loc["coords"]["latitude"]
        lon = loc["coords"]["longitude"]
        city = get_city_from_coords(lat, lon, api)
else:
    city = sel

if not city:
    city = "Vijayawada"

st.markdown(f"<div style='color:rgba(0,198,255,0.8);font-size:0.9rem;margin-bottom:8px;'>📍 Location: <b>{city}</b></div>", unsafe_allow_html=True)

# =========================
# DATA FETCH
# =========================
with st.spinner("🔄 Fetching water quality data..."):
    if lat and lon:
        temp, weather, _ = get_weather_by_coords(lat, lon)
    else:
        temp, weather, _ = get_weather_by_city(city)
    if not temp: temp = 28.0
    if not weather: weather = "clear sky"

    data = get_city_water_data(city, weather)
    score, result, breakdown, health = evaluate_water_quality(data)

# Dynamic theme color
theme_color = "#00c6ff" if score > 80 else "#ffd200" if score > 60 else "#ff9800" if score > 40 else "#f44336"
st.markdown(f"<style>:root{{--theme:{theme_color};}}.metric-value{{background:linear-gradient(135deg,{theme_color},#0072ff)!important;-webkit-background-clip:text;-webkit-text-fill-color:transparent;}}</style>", unsafe_allow_html=True)

# =========================
# WEATHER + RAIN BANNER
# =========================
weather_icon = "🌧" if "rain" in weather.lower() else "⛅" if "cloud" in weather.lower() else "☀️"
rain_forecast = 0
try:
    if lat and lon:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=auto"
        rain_data = requests.get(url, timeout=5).json()
        rain_forecast = max(rain_data["daily"]["precipitation_sum"][:3])
except:
    pass

wcol1, wcol2 = st.columns([1, 1])
with wcol1:
    st.markdown(f"""
    <div class="glass">
    <div class="section-title">🌡 Weather</div>
    <div style="font-size:2rem;">{weather_icon}</div>
    <div style="font-size:1.8rem;font-family:'Orbitron',monospace;color:{theme_color};">{temp}°C</div>
    <div style="color:rgba(255,255,255,0.6);text-transform:capitalize;">{weather}</div>
    </div>
    """, unsafe_allow_html=True)

with wcol2:
    if rain_forecast > 10:
        st.markdown(f"""
        <div class="alert-danger" style="height:100%;display:flex;align-items:center;gap:12px;padding:20px;">
        <div style="font-size:2rem;">🌧</div>
        <div>
        <b style="color:#ff9800;">Rain Impact Alert</b><br>
        <span style="font-size:0.9rem;">{rain_forecast:.1f}mm expected — Turbidity may spike.<br>Avoid untreated water for 24–48 hrs</span>
        </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="glass" style="height:100%;display:flex;align-items:center;gap:12px;padding:20px;">
        <div style="font-size:2rem;">✅</div>
        <div><b style="color:#4caf50;">No Rain Risk</b><br><span style="color:rgba(255,255,255,0.6);font-size:0.9rem;">Water quality stable<br>No weather alerts</span></div>
        </div>
        """, unsafe_allow_html=True)

# =========================
# METRIC CARDS (animated)
# =========================
st.markdown("<div class='section-title' style='margin-top:16px;'>📊 Water Parameters</div>", unsafe_allow_html=True)

def param_color(param, val):
    if param == "pH": return "#4caf50" if 6.5 <= val <= 8.5 else "#f44336"
    if param == "turbidity": return "#4caf50" if val <= 4 else "#ff9800" if val <= 6 else "#f44336"
    if param == "tds": return "#4caf50" if val <= 300 else "#ff9800" if val <= 500 else "#f44336"
    if param == "do": return "#4caf50" if val >= 6 else "#ff9800" if val >= 4 else "#f44336"
    return "#00c6ff"

mc1, mc2, mc3, mc4 = st.columns(4)
params = [
    (mc1, "pH", data['pH'], "6.5–8.5 safe", "🧪"),
    (mc2, "Turbidity", data['turbidity'], "< 4 NTU safe", "💧"),
    (mc3, "TDS", data['tds'], "< 300 mg/L", "🔬"),
    (mc4, "Dissolved O₂", data['dissolved_oxygen'], "> 6 mg/L safe", "⚗️"),
]
for col, label, val, hint, icon in params:
    c = param_color(label.lower().replace(" ", "").replace("₂",""), val)
    col.markdown(f"""
    <div class="metric-card">
    <div style="font-size:1.5rem;margin-bottom:4px;">{icon}</div>
    <div class="metric-value" style="background:linear-gradient(135deg,{c},{c}aa);-webkit-background-clip:text;">{val}</div>
    <div class="metric-label">{label}</div>
    <div style="font-size:0.75rem;color:rgba(255,255,255,0.4);margin-top:6px;">{hint}</div>
    <div style="height:3px;border-radius:2px;background:{c};margin-top:8px;opacity:0.6;"></div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# WQI GAUGE + EMOJI SLIDER
# =========================
st.markdown("<br>", unsafe_allow_html=True)
g1, g2 = st.columns([1, 2])

with g1:
    emoji = "😊" if score > 80 else "😐" if score > 60 else "😟" if score > 40 else "🤢"
    wqi_color = "#4caf50" if score > 80 else "#ffd200" if score > 60 else "#ff9800" if score > 40 else "#f44336"
    st.markdown(f"""
    <div class="glass" style="text-align:center;">
    <div class="section-title">💧 Water Quality Index</div>
    <div style="font-size:4rem;">{emoji}</div>
    <div style="font-family:'Orbitron',monospace;font-size:3.5rem;font-weight:900;color:{wqi_color};text-shadow:0 0 30px {wqi_color}88;">{score}</div>
    <div style="font-size:1.1rem;color:{wqi_color};font-weight:600;margin-top:4px;">{result}</div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin-top:8px;">out of 100</div>
    </div>
    """, unsafe_allow_html=True)

with g2:
    slider_pct = min(score, 100)
    components.html(f"""
    <style>
    body{{margin:0;background:transparent;font-family:'Exo 2',sans-serif;}}
    .slider-wrap{{background:rgba(255,255,255,0.05);border-radius:16px;padding:20px;border:1px solid rgba(0,198,255,0.2);}}
    .slider-title{{color:#00c6ff;font-size:0.8rem;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px;}}
    .track{{height:20px;border-radius:10px;background:linear-gradient(90deg,#4caf50,#ffd200,#ff9800,#f44336);position:relative;margin:30px 0 10px;}}
    .marker{{position:absolute;top:-20px;transform:translateX(-50%);font-size:1.8rem;transition:left 1s cubic-bezier(.34,1.56,.64,1);}}
    .labels{{display:flex;justify-content:space-between;color:rgba(255,255,255,0.5);font-size:0.75rem;}}
    </style>
    <div class="slider-wrap">
    <div class="slider-title">WQI Safety Slider</div>
    <div class="track">
      <div class="marker" id="mk" style="left:0%">{emoji}</div>
    </div>
    <div class="labels">
      <span>Unsafe<br>0</span><span>Poor<br>25</span><span>Moderate<br>50</span><span>Good<br>75</span><span>Safe<br>100</span>
    </div>
    </div>
    <script>
    setTimeout(()=>{{document.getElementById('mk').style.left='{slider_pct}%';}},300);
    </script>
    """, height=130)

    # Health advice
    advice = {
        "Safe": "✅ Water meets all safety standards. Safe for drinking, cooking, and all household uses.",
        "Moderate": "⚠️ Acceptable for most uses. Consider filtering before drinking. Safe for bathing and cooking.",
        "Unsafe": "❌ Water quality is poor. Use only after proper treatment. Not safe for direct consumption."
    }
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.05);border-radius:12px;padding:16px;border-left:4px solid {wqi_color};margin-top:8px;">
    <div style="color:{wqi_color};font-weight:600;margin-bottom:4px;">Health Advisory</div>
    <div style="color:rgba(255,255,255,0.8);font-size:0.9rem;">{advice.get(result, advice['Moderate'])}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# FEATURE 1: VIRTUAL WATER TANK
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🏺 Virtual Water Tank</div>", unsafe_allow_html=True)
tank_r = score / 100
r = int(255 * (1 - tank_r))
g_val = int(200 * tank_r)
b = int(255 * tank_r)
liquid_color = f"rgb({r},{g_val},{b})"
turbidity_opacity = min(data['turbidity'] / 10, 0.8)

components.html(f"""
<style>
body{{margin:0;background:transparent;}}
.tank-wrap{{display:flex;gap:20px;align-items:center;background:rgba(255,255,255,0.05);border-radius:16px;padding:20px;border:1px solid rgba(0,198,255,0.2);}}
.tank{{width:120px;height:180px;border:3px solid rgba(0,198,255,0.5);border-radius:8px;position:relative;overflow:hidden;background:rgba(0,0,0,0.3);}}
.liquid{{position:absolute;bottom:0;width:100%;background:{liquid_color};transition:height 2s ease;opacity:0.85;}}
.wave{{position:absolute;top:-10px;left:-50%;width:200%;height:20px;background:{liquid_color};border-radius:40%;animation:wave 2s infinite linear;}}
@keyframes wave{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}
.particle-dot{{position:absolute;border-radius:50%;background:rgba(139,90,43,0.6);animation:float {'{:.1f}'.format(2+tank_r)}s infinite ease-in-out;}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
.bubble{{position:absolute;border-radius:50%;background:rgba(255,255,255,0.3);animation:rise 3s infinite;}}
@keyframes rise{{0%{{bottom:0;opacity:1}}100%{{bottom:100%;opacity:0}}}}
.info{{flex:1;color:white;}}
.fill-pct{{font-size:2.5rem;font-weight:900;font-family:'Orbitron',monospace;color:{liquid_color};text-shadow:0 0 20px {liquid_color};}}
</style>
<div class="tank-wrap">
<div class="tank">
  <div class="liquid" id="liq" style="height:0%">
    <div class="wave"></div>
  </div>
  {''.join([f'<div class="particle-dot" style="width:{6+i*2}px;height:{6+i*2}px;left:{10+i*15}%;bottom:{10+i*8}%;animation-delay:{i*0.4}s;opacity:{turbidity_opacity};"></div>' for i in range(5)])}
  {''.join([f'<div class="bubble" style="width:{4+i*2}px;height:{4+i*2}px;left:{15+i*20}%;animation-delay:{i*0.8}s;"></div>' for i in range(4)])}
</div>
<div class="info">
  <div class="fill-pct">{score}%</div>
  <div style="color:rgba(255,255,255,0.7);margin:8px 0;">Safety Level</div>
  <div style="font-size:0.9rem;color:rgba(255,255,255,0.5);">Turbidity particles: {'High' if data['turbidity']>5 else 'Low'}</div>
  <div style="font-size:0.9rem;color:rgba(255,255,255,0.5);margin-top:4px;">pH Balance: {'⚠ Off' if data['pH']<6.5 or data['pH']>8.5 else '✅ Normal'}</div>
  <div style="font-size:0.9rem;color:rgba(255,255,255,0.5);margin-top:4px;">Tank Status: {'🔴 Critical — Do Not Use' if score<40 else '🟡 Treat Before Use' if score<70 else '🟢 Safe to Use'}</div>
</div>
</div>
<script>setTimeout(()=>{{document.getElementById('liq').style.height='{score}%';}},400);</script>
""", height=220)

# =========================
# FEATURE 2: WATER MOOD DROP
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>💧 Water Mood</div>", unsafe_allow_html=True)
mood_color = "#00c6ff" if score > 80 else "#ffd200" if score > 60 else "#ff9800" if score > 40 else "#cc2200"
mood_anim = "bounce" if score > 80 else "sway" if score > 60 else "pulse_slow" if score > 40 else "shake"
mood_face = "happy" if score > 80 else "neutral" if score > 60 else "sad" if score > 40 else "sick"
mood_msg = {
    "happy": "Your water is happy and healthy! 😊",
    "neutral": "Water quality is acceptable but could be better.",
    "sad": "Water is struggling — treatment recommended.",
    "sick": "Water is in poor condition — avoid use! 🤢"
}

components.html(f"""
<style>
body{{margin:0;background:transparent;font-family:'Exo 2',sans-serif;color:white;}}
.mood-wrap{{display:flex;align-items:center;gap:24px;background:rgba(255,255,255,0.05);border-radius:16px;padding:20px;border:1px solid rgba(0,198,255,0.2);}}
.drop-svg{{animation:{mood_anim} 2s infinite ease-in-out;}}
@keyframes bounce{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-15px)}}}}
@keyframes sway{{0%,100%{{transform:rotate(-5deg)}}50%{{transform:rotate(5deg)}}}}
@keyframes pulse_slow{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.08)}}}}
@keyframes shake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-4px)}}75%{{transform:translateX(4px)}}}}
</style>
<div class="mood-wrap">
<div class="drop-svg">
<svg width="80" height="100" viewBox="0 0 80 100">
  <defs><radialGradient id="dg" cx="40%" cy="30%"><stop offset="0%" stop-color="white" stop-opacity="0.4"/><stop offset="100%" stop-color="{mood_color}"/></radialGradient></defs>
  <path d="M40 5 C40 5 10 50 10 65 A30 30 0 0 0 70 65 C70 50 40 5 40 5Z" fill="url(#dg)" stroke="{mood_color}" stroke-width="2"/>
  {"<!-- happy --><circle cx='30' cy='60' r='4' fill='#0a1628'/><circle cx='50' cy='60' r='4' fill='#0a1628'/><path d='M28 72 Q40 82 52 72' stroke='#0a1628' stroke-width='3' fill='none' stroke-linecap='round'/>" if mood_face == "happy" else ""}
  {"<!-- neutral --><circle cx='30' cy='60' r='4' fill='#0a1628'/><circle cx='50' cy='60' r='4' fill='#0a1628'/><line x1='28' y1='74' x2='52' y2='74' stroke='#0a1628' stroke-width='3' stroke-linecap='round'/>" if mood_face == "neutral" else ""}
  {"<!-- sad --><circle cx='30' cy='60' r='4' fill='#0a1628'/><circle cx='50' cy='60' r='4' fill='#0a1628'/><path d='M28 76 Q40 68 52 76' stroke='#0a1628' stroke-width='3' fill='none' stroke-linecap='round'/>" if mood_face == "sad" else ""}
  {"<!-- sick --><line x1='26' y1='56' x2='34' y2='64' stroke='#0a1628' stroke-width='3'/><line x1='34' y1='56' x2='26' y2='64' stroke='#0a1628' stroke-width='3'/><line x1='46' y1='56' x2='54' y2='64' stroke='#0a1628' stroke-width='3'/><line x1='54' y1='56' x2='46' y2='64' stroke='#0a1628' stroke-width='3'/><path d='M28 76 Q40 68 52 76' stroke='#0a1628' stroke-width='3' fill='none' stroke-linecap='round'/>" if mood_face == "sick" else ""}
</svg>
</div>
<div>
  <div style="font-size:1.3rem;font-weight:600;color:{mood_color};">{mood_msg[mood_face]}</div>
  <div style="color:rgba(255,255,255,0.5);font-size:0.9rem;margin-top:8px;">WQI {score} • {result} Quality • {city}</div>
  <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
    {"".join([f'<span style="padding:4px 10px;border-radius:20px;font-size:0.8rem;background:rgba(244,67,54,0.2);border:1px solid #f44336;color:#f44336;">{a}</span>' for a in health]) if health else '<span style="padding:4px 10px;border-radius:20px;font-size:0.8rem;background:rgba(76,175,80,0.2);border:1px solid #4caf50;color:#4caf50;">No health concerns</span>'}
  </div>
</div>
</div>
""", height=160)

# =========================
# FEATURE 3: CAN I USE THIS WATER FOR...
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🧪 Can I Use This Water For...</div>", unsafe_allow_html=True)

activities = {
    "💧 Drinking": {"tds_max": 300, "turb_max": 1, "ph_range": (6.5, 8.5), "do_min": 6},
    "🍳 Cooking": {"tds_max": 500, "turb_max": 4, "ph_range": (6.0, 9.0), "do_min": 4},
    "🛁 Bathing": {"tds_max": 1000, "turb_max": 10, "ph_range": (5.5, 9.5), "do_min": 2},
    "🌱 Watering Plants": {"tds_max": 800, "turb_max": 15, "ph_range": (5.0, 9.0), "do_min": 1},
    "🏊 Swimming": {"tds_max": 400, "turb_max": 2, "ph_range": (7.0, 7.6), "do_min": 5},
}

act_cols = st.columns(len(activities))
for i, (act_name, limits) in enumerate(activities.items()):
    issues = []
    if data['tds'] > limits['tds_max']: issues.append(f"TDS {data['tds']} > {limits['tds_max']}")
    if data['turbidity'] > limits['turb_max']: issues.append(f"Turbidity {data['turbidity']} > {limits['turb_max']}")
    if not (limits['ph_range'][0] <= data['pH'] <= limits['ph_range'][1]): issues.append(f"pH {data['pH']} out of range")
    if data['dissolved_oxygen'] < limits['do_min']: issues.append(f"DO too low")

    if not issues:
        status, icon, cls = "Safe", "✅", "activity-safe"
    elif len(issues) == 1:
        status, icon, cls = "Caution", "⚠️", "activity-caution"
    else:
        status, icon, cls = "Unsafe", "❌", "activity-unsafe"

    reason = issues[0] if issues else "All parameters within limits"
    act_cols[i].markdown(f"""
    <div class="activity-btn {cls}" style="cursor:default;">
    <div style="font-size:1.5rem;">{act_name.split()[0]}</div>
    <div style="font-size:0.8rem;margin-top:4px;">{act_name.split(' ',1)[1]}</div>
    <div style="font-size:1.3rem;margin:6px 0;">{icon}</div>
    <div style="font-size:0.85rem;font-weight:600;">{status}</div>
    <div style="font-size:0.7rem;color:rgba(255,255,255,0.6);margin-top:4px;">{reason}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# FEATURE 4: PURIFIER RECOMMENDER
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🫙 Water Purifier Recommender</div>", unsafe_allow_html=True)

filters = []
if data['tds'] > 500: filters.append(("RO Filter", "💎", "#00c6ff", f"TDS {data['tds']} mg/L exceeds 500. RO removes dissolved salts.", "₹8,000–25,000"))
if data['turbidity'] > 4: filters.append(("UF Filter", "🌊", "#4caf50", f"Turbidity {data['turbidity']} NTU exceeds 4. UF removes particles.", "₹3,000–8,000"))
if data['dissolved_oxygen'] < 5: filters.append(("UV Purifier", "☀️", "#ffd200", "Low dissolved oxygen suggests bacterial risk. UV eliminates bacteria.", "₹2,000–6,000"))
if data['pH'] < 6.5 or data['pH'] > 8.5: filters.append(("pH Balancer", "⚗️", "#ff9800", f"pH {data['pH']} is out of safe range (6.5–8.5). pH correction needed.", "₹1,500–4,000"))
if not filters: filters.append(("Basic Sediment Filter", "🔵", "#4caf50", "Water quality is good! A basic sediment filter is sufficient.", "₹500–1,500"))

f_cols = st.columns(min(len(filters), 4))
for i, (name, icon, color, reason, cost) in enumerate(filters[:4]):
    f_cols[i % len(f_cols)].markdown(f"""
    <div class="glass" style="border-color:{color}44;text-align:center;">
    <div style="font-size:2rem;">{icon}</div>
    <div style="color:{color};font-weight:700;margin:6px 0;">{name}</div>
    <div style="font-size:0.8rem;color:rgba(255,255,255,0.6);margin-bottom:8px;">{reason}</div>
    <div style="background:{color}22;border-radius:8px;padding:4px 8px;font-size:0.8rem;color:{color};">Est. Cost: {cost}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# FEATURE 5: WATER QUALITY STORY
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>📖 Today's Water Story</div>", unsafe_allow_html=True)

def generate_story(city, score, result, data, weather, temp):
    season = "summer" if temp and temp > 35 else "monsoon" if weather and "rain" in weather.lower() else "winter" if temp and temp < 15 else "current"
    tds_note = f"The dissolved solids ({data['tds']} mg/L) are elevated, possibly due to {season} conditions and mineral runoff." if data['tds'] > 300 else f"Dissolved solids are within acceptable limits at {data['tds']} mg/L."
    turb_note = f"Water clarity is reduced with turbidity at {data['turbidity']} NTU — visible particles may be present." if data['turbidity'] > 4 else f"Water appears clear with turbidity at {data['turbidity']} NTU."
    ph_note = f"The pH level of {data['pH']} is slightly {'acidic' if data['pH'] < 6.5 else 'alkaline'} — outside the ideal range." if data['pH'] < 6.5 or data['pH'] > 8.5 else f"pH is balanced at {data['pH']}, within the safe range."
    rec = "Safe for all household uses without treatment." if score > 80 else "Filtration is recommended before drinking." if score > 50 else "Water should be treated before any use. Consider boiling or RO filtration."
    return f"Today in {city}, the water quality index stands at {score} — classified as {result}. {tds_note} {turb_note} {ph_note} {rec}"

story_text = generate_story(city, score, result, data, weather, temp)

s1, s2 = st.columns([4, 1])
with s1:
    st.markdown(f'<div class="story-card"><span style="font-size:1.5rem;margin-right:8px;">💬</span>{story_text}</div>', unsafe_allow_html=True)
with s2:
    if st.button("🔄 Regenerate Story", use_container_width=True):
        st.rerun()

# =========================
# FEATURE 6: WATER STORAGE CALCULATOR
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>⏱️ Safe Water Storage Calculator</div>", unsafe_allow_html=True)

sc1, sc2, sc3 = st.columns(3)
with sc1:
    container_type = st.selectbox("Container Type", ["Closed Bottle", "Closed Container", "Open Container"])
with sc2:
    storage_loc = st.selectbox("Storage Location", ["Refrigerator (4°C)", "Room Temperature", "Outside / Hot Area"])
with sc3:
    st.markdown("<br>", unsafe_allow_html=True)
    calc_storage = st.button("⏱️ Calculate", use_container_width=True)

if calc_storage:
    base_hours = 72
    tds_factor = max(0.5, 1 - (data['tds'] - 300) / 1000) if data['tds'] > 300 else 1.0
    ph_factor = 0.7 if (data['pH'] < 6.5 or data['pH'] > 8.5) else 1.0
    turb_factor = 0.7 if data['turbidity'] > 4 else 1.0
    temp_factor = 0.4 if "outside" in storage_loc.lower() else 0.7 if "room" in storage_loc.lower() else 1.0
    container_factor = 1.0 if "closed bottle" in container_type.lower() else 0.8 if "closed" in container_type.lower() else 0.4
    safe_hours = int(base_hours * tds_factor * ph_factor * turb_factor * temp_factor * container_factor)
    safe_hours = max(2, min(safe_hours, 168))
    days = safe_hours // 24
    hrs = safe_hours % 24

    storage_color = "#4caf50" if safe_hours > 48 else "#ff9800" if safe_hours > 12 else "#f44336"
    st.markdown(f"""
    <div class="glass" style="border-color:{storage_color}44;display:flex;align-items:center;gap:20px;margin-top:8px;">
    <div style="font-size:3rem;font-family:'Orbitron',monospace;color:{storage_color};">{safe_hours}h</div>
    <div>
    <div style="font-weight:600;color:{storage_color};">Safe Storage Duration: {days} days {hrs} hours</div>
    <div style="color:rgba(255,255,255,0.6);font-size:0.85rem;margin-top:4px;">In {container_type.lower()} at {storage_loc.lower()}</div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.8rem;margin-top:4px;">Based on current TDS, pH, and turbidity levels</div>
    </div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# FEATURE 7: CONTAMINATION SOURCE CLASSIFIER
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🏭 Contamination Source Classifier</div>", unsafe_allow_html=True)

sources = {
    "Industrial/Mining Runoff": 0,
    "Agricultural Runoff": 0,
    "Natural Minerals": 0,
    "Soil Erosion / Construction": 0,
    "Acid Rain / Discharge": 0,
}
if data['tds'] > 400 and data['pH'] < 7: sources["Industrial/Mining Runoff"] += 40
if data['tds'] > 300: sources["Natural Minerals"] += 25
if data['turbidity'] > 5 and data['dissolved_oxygen'] < 5: sources["Agricultural Runoff"] += 35
if data['turbidity'] > 6: sources["Soil Erosion / Construction"] += 30
if data['pH'] < 6.5 and data['tds'] > 400: sources["Acid Rain / Discharge"] += 20
sources = {k: max(5, v) for k, v in sources.items()}
total = sum(sources.values())
sources = {k: round(v / total * 100) for k, v in sources.items()}
primary = max(sources, key=sources.get)

src_icons = {"Industrial/Mining Runoff": "🏭", "Agricultural Runoff": "🌾", "Natural Minerals": "⛰️", "Soil Erosion / Construction": "🏗️", "Acid Rain / Discharge": "🌧️"}
src_colors = {"Industrial/Mining Runoff": "#f44336", "Agricultural Runoff": "#ff9800", "Natural Minerals": "#4caf50", "Soil Erosion / Construction": "#ffd200", "Acid Rain / Discharge": "#9c27b0"}

st.markdown(f"""
<div class="glass">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
<div>
  <div style="font-size:1rem;color:rgba(255,255,255,0.5);">Primary Contamination Source</div>
  <div style="font-size:1.4rem;font-weight:700;color:{src_colors[primary]};margin-top:4px;">{src_icons[primary]} {primary}</div>
</div>
<div style="text-align:right;">
  <div style="font-size:0.8rem;color:rgba(255,255,255,0.5);">Confidence</div>
  <div style="font-size:2rem;font-family:'Orbitron',monospace;color:{src_colors[primary]};">{sources[primary]}%</div>
</div>
</div>
""", unsafe_allow_html=True)

for src, pct in sorted(sources.items(), key=lambda x: -x[1]):
    st.markdown(f"""
<div style="margin-bottom:10px;">
<div style="display:flex;justify-content:space-between;color:rgba(255,255,255,0.8);font-size:0.85rem;margin-bottom:4px;">
  <span>{src_icons[src]} {src}</span><span style="color:{src_colors[src]};">{pct}%</span>
</div>
<div style="height:8px;background:rgba(255,255,255,0.1);border-radius:4px;overflow:hidden;">
  <div style="height:100%;width:{pct}%;background:{src_colors[src]};border-radius:4px;transition:width 1s ease;"></div>
</div>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# FEATURE 8: SMART ALERT TIMELINE
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🔔 Smart Alert Timeline</div>", unsafe_allow_html=True)

now_str = datetime.now().strftime("%I:%M %p")
current_alerts = []
if data['pH'] < 6.5 or data['pH'] > 8.5:
    current_alerts.append(("pH", f"pH {data['pH']} out of safe range (6.5–8.5)", "danger", now_str))
if data['turbidity'] > 4:
    current_alerts.append(("Turbidity", f"Turbidity {data['turbidity']} NTU exceeds 4 NTU limit", "danger" if data['turbidity'] > 6 else "warn", now_str))
if data['tds'] > 300:
    current_alerts.append(("TDS", f"TDS {data['tds']} mg/L above 300 mg/L threshold", "danger" if data['tds'] > 500 else "warn", now_str))
if data['dissolved_oxygen'] < 6:
    current_alerts.append(("DO", f"Dissolved oxygen {data['dissolved_oxygen']} mg/L below 6 mg/L", "warn", now_str))

for alert in current_alerts:
    if alert not in st.session_state.alert_timeline:
        st.session_state.alert_timeline.insert(0, alert)

st.session_state.alert_timeline = st.session_state.alert_timeline[:10]

if st.session_state.alert_timeline:
    for param, msg, level, t in st.session_state.alert_timeline:
        icon = "🚨" if level == "danger" else "⚠️"
        color = "#f44336" if level == "danger" else "#ff9800"
        st.markdown(f"""
        <div class="timeline-item">
        <div style="min-width:60px;color:rgba(255,255,255,0.4);font-size:0.8rem;padding-top:2px;">{t}</div>
        <div style="color:{color};font-size:1.2rem;">{icon}</div>
        <div>
          <div style="font-weight:600;color:{color};">{param}</div>
          <div style="color:rgba(255,255,255,0.7);font-size:0.85rem;">{msg}</div>
        </div>
        </div>
        """, unsafe_allow_html=True)
    if st.button("🗑️ Clear Timeline"):
        st.session_state.alert_timeline = []
        st.rerun()
else:
    st.markdown("""
    <div style="text-align:center;padding:20px;color:rgba(76,175,80,0.8);">
    <div style="font-size:2rem;">✅</div>
    <div>All Clear — No active alerts</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# FAMILY SAFETY MODE
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🧒 Family Safety Mode</div>", unsafe_allow_html=True)
grp = st.multiselect("Select family members to check safety:", ["👶 Infant", "🤰 Pregnant", "👴 Elderly", "🧑 Adult"])
fam_cols = st.columns(max(len(grp), 1))
for i, member in enumerate(grp):
    issues = []
    if "Infant" in member:
        if data['tds'] > 200: issues.append(f"TDS {data['tds']} too high (max 200 for infants)")
        if data['pH'] < 7.0 or data['pH'] > 8.0: issues.append("pH slightly off for infants")
    elif "Pregnant" in member:
        if data['tds'] > 300: issues.append(f"TDS {data['tds']} elevated")
        if data['turbidity'] > 2: issues.append("Turbidity risk for pregnancy")
    elif "Elderly" in member:
        if data['tds'] > 400: issues.append("High TDS risk for elderly kidneys")
    else:
        if data['tds'] > 500: issues.append("Very high TDS")

    safe = len(issues) == 0
    color = "#4caf50" if safe else "#f44336"
    fam_cols[i].markdown(f"""
    <div class="glass" style="border-color:{color}44;text-align:center;">
    <div style="font-size:1.8rem;">{member.split()[0]}</div>
    <div style="color:{color};font-weight:600;margin:6px 0;">{'✅ Safe' if safe else '❌ Not Safe'}</div>
    {''.join([f'<div style="font-size:0.8rem;color:rgba(255,255,255,0.6);">• {issue}</div>' for issue in issues]) if issues else '<div style="font-size:0.8rem;color:rgba(76,175,80,0.7);">All parameters OK</div>'}
    </div>
    """, unsafe_allow_html=True)

# =========================
# SHOULD I DRINK BUTTON
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>💧 Drink Decision</div>", unsafe_allow_html=True)
st.markdown('<div class="big-drink">', unsafe_allow_html=True)
if st.button("💧 SHOULD I DRINK THIS WATER?", use_container_width=True):
    if score > 80:
        st.success(f"✅ YES — Water is safe to drink in {city}. WQI: {score}")
    elif score > 50:
        st.warning(f"⚠️ FILTER FIRST — Moderate quality. Use RO/UV filter before drinking. WQI: {score}")
    else:
        st.error(f"❌ NO — Water is unsafe. Avoid drinking. Use bottled or treated water. WQI: {score}")
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# WATER FINGERPRINT
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🫧 Water Fingerprint</div>", unsafe_allow_html=True)
components.html(f"""
<style>body{{margin:0;background:transparent;font-family:'Exo 2',sans-serif;color:white;}}</style>
<div style="background:rgba(255,255,255,0.05);border-radius:16px;padding:16px;border:1px solid rgba(0,198,255,0.2);display:flex;gap:16px;align-items:center;">
<canvas id="fp" width="200" height="200" style="border-radius:50%;border:2px solid rgba(0,198,255,0.3);"></canvas>
<div>
  <div style="font-size:1.2rem;font-weight:700;color:#00c6ff;">{city} Water Identity</div>
  <div style="color:rgba(255,255,255,0.6);font-size:0.85rem;margin-top:4px;">{datetime.now().strftime('%d %b %Y')}</div>
  <div style="margin-top:12px;font-size:0.85rem;color:rgba(255,255,255,0.7);">pH: {data['pH']} · TDS: {data['tds']} · Turb: {data['turbidity']}</div>
  <div style="font-size:0.85rem;color:rgba(255,255,255,0.7);">DO: {data['dissolved_oxygen']} · WQI: {score}</div>
  <div style="margin-top:8px;padding:4px 12px;border-radius:20px;display:inline-block;font-size:0.8rem;background:rgba(0,198,255,0.15);border:1px solid rgba(0,198,255,0.4);color:#00c6ff;">Unique ID: WF-{abs(hash(city+str(score)))%99999:05d}</div>
</div>
</div>
<script>
const c=document.getElementById("fp");
const ctx=c.getContext("2d");
ctx.fillStyle="rgba(10,22,40,0.8)";ctx.fillRect(0,0,200,200);
const seed=[{data['pH']},{data['tds']},{data['turbidity']},{data['dissolved_oxygen']}];
for(let i=0;i<60;i++){{
  ctx.beginPath();
  const r=seed[i%4]*3%80+10;
  const x=100+r*Math.cos(i*0.5+seed[0]);
  const y=100+r*Math.sin(i*0.5+seed[1]/100);
  ctx.arc(x,y,seed[2]%5+2,0,Math.PI*2);
  ctx.strokeStyle=`hsla(${{(seed[i%4]*30+i*6)%360}},80%,60%,0.6)`;
  ctx.lineWidth=1.5;ctx.stroke();
}}
for(let i=0;i<8;i++){{
  ctx.beginPath();
  ctx.arc(100,100,20+i*12,seed[0]/10,seed[1]/50);
  ctx.strokeStyle=`hsla(${{i*45}},70%,60%,0.3)`;
  ctx.lineWidth=1;ctx.stroke();
}}
</script>
""", height=240)

# =========================
# CHART
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>📈 Water Quality Trends</div>", unsafe_allow_html=True)
hist_data = [{"tds": data['tds'] + (i-5)*8, "ph": data['pH'] + (i-5)*0.05, "turbidity": data['turbidity'] + (i-5)*0.3} for i in range(11)]
components.html(f"""
<canvas id="chart" height="120"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
new Chart(document.getElementById("chart"),{{
type:'line',
data:{{
  labels:{[f'Day {i-5}' if i!=5 else 'Today' for i in range(11)]},
  datasets:[
    {{label:'TDS',data:{[round(d['tds'],1) for d in hist_data]},borderColor:'#00c6ff',yAxisID:'y',tension:0.4,fill:true,backgroundColor:'rgba(0,198,255,0.05)'}},
    {{label:'pH',data:{[round(d['ph'],2) for d in hist_data]},borderColor:'#4caf50',yAxisID:'y1',tension:0.4}},
    {{label:'Turbidity',data:{[round(d['turbidity'],2) for d in hist_data]},borderColor:'#ff9800',yAxisID:'y1',tension:0.4}}
  ]
}},
options:{{
  animation:{{duration:1500,easing:'easeInOutQuart'}},
  plugins:{{legend:{{labels:{{color:'rgba(255,255,255,0.8)'}}}}}},
  scales:{{
    x:{{ticks:{{color:'rgba(255,255,255,0.5)'}},grid:{{color:'rgba(255,255,255,0.05)'}}}},
    y:{{position:'left',ticks:{{color:'#00c6ff'}},grid:{{color:'rgba(255,255,255,0.05)'}},title:{{display:true,text:'TDS mg/L',color:'#00c6ff'}}}},
    y1:{{position:'right',ticks:{{color:'#4caf50'}},grid:{{display:false}},title:{{display:true,text:'pH / Turbidity',color:'#4caf50'}}}}
  }}
}}
}});
</script>
""", height=320)

# =========================
# MAP
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>🗺️ City Water Quality Map</div>", unsafe_allow_html=True)
map_lat = lat if lat else 16.5
map_lon = lon if lon else 80.6
map_color = "green" if score > 80 else "orange" if score > 50 else "red"

components.html(f"""
<div id="map" style="height:400px;border-radius:16px;overflow:hidden;"></div>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
var map=L.map('map').setView([{map_lat},{map_lon}],8);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{attribution:'© OpenStreetMap'}}).addTo(map);
var circle=L.circleMarker([{map_lat},{map_lon}],{{color:'{map_color}',fillColor:'{map_color}',fillOpacity:0.7,radius:16,weight:2}})
.addTo(map).bindPopup('<b>📍 {city}</b><br>WQI: {score}<br>pH: {data["pH"]}<br>TDS: {data["tds"]}<br>Status: {result}').openPopup();
// Ripple animation
function ripple(){{
  var r=L.circleMarker([{map_lat},{map_lon}],{{color:'{map_color}',fillColor:'transparent',radius:16,weight:2,opacity:1}}).addTo(map);
  var s=16;var op=1;
  var t=setInterval(function(){{s+=1;op-=0.05;r.setRadius(s);r.setStyle({{opacity:op}});if(op<=0){{map.removeLayer(r);clearInterval(t);ripple();}}}},50);
}}
ripple();
</script>
""", height=420)

# =========================
# TIME CAPSULE
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>💾 Water Quality Time Capsule</div>", unsafe_allow_html=True)
tc1, tc2 = st.columns([1, 2])
with tc1:
    if st.button("💾 Save Snapshot", use_container_width=True):
        snap = {"city": city, "wqi": score, "status": result, "ph": data['pH'],
                "tds": data['tds'], "turbidity": data['turbidity'], "do": data['dissolved_oxygen'],
                "time": datetime.now().strftime("%d %b %Y %I:%M %p")}
        st.session_state.snapshots.insert(0, snap)
        st.session_state.snapshots = st.session_state.snapshots[:5]
        st.success("Snapshot saved!")

with tc2:
    if st.session_state.snapshots:
        for i, snap in enumerate(st.session_state.snapshots):
            prev_wqi = st.session_state.snapshots[i+1]['wqi'] if i+1 < len(st.session_state.snapshots) else snap['wqi']
            arrow = "↑" if snap['wqi'] > prev_wqi else "↓" if snap['wqi'] < prev_wqi else "→"
            arrow_color = "#4caf50" if snap['wqi'] > prev_wqi else "#f44336" if snap['wqi'] < prev_wqi else "#888"
            c = "#4caf50" if snap['wqi'] > 80 else "#ff9800" if snap['wqi'] > 50 else "#f44336"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;padding:8px 12px;background:rgba(255,255,255,0.04);border-radius:10px;margin-bottom:6px;border:1px solid rgba(255,255,255,0.07);">
            <div style="color:{c};font-family:'Orbitron',monospace;font-weight:700;min-width:40px;">{snap['wqi']}</div>
            <div style="color:{arrow_color};font-size:1.2rem;">{arrow}</div>
            <div style="flex:1;font-size:0.85rem;color:rgba(255,255,255,0.7);">{snap['city']} · pH {snap['ph']} · TDS {snap['tds']}</div>
            <div style="font-size:0.75rem;color:rgba(255,255,255,0.4);">{snap['time']}</div>
            </div>
            """, unsafe_allow_html=True)

# =========================
# PDF REPORT
# =========================
st.markdown("<div class='section-title' style='margin-top:20px;'>📄 Download Report</div>", unsafe_allow_html=True)

def generate_pdf():
    f = "water_report.pdf"
    doc = SimpleDocTemplate(f)
    styles = getSampleStyleSheet()
    content = [
        Paragraph("💧 QuXAT Water Quality Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"City: {city} | Date: {datetime.now().strftime('%d %b %Y %I:%M %p')}", styles["Normal"]),
        Spacer(1, 8),
        Paragraph(f"WQI Score: {score} — {result}", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph("Water Parameters:", styles["Heading3"]),
    ]
    table_data = [["Parameter", "Value", "Safe Range", "Status"],
                  ["pH", str(data['pH']), "6.5–8.5", "✓" if 6.5 <= data['pH'] <= 8.5 else "✗"],
                  ["TDS", f"{data['tds']} mg/L", "< 300 mg/L", "✓" if data['tds'] <= 300 else "✗"],
                  ["Turbidity", f"{data['turbidity']} NTU", "< 4 NTU", "✓" if data['turbidity'] <= 4 else "✗"],
                  ["Dissolved O₂", f"{data['dissolved_oxygen']} mg/L", "> 6 mg/L", "✓" if data['dissolved_oxygen'] >= 6 else "✗"]]
    t = Table(table_data)
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d2137')),
                           ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                           ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    content += [t, Spacer(1, 12), Paragraph(f"Story: {story_text}", styles["Normal"])]
    doc.build(content)
    return f

r1, r2 = st.columns(2)
with r1:
    with open(generate_pdf(), "rb") as f:
        st.download_button("📥 Download PDF Report", f, file_name=f"QuXAT_{city}_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)
with r2:
    wa_msg = f"💧 Water Quality Update for {city}%0AWQI: {score} ({result})%0ApH: {data['pH']} | TDS: {data['tds']} | Turbidity: {data['turbidity']}%0A{advice.get(result, '')}"
    st.markdown(f'<a href="https://wa.me/?text={wa_msg}" target="_blank"><button style="width:100%;background:linear-gradient(135deg,#25d366,#128c7e);color:white;border:none;padding:10px;border-radius:10px;cursor:pointer;font-size:0.9rem;font-family:Exo 2,sans-serif;font-weight:600;">📲 Share on WhatsApp</button></a>', unsafe_allow_html=True)

# =========================
# REFRESH
# =========================
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 Refresh Data", use_container_width=True):
    st.rerun()

st.markdown("""
<div style="text-align:center;padding:20px;color:rgba(255,255,255,0.3);font-size:0.8rem;border-top:1px solid rgba(255,255,255,0.07);margin-top:20px;">
💧 QuXAT Hydro Dashboard · Water Quality Intelligence Platform · Data refreshes on each load
</div>
""", unsafe_allow_html=True)