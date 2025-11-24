from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
)
from PyQt5.QtCore import QTimer
from network import open_connection, send_request, close_connection
import base64
import json


def api_fetch_messages(ride_id):
    conn = open_connection()
    if not conn:
        return [], "Unable to connect to server."

    resp = send_request(conn, f"get_messages:{ride_id}")
    close_connection(conn)

    if not resp:
        return [], "Empty server response."

    if resp.startswith("success:"):
        payload = resp.split(":", 1)[1]
        try:
            return json.loads(payload or "[]"), None
        except json.JSONDecodeError:
            return [], "Malformed message data."

    if resp.startswith("error:"):
        return [], resp.split(":", 1)[1] or "Server error."

    return [], resp


def api_send_message(ride_id, sender, recipient, text):
    conn = open_connection()
    if not conn:
        return "Unable to connect to server."
    encoded = base64.b64encode(text.encode()).decode()
    resp = send_request(conn, f"send_message:{ride_id}:{sender}:{recipient}:{encoded}")
    close_connection(conn)
    return resp or "No server response."


class ChatWindow(QWidget):
    def __init__(self, ride_id, current_user, other_user, other_user_name=None):
        super().__init__()
        self.ride_id = ride_id
        self.current_user = current_user
        self.other_user = other_user
        self.other_user_name = other_user_name or other_user
        self.setWindowTitle(f"Chat with {self.other_user_name}")

        layout = QVBoxLayout()

        header = QLabel(f"Ride: {ride_id}")
        layout.addWidget(header)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message...")
        input_layout.addWidget(self.input_field)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_messages)
        layout.addWidget(refresh_btn)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.load_messages)
        self.timer.start(3000)

        self.load_messages()

    def load_messages(self):
        messages, error = api_fetch_messages(self.ride_id)
        if error:
            self.log.setPlainText(f"Error loading messages: {error}")
            return

        lines = []
        for msg in messages:
            sender = msg.get("sender", "Unknown")
            sender_name = msg.get("sender_name") or sender
            text = msg.get("message", "")
            timestamp = msg.get("timestamp", "")
            lines.append(f"[{timestamp}] {sender_name}: {text}")
        self.log.setPlainText("\n".join(lines))
        self.log.moveCursor(self.log.textCursor().End)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        resp = api_send_message(self.ride_id, self.current_user, self.other_user, text)
        if resp.lower().startswith("message sent"):
            self.input_field.clear()
            self.load_messages()
        else:
            self.log.append(f"\n[Error] {resp}")

    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
        super().closeEvent(event)
