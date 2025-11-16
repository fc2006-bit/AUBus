from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt

class PendingRequestsPage(QWidget):
    def __init__(self, requests):
        super().__init__()
        self.requests = requests
        self.request_rows = []
        main_layout = QVBoxLayout()

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_rows)
        top_bar.addWidget(btn_refresh)
        main_layout.addLayout(top_bar)

        title = QLabel("Pending Ride Requests")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self._header_label("Passenger"))
        header_layout.addWidget(self._header_label("Direction"))
        header_layout.addWidget(self._header_label("Area"))
        header_layout.addWidget(self._header_label("Min rating"))
        header_layout.addWidget(self._header_label("Action"))
        main_layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        self.rows_layout = QVBoxLayout()
        main_layout.addLayout(self.rows_layout)

        main_layout.addStretch(1)
        self.setLayout(main_layout)

        self.refresh_rows()

    def _header_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold;")
        return lbl

    def clear_rows(self):
        for row in self.request_rows:
            row.hide()
            row.setParent(None)
        self.request_rows = []

    def refresh_rows(self):
        self.clear_rows()

        if not self.requests:
            no_lbl = QLabel("No requests.")
            self.rows_layout.addWidget(no_lbl)
            self.request_rows.append(no_lbl)
            return

        for req in self.requests:
            row_widget = self.build_row(req)
            self.rows_layout.addWidget(row_widget)
            self.request_rows.append(row_widget)

    def build_row(self, request):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        passenger = request.get("passenger", "Unknown")
        direction = request.get("direction", "")
        area = request.get("area", "")
        min_rating = request.get("min_driver_rating", "")

        layout.addWidget(QLabel(passenger))
        layout.addWidget(QLabel(direction))
        layout.addWidget(QLabel(area))
        layout.addWidget(QLabel(str(min_rating)))

        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)

        action_container.setFixedWidth(160)
        action_container.setFixedHeight(28)

        status = request.get("status", "pending")

        if status == "pending":
            btn_accept = QPushButton("Accept")
            btn_accept.request = request
            btn_accept.clicked.connect(self.accept_request)
            action_layout.addWidget(btn_accept)

        elif status == "active":
            btn_end = QPushButton("End")
            btn_cancel = QPushButton("Cancel")

            btn_end.request = request
            btn_cancel.request = request

            btn_end.clicked.connect(self.end_request)
            btn_cancel.clicked.connect(self.cancel_request)

            action_layout.addWidget(btn_end)
            action_layout.addWidget(btn_cancel)

        else:
            action_layout.addWidget(QLabel(status))

        layout.addWidget(action_container)

        return row

    def accept_request(self):
        btn = self.sender()
        request = getattr(btn, "request", None)
        if request is None:
            return

        request["status"] = "active"
        self.refresh_rows()

    def end_request(self):
        btn = self.sender()
        req = getattr(btn, "request", None)
        if req is None:
            return

        passenger = req.get("passenger", "Unknown")

        if req in self.requests:
            self.requests.remove(req)
    
        self.refresh_rows()

    def cancel_request(self):
        btn = self.sender()
        request = getattr(btn, "request", None)
        if request is None:
            return

        request["status"] = "pending"

        self.refresh_rows()
