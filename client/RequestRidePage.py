import sys
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout, QFormLayout, QRadioButton, QMessageBox, QButtonGroup, QTimeEdit
from PyQt5.QtCore import QTime
from network import open_connection, send_request, close_connection

class RequestRidePage(QWidget):
    def __init__(self, person):
        super().__init__()
        self.setWindowTitle("Request Ride Page")
        layout = QVBoxLayout()

        self.to_button = QRadioButton("To AUB")
        self.from_button = QRadioButton("From AUB")
        self.to_button.setChecked(True)

        self.direction_group = QButtonGroup(self)
        self.direction_group.addButton(self.to_button)
        self.direction_group.addButton(self.from_button)

        layout.addWidget(self.to_button)
        layout.addWidget(self.from_button)

        self.area_input = QLineEdit()
        self.area_label = QLabel("")
        self.update_area_label()
        form1 = QFormLayout()
        form1.addRow(self.area_label, self.area_input)
        layout.addLayout(form1)

        self.to_button.clicked.connect(self.update_area_label)
        self.from_button.clicked.connect(self.update_area_label)

        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setTime(QTime.currentTime())
        form1.addRow("Time:", self.time_input)

        self.days_radio_buttons = {}
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for day in days:
            radio_button = QRadioButton(day)
            self.days_radio_buttons[day] = radio_button
            layout.addWidget(radio_button)
        
        self.minimum_rating = QLineEdit()
        form2 = QFormLayout()
        form2.addRow("Minimum rating:", self.minimum_rating)
        layout.addLayout(form2)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit_request)
        layout.addWidget(submit_button)

        self.setLayout(layout)

    def update_area_label(self):
        """Update the area label based on the selected direction."""
        if self.to_button.isChecked():
            self.area_label.setText("Area (To AUB):")
        else:
            self.area_label.setText("Area (From AUB):")

    def submit_request(self):
        selected_day = next((day for day, radio in self.days_radio_buttons.items() if radio.isChecked()), None)
        area = self.area_input.text().strip()
        min_rating = self.minimum_rating.text().strip()
        ride_time = self.time_input.time().toString("HH:mm")

        if not area or not min_rating or not selected_day:
            QMessageBox.warning(self, "Missing Info", "Please fill in all fields and select a day.")
            return

        s = open_connection()
        message = f"request_ride:{area}:{selected_day.lower()}:{ride_time}:{min_rating}"
        response = send_request(s, message)
        close_connection(s)
        QMessageBox.information(self, "Request Ride Page", "Request submitted. Waiting for driver.")
