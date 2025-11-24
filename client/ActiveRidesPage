from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt
import json
from network import open_connection, send_request, close_connection
from RatingPage import RatingPage
from ChatWindow import ChatWindow


def _fetch_rides(command, passenger_username):
    conn = open_connection()
    if not conn:
        return [], "Unable to connect to server."

    resp = send_request(conn, f"{command}:{passenger_username}")
    close_connection(conn)

    if not resp:
        return [], "Empty server response."

    if resp.startswith("success:"):
        payload = resp.split(":", 1)[1]
        try:
            return json.loads(payload or "[]"), None
        except json.JSONDecodeError:
            return [], "Malformed data from server."

    if resp.startswith("error:"):
        return [], resp.split(":", 1)[1] or "Server error."

    return [], resp


def api_get_all_rides(passenger_username):
    active, err = _fetch_rides("get_active_rides", passenger_username)
    if err:
        return [], err

    completed, err_completed = _fetch_rides("get_completed_rides", passenger_username)
    if err_completed:
        return active, f"Failed to load completed rides: {err_completed}"

    return active + completed, None


def api_rate_driver_ride(passenger_username, driver_username, request_id, rating):
    conn = open_connection()
    if not conn:
        return "Unable to connect to server."
    resp = send_request(conn, f"rate_driver_ride:{passenger_username}:{driver_username}:{request_id}:{rating}")
    close_connection(conn)
    return resp or "No server response."


class ActiveRidesPage(QWidget):
    def __init__(self, passenger_username):
        super().__init__()
        self.passenger_username = passenger_username
        self.rides = []
        self.rows = []
        self.chat_windows = []

        main_layout = QVBoxLayout()

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_rows)
        top_bar.addWidget(btn_refresh)
        main_layout.addLayout(top_bar)

        title = QLabel("Active Rides")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        header = QHBoxLayout()
        header.addWidget(self._header_label("Driver"))
        header.addWidget(self._header_label("Day"))
        header.addWidget(self._header_label("Time"))
        header.addWidget(self._header_label("Area"))
        header.addWidget(self._header_label("Actions"))
        main_layout.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        self.rows_layout = QVBoxLayout()
        main_layout.addLayout(self.rows_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)
        self.refresh_rows()

    def _header_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold;")
        return lbl

    def clear_rows(self):
        for row in self.rows:
            row.hide()
            row.setParent(None)
        self.rows = []

    def refresh_rows(self):
        self.clear_rows()
        self.rides, error = api_get_all_rides(self.passenger_username)

        if error:
            err = QLabel(f"Failed to load rides: {error}")
            err.setStyleSheet("color: red;")
            self.rows_layout.addWidget(err)
            self.rows.append(err)

        if not self.rides:
            empty = QLabel("No active rides.")
            self.rows_layout.addWidget(empty)
            self.rows.append(empty)
            return

        for ride in self.rides:
            row_widget = self.build_row(ride)
            self.rows_layout.addWidget(row_widget)
            self.rows.append(row_widget)

    def build_row(self, ride):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        driver = ride.get("driver", "Unknown")
        driver_name = ride.get("driver_name") or driver
        day = ride.get("day", "").replace("_commute", "").title() or "N/A"
        time = ride.get("time", "N/A")
        area = ride.get("area", "N/A")
        status = ride.get("status", "active")

        layout.addWidget(QLabel(driver_name))
        layout.addWidget(QLabel(day))
        layout.addWidget(QLabel(time))
        layout.addWidget(QLabel(area))

        if status == "completed":
            btn_rate = QPushButton("Rate")
            btn_rate.ride = ride
            btn_rate.clicked.connect(self.rate_driver)
            layout.addWidget(btn_rate)
        else:
            btn_message = QPushButton("Message")
            btn_message.chat_info = {
                "ride_id": ride.get("id"),
                "driver": driver,
                "driver_name": driver_name,
            }
            btn_message.clicked.connect(self.open_chat)
            layout.addWidget(btn_message)

        return row

    def rate_driver(self):
        ride = getattr(self.sender(), "ride", None)
        if not ride:
            return
        driver = ride.get("driver")
        driver_name = ride.get("driver_name") or driver
        request_id = ride.get("id")

        def submit_rating(value, driver=driver, request_id=request_id):
            if driver and request_id:
                api_rate_driver_ride(self.passenger_username, driver, request_id, value)
                self.refresh_rows()

        prompt = f"Rate driver {driver_name}" if driver_name else "Rate driver"
        self.rating_dialog = RatingPage(prompt=prompt, on_submit=submit_rating)
        self.rating_dialog.show()

    def open_chat(self):
        info = getattr(self.sender(), "chat_info", None)
        if not info or not info.get("ride_id") or not info.get("driver"):
            return
        chat = ChatWindow(
            info["ride_id"],
            self.passenger_username,
            info["driver"],
            other_user_name=info.get("driver_name"),
        )
        chat.show()
        self.chat_windows.append(chat)
