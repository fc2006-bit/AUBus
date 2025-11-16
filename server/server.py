import socket
import threading
from database import init_db, register_user, login_user, db_lock, edit_fields  # Removed update_availability import
import json


HOST = '0.0.0.0'
PORT = 12345

def handle_client(conn, addr):
    print(f"New connection from {addr}")
    message = conn.recv(1024).decode()
    try:
        fields = message.split(":")
        if fields[0].lower() == "register":
            username = fields[1]
            name = fields[2] 
            email = fields[3] 
            password = fields[4]
            area = fields[5]
            is_driver = int(fields[6])
            print(f"Registering user: {username}, {name}, {email}, {area}, {is_driver}")
            conn.sendall(register_user(username,name,email,password,area,is_driver).encode())
        elif fields[0].lower() == "login":
            username = fields[1]
            password = fields[2]
            print(f"Logging in user: {username}")
            conn.sendall(login_user(username, password).encode())
        elif fields[0].lower() == "editprofile":
            username = fields[1]
            full_name = fields[2]
            area = fields[3]
            is_driver = int(fields[4])
            dict = {"name": full_name, "area": area, "is_driver": is_driver}
            print(f"Editing profile for user: {username}")
            conn.sendall(edit_fields(username, dict).encode())
        elif fields[0].lower() == "update_availability":
            username = fields[1]
            availability_str = fields[2]
            min_rating = fields[3]

            print("Received availability:", availability_str)

            parts = availability_str.split(";")

            days_order = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            availability = {}

            for i, day in enumerate(days_order):
                entry = parts[i]
                if entry:   # if not empty
                    from_time, to_time = entry.split("-")
                    availability[day] = {
                        "from": from_time.replace(".", ":"),
                        "to": to_time.replace(".", ":")
                    }
                else:
                    availability[day] = None

            update_fields = {
                "mon_commute": availability["mon"] or [],
                "tue_commute": availability["tue"] or [],
                "wed_commute": availability["wed"] or [],
                "thu_commute": availability["thu"] or [],
                "fri_commute": availability["fri"] or [],
                "sat_commute": availability["sat"] or [],
                "sun_commute": availability["sun"] or [],
                "min_passenger_rating": min_rating
            }

            print("Parsed availability:", availability)

            response = edit_fields(username, update_fields)
            conn.sendall(response.encode())

        else:
            conn.sendall("Invalid command.".encode())
    except Exception as e:
        print(f"Error: {e}")
        conn.sendall("Error processing request. Connection closing.\n".encode())
    finally:
        conn.close()

init_db()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Server listening on port {PORT}...")

while True:
    conn, addr = server_socket.accept()
    client_thread = threading.Thread(target=handle_client, args=(conn, addr))
    client_thread.start()
