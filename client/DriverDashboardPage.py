from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QCheckBox, QGridLayout
from PyQt5.QtCore import Qt

class DriverDashboardPage(QWidget):
    def __init__(self, person):
        super().__init__()
        self.person=person

        title = QLabel("Driver Dashboard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        info_label = QLabel("Select the days you drive to AUB and enter times for each day:")
        info_label.setAlignment(Qt.AlignLeft)

        grid = QGridLayout()
        grid.addWidget(QLabel("Day"), 0, 0)
        grid.addWidget(QLabel("To AUB"), 0, 1)
        grid.addWidget(QLabel("From AUB"), 0, 2)

        self.schedule = {}

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        row = 1
        for day in days:
            check = QCheckBox(day)
            to_edit = QLineEdit()
            from_edit = QLineEdit()
            self.schedule[day] = {"check": check, "to": to_edit, "from": from_edit}
            grid.addWidget(check, row, 0)
            grid.addWidget(to_edit, row, 1)
            grid.addWidget(from_edit, row, 2)
            row+=1

        availability = self.person.availability
        for day, widgets in self.schedule.items():
            if day in availability:
                widgets["check"].setChecked(True)
                widgets["to"].setText(availability[day].get("to", ""))
                widgets["from"].setText(availability[day].get("from", ""))

        form = QFormLayout()
        self.min_rating = QLineEdit()
        form.addRow("Minimum passenger rating:", self.min_rating)

        self.min_rating.setText(str(self.person.min_passenger_rating))

        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save Availability")
        self.save_button.clicked.connect(self.save_availability)

        self.back_button = QPushButton("Back to Profile")
        self.back_button.clicked.connect(self.close)

        buttons.addStretch()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.back_button)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(info_label)
        layout.addLayout(grid)
        layout.addSpacing(10)
        layout.addLayout(form)
        layout.addSpacing(10)
        layout.addLayout(buttons)
        layout.addStretch(1)

        self.setLayout(layout)

    def save_availability(self):
        self.person.availability = {}

        for day, widgets in self.schedule.items():
            if widgets["check"].isChecked():
                to_time = widgets["to"].text()
                from_time = widgets["from"].text()
                self.person.availability[day] = {"to": to_time, "from": from_time}

        if not self.person.availability:
            QMessageBox.warning(self, "Error", "Please select at least one day and enter times.")
            return

        self.person.min_rating = self.min_rating.text()
