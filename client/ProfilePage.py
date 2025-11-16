import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)
from RegisterPage import RegisterWindow
from network import send_request, open_connection, close_connection
from ProfilePage import ProfilePage
from Person import Person
from WeatherPage import WeatherPage

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

        weather_btn = QPushButton("Weather")
        weather_btn.clicked.connect(self.open_weather)
        layout.addWidget(weather_btn)

        self.setLayout(layout)

    def login_user(self):
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Missing Info", "Please fill in all fields.")
            return
        
        message = f"login:{username}:{password}"
        s = open_connection()
        response = send_request(s,message)
        close_connection(s)
        parts = response.split(":")
        if parts[0] == "success":
            self.hide()
            user = Person()
            user.username = username
            user.full_name = parts[1]
            user.email = parts[2]
            user.area = parts[3]
            user.is_driver = bool(int(parts[4]))
            self.profile_window = ProfilePage(user)
            self.profile_window.show()
        else:
            QMessageBox.critical(self, "Login Failed", parts[1])

    def open_register(self):
        self.hide()
        self.register_window = RegisterWindow()
        self.register_window.show()

    def open_weather(self):
        self.hide()
        self.weather_window = WeatherPage()
        self.weather_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec_())
