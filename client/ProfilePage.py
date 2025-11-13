from PyQt5.QtWidgets import QWidget, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QCheckBox, QDialogButtonBox, QMessageBox
from RequestRidePage import RequestRidePage
from DriverDashboardPage import DriverDashboardPage
from network import open_connection, send_request, close_connection

class ProfilePage(QWidget):
    def __init__(self, person):
        self.socket = open_connection()
        super().__init__()
        self.person = person
        layout = QVBoxLayout()

        self.edit_button = QPushButton("Edit Profile")
        self.make_editable = True
        self.edit_button.clicked.connect(lambda: self.editable())
        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(self.edit_button)
        layout.addLayout(top)

        self.full_name_field = QLineEdit(person.full_name or person.username)
        self.full_name_field.setReadOnly(True)
        self.email_field = QLineEdit(person.email)
        self.email_field.setReadOnly(True)
        self.area_field = QLineEdit(person.area)
        self.area_field.setReadOnly(True)
        self.driver_checkbox = QCheckBox()
        self.driver_checkbox.setEnabled(False)
        self.driver_checkbox.setChecked(person.is_driver == 1)
        self.driver_checkbox.stateChanged.connect(self.driver_toggle)

        form = QFormLayout()
        form.addRow("Full name:", self.full_name_field)
        form.addRow("Email:", self.email_field)
        form.addRow("Area:", self.area_field)
        form.addRow("Driver:", self.driver_checkbox)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.save_profile)
        self.buttons.rejected.connect(self.cancel)
        layout.addWidget(self.buttons)
        self.buttons.hide()

        request_ride_button = QPushButton("Request Ride")
        self.r = RequestRidePage()
        request_ride_button.clicked.connect(lambda: self.r.show())
        layout.addWidget(request_ride_button)

        self.driver_dashboard_button = QPushButton("Driver dashboard")
        self.d = DriverDashboardPage()
        self.driver_dashboard_button.clicked.connect(lambda: self.d.show())
        layout.addWidget(self.driver_dashboard_button)
        self.driver_dashboard_button.hide()

        sign_out_button = QPushButton("Sign Out")
        sign_out_button.clicked.connect(self.sign_out)
        layout.addWidget(sign_out_button)

        self.setLayout(layout)

    def editable(self):
        self.make_editable = not self.make_editable
        self.full_name_field.setReadOnly(self.make_editable)
        self.area_field.setReadOnly(self.make_editable)
        self.edit_button.setEnabled(self.make_editable)
        self.driver_checkbox.setEnabled(not self.make_editable)
        self.buttons.setVisible(not self.make_editable)

    def save_profile(self):
        self.person.full_name = self.full_name_field.text()
        self.person.email = self.email_field.text()
        self.person.area = self.area_field.text()
        self.person.is_driver = int(self.driver_checkbox.isChecked())
        send_request(self.socket, f"editprofile:{self.person.username}:{self.person.full_name}:{self.person.area}:{self.person.is_driver}")
        self.editable()

    def cancel(self):
        self.full_name_field.setText(self.person.full_name or self.person.username)
        self.email_field.setText(self.person.email)
        self.area_field.setText(self.person.area)
        self.driver_checkbox.setChecked(self.person.is_driver)
        self.editable()

    def driver_toggle(self):
        if self.driver_checkbox.isChecked():
            self.driver_dashboard_button.show()
        else:
            self.driver_dashboard_button.hide()

    def sign_out(self):
        QMessageBox.information(self, "Sign Out", "You have been signed out.")
        close_connection(self.socket)
        from LoginPage import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.hide()