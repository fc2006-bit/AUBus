from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt
import json
from network import open_connection, send_request, close_connection
from RatingPage import RatingPage
from ChatWindow import ChatWindow

def api_get_pending(driver_username):
    conn = open_connection()
    if not conn:
        return [], "Unable to connect to server."

    resp = send_request(conn, f"get_pending:{driver_username}")
    close_connection(conn)

    if not resp:
        return [], "Empty server response."

    if resp.startswith("success:"):
        payload = resp.split(":", 1)[1]
        try:
            return json.loads(payload or "[]"), None
        except json.JSONDecodeError:
            return [], "Malformed data returned from server."

    if resp.startswith("error:"):
        return [], resp.split(":", 1)[1] or "Server returned an error."

    return [], resp


def api_delete_request(driver, index):
    conn = open_connection()
    if not conn:
        return "Unable to connect to server."
    response = send_request(conn, f"delete_request:{driver}:{index}")
    close_connection(conn)
    return response or "No server response."


def api_accept_request(driver, request_id):
    conn = open_connection()
    if not conn:
        return "Unable to connect to server."
    response = send_request(conn, f"accept_request:{driver}:{request_id}")
    close_connection(conn)
    return response or "No server response."


def api_end_request(driver, request_id):
    conn = open_connection()
    if not conn:
        return "Unable to connect to server."
    response = send_request(conn, f"end_request:{driver}:{request_id}")
    close_connection(conn)
    return response or "No server response."


def api_rate_passenger(passenger_username, rating):
    conn = open_connection()
    if not conn:
        return "Unable to connect to server."
    response = send_request(conn, f"rate_passenger:{passenger_username}:{rating}")
    close_connection(conn)
    return response or "No server response."


class PendingRequestsPage(QWidget):
    def __init__(self, driver_username, driver_name=None):
        super().__init__()

        self.driver_username = driver_username
        self.driver_name = driver_name or driver_username
        self.requests = []
        self.request_rows = []
        self.chat_windows = []

        main_layout = QVBoxLayout()

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_rows)
        top_bar.addWidget(btn_refresh)
        main_layout.addLayout(top_bar)

        title = QLabel(f"Pending Ride Requests for {self.driver_name}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self._header_label("Passenger"))
        header_layout.addWidget(self._header_label("Day"))
        header_layout.addWidget(self._header_label("Time"))
        header_layout.addWidget(self._header_label("Area"))
        header_layout.addWidget(self._header_label("Min Rating"))
        header_layout.addWidget(self._header_label("Actions"))
        main_layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        self.rows_layout = QVBoxLayout()
        main_layout.addLayout(self.rows_layout)

        main_layout.addStretch(1)
        self.setLayout(main_layout)

        self.refresh_rows()

    def _header_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold;")
        return lbl

    def clear_rows(self):
        for row in self.request_rows:
            row.hide()
            row.setParent(None)
        self.request_rows = []

    def refresh_rows(self):
        self.clear_rows()
        self.requests, error = api_get_pending(self.driver_username)

        if error:
            err_lbl = QLabel(f"Failed to load requests: {error}")
            err_lbl.setStyleSheet("color: red;")
            self.rows_layout.addWidget(err_lbl)
            self.request_rows.append(err_lbl)
            return

        if not self.requests:
            no_lbl = QLabel("No pending requests.")
            self.rows_layout.addWidget(no_lbl)
            self.request_rows.append(no_lbl)
            return

        for idx, req in enumerate(self.requests):
            row_widget = self.build_row(req, idx)
            self.rows_layout.addWidget(row_widget)
            self.request_rows.append(row_widget)

    def build_row(self, req, index):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        passenger_username = req.get("passenger", "Unknown")
        passenger_display = req.get("passenger_name") or passenger_username
        day = req.get("day", "").replace("_commute", "").title() or "N/A"
        area = req.get("area", "N/A")
        ride_time = req.get("time", "N/A")
        min_rating = req.get("min_rating", req.get("min_passenger_rating", "N/A"))
        request_id = req.get("id") or req.get("request_id")
        status = req.get("status", "pending")

        layout.addWidget(QLabel(passenger_display))
        layout.addWidget(QLabel(day))
        layout.addWidget(QLabel(ride_time))
        layout.addWidget(QLabel(area))
        layout.addWidget(QLabel(str(min_rating)))

        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)

        if status == "active":
            btn_end = QPushButton("End Ride")
            btn_end.request_id = request_id
            btn_end.request_data = req
            btn_end.clicked.connect(self.end_request)
            action_layout.addWidget(btn_end)

            btn_message = QPushButton("Message")
            btn_message.chat_info = {
                "ride_id": request_id,
                "other_user": passenger_username,
                "other_name": passenger_display,
            }
            btn_message.clicked.connect(self.open_chat)
            action_layout.addWidget(btn_message)
        else:
            btn_accept = QPushButton("Accept")
            btn_accept.request_id = request_id
            btn_accept.request_index = index
            btn_accept.clicked.connect(self.accept_request)
            action_layout.addWidget(btn_accept)

            btn_remove = QPushButton("Remove")
            btn_remove.request_index = index
            btn_remove.clicked.connect(self.remove_request)
            action_layout.addWidget(btn_remove)

        layout.addWidget(action_container)
        return row

    def accept_request(self):
        sender = self.sender()
        request_id = getattr(sender, "request_id", None)
        if request_id:
            api_accept_request(self.driver_username, request_id)
        else:
            index = getattr(sender, "request_index", None)
            if index is None:
                return
            api_delete_request(self.driver_username, index)
        self.refresh_rows()

    def end_request(self):
        sender = self.sender()
        request_id = getattr(sender, "request_id", None)
        req = getattr(sender, "request_data", None)
        if not request_id or not req:
            return
        passenger = req.get("passenger")
        passenger_display = req.get("passenger_name") or passenger or "passenger"
        api_end_request(self.driver_username, request_id)

        def submit_rating(value, passenger=passenger):
            if passenger:
                api_rate_passenger(passenger, value)

        prompt = f"Rate passenger {passenger_display}" if passenger_display else "Rate passenger"
        self.rating_page = RatingPage(prompt=prompt, on_submit=submit_rating)
        self.rating_page.show()
        self.refresh_rows()

    def open_chat(self):
        info = getattr(self.sender(), "chat_info", None)
        if not info or not info.get("ride_id") or not info.get("other_user"):
            return
        chat = ChatWindow(
            info["ride_id"],
            self.driver_username,
            info["other_user"],
            other_user_name=info.get("other_name"),
        )
        chat.show()
        self.chat_windows.append(chat)

    def remove_request(self):
        index = getattr(self.sender(), "request_index", None)
        if index is None:
            return
        api_delete_request(self.driver_username, index)
        self.refresh_rows()
