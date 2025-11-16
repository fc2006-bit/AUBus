from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QCheckBox, QGridLayout
from PyQt5.QtCore import Qt
from network import open_connection, send_request, close_connection  # Add these imports

class DriverDashboardPage(QWidget):
    def __init__(self, person):
        super().__init__()
        self.person=person

        title = QLabel("Driver Dashboard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        info_label = QLabel("Select the days you drive to AUB and enter times (24 hour format) for each day:")
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
                if availability[day]['from']:
                    widgets["check"].setChecked(True)
                    widgets["from"].setText(availability[day].get("from", ""))
                if availability[day]['to']:
                    widgets["check"].setChecked(True)
                    widgets["to"].setText(availability[day].get("to", ""))

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
        days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        availability_list = []

        for day in days_order:
            widgets = self.schedule[day]

            if widgets["check"].isChecked():
                from_time = widgets["from"].text().replace(":", ".")
                to_time = widgets["to"].text().replace(":", ".")

                # Make sure times exist if the day is checked
                if not from_time and not to_time:
                    QMessageBox.warning(self, "Error", f"Please enter a time for {day}.")
                    return

                availability_list.append(f"{from_time}-{to_time}")
            else:
                availability_list.append("")  # empty slot allowed

        # Convert list to semicolon-separated string
        availability_str = ";".join(availability_list)

        # Save minimum rating
        self.person.min_rating = self.min_rating.text()

        # Build server message
        availability_message = (
            f"update_availability:{self.person.username}:{availability_str}:{self.person.min_rating}"
        )

        # Send to server
        s = open_connection()
        response = send_request(s, availability_message)
        close_connection(s)

        QMessageBox.information(self, "Availability Update", response)
