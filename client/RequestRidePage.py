import sys
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout, QFormLayout, QRadioButton, QMessageBox

class RequestRidePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Request Ride Page")
        layout = QVBoxLayout()

        self.to_button = QRadioButton("To AUB")
        self.from_button = QRadioButton("From AUB")
        self.to_button.setChecked(True)
        layout.addWidget(self.to_button)
        layout.addWidget(self.from_button)

        self.area_input = QLineEdit()
        self.minimum_rating = QLineEdit()
        form = QFormLayout()
        form.addRow("Area:", self.area_input)
        form.addRow("Minimum rating:", self.minimum_rating)
        layout.addLayout(form)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit_request)
        layout.addWidget(submit_button)

        self.setLayout(layout)

    def submit_request(self):
        QMessageBox.information(self, "Request Ride Page", "Request submitted. Waiting for driver.")