import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)
from RegisterPage import RegisterWindow
from network import send_request, open_connection, close_connection
from ProfilePage import ProfilePage
from Person import Person
import json

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AUBus - Login")
        self.setGeometry(300, 300, 350, 250)
        self.sessions = []  # keep track of open profile windows

        layout = QVBoxLayout()

        self.label = QLabel("Login to your account")
        layout.addWidget(self.label)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login_user)
        layout.addWidget(login_btn)

        register_btn = QPushButton("Create Account")
        register_btn.clicked.connect(self.open_register)
        layout.addWidget(register_btn)

        self.setLayout(layout)

    def login_user(self):
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Missing Info", "Please fill in all fields.")
            return
        
        message = f"login:{username}:{password}"
        s = open_connection()
        response = send_request(s, message)
        close_connection(s)

        if response.startswith("error:"):
            error_msg = response.split(":", 1)[1] if ":" in response else "Login failed."
            QMessageBox.critical(self, "Login Failed", error_msg)
            return

        if not response.startswith("success:"):
            QMessageBox.critical(self, "Login Failed", "Unexpected server response.")
            return

        payload_raw = response.split(":", 1)[1]
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Login Failed", "Invalid data returned from server.")
            return

        user = Person()
        user.username = username
        user.full_name = payload.get("name") or username
        user.email = payload.get("email", "")
        user.area = payload.get("area", "")
        user.is_driver = 1 if payload.get("is_driver") else 0
        user.min_passenger_rating = float(payload.get("min_passenger_rating", 0.0))
        user.passenger_rating = float(payload.get("passenger_rating", 0.0))
        user.driver_rating = float(payload.get("driver_rating", 0.0))
        user.pending_requests = payload.get("pending_requests", [])
        user.availability = payload.get("availability", {})
        user.active_rides = payload.get("active_rides", [])
        user.completed_rides = payload.get("completed_rides", [])

        profile_window = ProfilePage(user, login_window=self)
        profile_window.show()
        self.sessions.append(profile_window)
        self.username.clear()
        self.password.clear()

    def session_closed(self, profile_window):
        if profile_window in self.sessions:
            self.sessions.remove(profile_window)

    def open_register(self):
        self.hide()
        self.register_window = RegisterWindow()
        self.register_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec_())
