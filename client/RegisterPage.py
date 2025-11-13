from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QCheckBox
)
from network import send_request, open_connection, close_connection
from PyQt5.QtCore import pyqtSignal

class RegisterWindow(QWidget):
    back_to_login = pyqtSignal()  # optional, if you want to go back later

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AUBus - Register")
        self.setGeometry(300, 300, 350, 400)

        layout = QVBoxLayout()

        self.label = QLabel("Create a new account")
        layout.addWidget(self.label)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Full Name")
        layout.addWidget(self.name)

        self.email = QLineEdit()
        self.email.setPlaceholderText("Email")
        layout.addWidget(self.email)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)

        self.area = QLineEdit()
        self.area.setPlaceholderText("Area (optional)")
        layout.addWidget(self.area)

        self.is_driver = QCheckBox("I am a driver")
        layout.addWidget(self.is_driver)

        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.register_user)
        layout.addWidget(register_btn)

        back_btn = QPushButton("Back to Login")
        back_btn.clicked.connect(self.go_back)
        layout.addWidget(back_btn)

        self.setLayout(layout)

    def register_user(self):
        s = open_connection()
        username = self.username.text().strip()
        name = self.name.text().strip()
        email = self.email.text().strip()
        password = self.password.text().strip()
        area = self.area.text().strip() or "N/A"
        is_driver = 1 if self.is_driver.isChecked() else 0

        if not all([username, name, email, password]):
            QMessageBox.warning(self, "Missing Info", "Please fill in all required fields.")
            return

        message = f"register:{username}:{name}:{email}:{password}:{area}:{is_driver}"
        response = send_request(s,message)
        QMessageBox.information(self, "Server Response", response)

    def go_back(self):
        self.close()
        from LoginPage import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
