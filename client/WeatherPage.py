import sys
from datetime import datetime
from typing import Optional

import requests
from PyQt5.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from LoginPage import LoginWindow


WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherPage(QWidget):
    """Weather landing page for Lebanon with AUB (Beirut) highlights."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AUBus - Lebanon Weather")
        self.resize(420, 600)

        main_layout = QVBoxLayout()

        header = QLabel("Check current weather and forecasts across Lebanon")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(header)

        # Area search controls
        search_row = QHBoxLayout()
        self.area_input = QLineEdit()
        self.area_input.setPlaceholderText("Enter your area (e.g., Hamra, Tripoli)")
        search_row.addWidget(self.area_input)

        search_button = QPushButton("Find Weather")
        search_button.clicked.connect(self.search_area_weather)
        search_row.addWidget(search_button)

        main_layout.addLayout(search_row)

        # Current weather panel
        current_group = QGroupBox("Current weather")
        current_layout = QFormLayout()
        self.location_label = QLabel("—")
        self.temperature_label = QLabel("—")
        self.description_label = QLabel("—")
        current_layout.addRow("Location:", self.location_label)
        current_layout.addRow("Temperature:", self.temperature_label)
        current_layout.addRow("Sky:", self.description_label)
        current_group.setLayout(current_layout)
        main_layout.addWidget(current_group)

        # Forecast list
        forecast_group = QGroupBox("Upcoming forecast (next days)")
        forecast_layout = QVBoxLayout()
        self.forecast_list = QListWidget()
        forecast_layout.addWidget(self.forecast_list)
        forecast_group.setLayout(forecast_layout)
        main_layout.addWidget(forecast_group)

        # AUB (Beirut) highlight
        aub_group = QGroupBox("American University of Beirut (Beirut) weather")
        aub_layout = QFormLayout()
        self.aub_temp_label = QLabel("—")
        self.aub_description_label = QLabel("—")
        aub_layout.addRow("Temperature:", self.aub_temp_label)
        aub_layout.addRow("Sky:", self.aub_description_label)
        aub_group.setLayout(aub_layout)
        main_layout.addWidget(aub_group)

        # Navigation to login
        action_row = QHBoxLayout()
        action_row.addStretch()
        login_button = QPushButton("Go to Login")
        login_button.clicked.connect(self.open_login)
        action_row.addWidget(login_button)
        main_layout.addLayout(action_row)

        self.setLayout(main_layout)

        self.load_aub_weather()

    def open_login(self):
        self.login_window = LoginWindow()
        self.login_window.show()
        self.hide()

    def search_area_weather(self):
        query = self.area_input.text().strip()
        if not query:
            QMessageBox.information(self, "Missing area", "Please enter an area in Lebanon.")
            return

        location = self.geocode_location(query)
        if not location:
            QMessageBox.warning(
                self,
                "Location not found",
                "Could not find that area in Lebanon. Please try another nearby spot.",
            )
            return

        weather = self.fetch_weather(location["latitude"], location["longitude"], location["name"])
        if weather:
            self.update_current_weather(weather)
            self.populate_forecast(weather)

    def geocode_location(self, area: str) -> Optional[dict]:
        try:
            response = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": area, "count": 1, "language": "en", "format": "json", "country": "LB"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("results"):
                return None
            return data["results"][0]
        except requests.RequestException:
            QMessageBox.critical(self, "Network error", "Unable to reach the weather service right now.")
            return None

    def fetch_weather(self, latitude: float, longitude: float, name: str) -> Optional[dict]:
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current_weather": True,
                    "hourly": "temperature_2m,weathercode",
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            data["resolved_name"] = name
            return data
        except requests.RequestException:
            QMessageBox.critical(self, "Network error", "Unable to retrieve weather data.")
            return None

    def load_aub_weather(self):
        # Coordinates approximated for AUB campus in Beirut.
        aub_latitude = 33.9023
        aub_longitude = 35.4801
        aub_data = self.fetch_weather(aub_latitude, aub_longitude, "AUB (Beirut)")
        if aub_data and aub_data.get("current_weather"):
            current = aub_data["current_weather"]
            description = WEATHER_CODE_DESCRIPTIONS.get(current.get("weathercode"), "—")
            self.aub_temp_label.setText(f"{current.get('temperature', '—')}°C")
            self.aub_description_label.setText(description)
        else:
            self.aub_temp_label.setText("Unavailable")
            self.aub_description_label.setText("—")

    def update_current_weather(self, weather: dict):
        current = weather.get("current_weather", {})
        description = WEATHER_CODE_DESCRIPTIONS.get(current.get("weathercode"), "—")
        self.location_label.setText(weather.get("resolved_name", "—"))
        self.temperature_label.setText(f"{current.get('temperature', '—')}°C")
        self.description_label.setText(description)

    def populate_forecast(self, weather: dict):
        self.forecast_list.clear()
        daily = weather.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        codes = daily.get("weathercode", [])

        for index, date_str in enumerate(dates):
            date_label = self._format_date(date_str)
            summary = WEATHER_CODE_DESCRIPTIONS.get(codes[index], "—") if index < len(codes) else "—"
            max_temp = max_temps[index] if index < len(max_temps) else "—"
            min_temp = min_temps[index] if index < len(min_temps) else "—"
            item_text = f"{date_label}: {summary} (Min {min_temp}°C / Max {max_temp}°C)"
            QListWidgetItem(item_text, self.forecast_list)

    @staticmethod
    def _format_date(date_str: str) -> str:
        try:
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime("%a, %b %d")
        except ValueError:
            return date_str
