import socket
import threading
import json
import uuid
import base64
from database import (
    init_db,
    register_user,
    login_user,
    db_lock,
    edit_fields,
    search_valid_drivers,
    add_pending_request,
    get_pending_requests,
    delete_pending_request,
    accept_pending_request,
    complete_pending_request,
    get_active_rides,
    get_completed_rides,
    add_active_ride,
    remove_active_ride,
    add_completed_ride,
    remove_completed_ride,
    rate_driver,
    rate_passenger,
    get_user_display_name,
    add_ride_message,
    get_ride_messages,
)


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
                if entry:
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

            response = edit_fields(username, update_fields)
            conn.sendall(response.encode())
        elif fields[0].lower() == "request_ride":
            passenger = fields[1]
            area = fields[2]
            day = fields[3] + "_commute"
            ride_time = f"{fields[4]}:{fields[5]}"
            min_rating = float(fields[6])
            passenger_name = get_user_display_name(passenger)
            drivers = search_valid_drivers(area, day, ride_time, min_rating)
            print(f"Found drivers: {drivers}")
            if isinstance(drivers, str):
                # No drivers or error message
                conn.sendall(drivers.encode())
            else:
                added = 0
                failures = []
                request_id = str(uuid.uuid4())
                request_payload = {
                    "id": request_id,
                    "passenger": passenger,
                    "passenger_name": passenger_name,
                    "area": area,
                    "day": day,
                    "time": ride_time,
                    "min_rating": min_rating,
                    "status": "pending",
                    "accepted_by": None
                }

                for d in drivers:
                    try:
                        res = add_pending_request(d["username"], request_payload)
                        if "added" in res.lower() or "request added" in res.lower() or res == "Request added to pending queue.":
                            added += 1
                        else:
                            # treat non-success as failure but continue
                            failures.append(f"{d['username']}: {res}")
                    except Exception as e:
                        failures.append(f"{d.get('username','?')}: {e}")

                resp = f"Request added to {added} driver(s)."
                if failures:
                    resp += " Failures: " + "; ".join(failures)
                print(resp)
                conn.sendall(resp.encode())
        elif fields[0].lower() == "get_pending":
            username = fields[1]
            result = get_pending_requests(username)
            if isinstance(result, str):
                conn.sendall(("error:" + result).encode())
            else:
                conn.sendall(("success:" + json.dumps(result)).encode())
        elif fields[0].lower() == "get_active_rides":
            username = fields[1]
            result = get_active_rides(username)
            if isinstance(result, str):
                conn.sendall(("error:" + result).encode())
            else:
                conn.sendall(("success:" + json.dumps(result)).encode())
        elif fields[0].lower() == "get_completed_rides":
            username = fields[1]
            result = get_completed_rides(username)
            if isinstance(result, str):
                conn.sendall(("error:" + result).encode())
            else:
                conn.sendall(("success:" + json.dumps(result)).encode())
        elif fields[0].lower() == "delete_request":
            username = fields[1]
            index = int(fields[2])

            result = delete_pending_request(username, index)
            conn.sendall(result.encode())
        elif fields[0].lower() == "accept_request":
            driver_username = fields[1]
            request_id = fields[2]
            result = accept_pending_request(driver_username, request_id)
            conn.sendall(result.encode())
        elif fields[0].lower() == "end_request":
            driver_username = fields[1]
            request_id = fields[2]
            result = complete_pending_request(driver_username, request_id)
            conn.sendall(result.encode())
        elif fields[0].lower() == "rate_passenger":
            passenger_username = fields[1]
            try:
                rating = float(fields[2])
            except (ValueError, IndexError):
                conn.sendall("Invalid rating.".encode())
                return
            result = rate_passenger(passenger_username, rating)
            conn.sendall(result.encode())
        elif fields[0].lower() == "rate_driver_ride":
            passenger_username = fields[1]
            driver_username = fields[2]
            request_id = fields[3]
            try:
                rating = float(fields[4])
            except (ValueError, IndexError):
                conn.sendall("Invalid rating.".encode())
                return
            result = rate_driver(driver_username, rating)
            if result.lower().startswith("driver rating updated"):
                remove_completed_ride(passenger_username, request_id)
            conn.sendall(result.encode())
        elif fields[0].lower() == "send_message":
            if len(fields) < 5:
                conn.sendall("Invalid message payload.".encode())
                return
            ride_id = fields[1]
            sender = fields[2]
            recipient = fields[3]
            encoded_msg = fields[4]
            try:
                message_text = base64.b64decode(encoded_msg.encode()).decode()
            except Exception:
                conn.sendall("Invalid message encoding.".encode())
                return
            result = add_ride_message(ride_id, sender, recipient, message_text)
            conn.sendall(result.encode())
        elif fields[0].lower() == "get_messages":
            if len(fields) < 2:
                conn.sendall("Invalid ride id.".encode())
                return
            ride_id = fields[1]
            result = get_ride_messages(ride_id)
            if isinstance(result, str):
                conn.sendall(("error:" + result).encode())
            else:
                conn.sendall(("success:" + json.dumps(result)).encode())


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
