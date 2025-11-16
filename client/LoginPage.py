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
        parts = response.split(":", 9)
        if parts[0] == "success":
            self.hide()
            user = Person()
            user.username = username
            user.full_name = parts[1]
            user.email = parts[2]
            user.area = parts[3]
            user.is_driver = bool(int(parts[4]))
            self.min_passenger_rating = float(parts[5])
            user.passenger_rating = float(parts[6])
            user.driver_rating = float(parts[7])
            user.pending_requests = parts[8].split(",") if parts[8] else []
            availability_raw = parts[9]
            availability_parts = []
            current = ""
            brackets = 0
            for char in availability_raw:
                if char == ":" and brackets == 0:
                    availability_parts.append(current)
                    current = ""
                else:
                    current += char
                
                if char == '{':
                    brackets += 1
                elif char == '}':
                    brackets -= 1
            availability_parts.append(current)

            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            availability = {}

            for day, part in zip(days, availability_parts[-7:]):  
                part = part.strip()
                if part == "[]":
                    availability[day] = {"from": None, "to": None}
                else:
                    availability[day] = json.loads(part)
            user.availability = availability
            self.profile_window = ProfilePage(user)
            self.profile_window.show()
        else:
            QMessageBox.critical(self, "Login Failed", parts[1])

    def open_register(self):
        self.hide()
        self.register_window = RegisterWindow()
        self.register_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec_())
