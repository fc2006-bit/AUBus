from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit


class RatingPage(QWidget):
    def __init__(self, prompt="Enter Rating (0 to 5):", on_submit=None):
        super().__init__()

        self.rating = 0
        self.on_submit = on_submit

        title = QLabel(prompt)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("e.g. 4.5")

        submit = QPushButton("Submit")
        submit.clicked.connect(self.submit_rating)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.input_field)
        layout.addWidget(submit)

        self.setLayout(layout)
        self.setFixedSize(260, 140)

    def submit_rating(self):
        text = self.input_field.text()
        try:
            value = float(text)
        except ValueError:
            print("Invalid rating. Must be a number.")
            return
        if value < 0 or value > 5:
            print("Rating must be between 0 and 5.")
            return
        self.rating = value
        if self.on_submit:
            self.on_submit(self.rating)
        self.close()
