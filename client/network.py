import socket

HOST = "5.tcp.eu.ngrok.io"
PORT = 13482

def open_connection():
    """Establish a TCP connection to the server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    return s

def send_request(s: socket.socket, data: str):
    """Send data to the server through the given socket."""
    try:
        s.sendall(data.encode())
        response = s.recv(2048).decode()
        return response
    except Exception as e:
        return f"Connection error: {e}"
    
def close_connection(s: socket.socket):
    """Close the given socket connection."""
    s.close()

open_connection()
