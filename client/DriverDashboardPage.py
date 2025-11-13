from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox, QCalendarWidget
from PyQt5.QtCore import Qt, QDate

class DriverDashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Driver Dashboard")

        title = QLabel("Driver Dashboard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        calendar_label = QLabel("Select the days you go to AUB:")
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMinimumDate(QDate.currentDate())

        self.selected_date_label = QLabel("Selected date: None")
        self.calendar.selectionChanged.connect(self.update_selected_date)

        form = QFormLayout()
        self.departure_time = QLineEdit()
        self.return_time = QLineEdit()
        self.min_rating = QLineEdit()

        form.addRow("Departure time (to AUB):", self.departure_time)
        form.addRow("Return time (from AUB):", self.return_time)
        form.addRow("Minimum passenger rating:", self.min_rating)

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
        layout.addWidget(calendar_label)
        layout.addWidget(self.calendar)
        layout.addWidget(self.selected_date_label)
        layout.addLayout(form)
        layout.addSpacing(10)
        layout.addLayout(buttons)
        layout.addStretch(1)
        self.setLayout(layout)

    def update_selected_date(self):
        date = self.calendar.selectedDate().toString("dddd, MMMM d, yyyy")
        self.selected_date_label.setText(f"Selected date: {date}")

    def save_availability(self):
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        dep = self.departure_time.text().strip()
        ret = self.return_time.text().strip()
        rating = self.min_rating.text().strip()

        QMessageBox.information(
            self,
            "Saved",
            f"Availability saved for {date}\n"
            f"Departure: {dep}\nReturn: {ret}\nMin rating: {rating}\n\n"
            "(Backend connection pending.)"
        )