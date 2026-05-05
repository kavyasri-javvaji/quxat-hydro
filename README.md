# 💧 QuXAT Hydro Dashboard

A real-time Water Quality Intelligence Platform built with Python and Streamlit.

## 🌊 Features
- Real-time water quality monitoring for Indian cities
- WQI (Water Quality Index) scoring with weighted parameters
- Interactive water quality visualizer (Ripple Gauge + Liquid Tube + Hex Grid)
- Water Mood animated drop
- Activity checker (Drinking, Cooking, Bathing, Plants, Swimming)
- Water Purifier Recommender with cost estimates
- Contamination Source Classifier
- Virtual Water Tank visualization
- Smart Alert Timeline
- Family Safety Mode
- Safe Water Storage Calculator
- Water Story Generator
- 10-Day trend chart with dual axis
- Leaflet.js interactive map
- PDF Report download
- WhatsApp share

## 🔧 Tech Stack
- Python
- Streamlit
- OpenWeatherMap API
- Open-Meteo API
- Leaflet.js
- Chart.js
- ReportLab

## 📊 Water Parameters Monitored
- pH (6.5–8.5 safe range)
- Turbidity (< 4 NTU)
- TDS — Total Dissolved Solids (< 300 mg/L)
- Dissolved Oxygen (> 6 mg/L)

## 🚀 How to Run Locally
1. Clone the repository
2. Install dependencies: pip install -r requirements.txt
3. Add your API key in .env file: OPENWEATHER_API_KEY=your_key
4. Run: streamlit run app.py

## 🌐 Live Demo
[Click here to open the app](https://quxat-hydro.streamlit.app)

## 📁 Project Structure
QUXAT/
├── app.py
├── requirements.txt
├── data/
│   └── india_cities.csv
└── utils/
    ├── data_converter.py
    ├── location_api.py
    └── weather_api.py

## 👩‍💻 Developer
Kavya Sri Javvaji
