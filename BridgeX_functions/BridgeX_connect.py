# connect.py
import socket
import threading
import time
import json
from BridgeX_functions.app import User
from BridgeX_receive import receive_file
from shared import active_connections

def connect(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return {'success': False, 'message': 'User not found'}, 404

        IPADDRESS = socket.gethostbyname(socket.gethostname())
        PORT = 1234
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((IPADDRESS, PORT))
            server_socket.listen(1)

            
            broadcast_stop = threading.Event()
            def broadcast_loop():
                udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                message = json.dumps({
                    "username": username,
                    "ip": IPADDRESS,
                    "port": PORT
                }).encode()
                while not broadcast_stop.is_set():
                    udp_socket.sendto(message, ('<broadcast>', 4444))
                    time.sleep(2)
                udp_socket.close()

            threading.Thread(target=broadcast_loop, daemon=True).start()

            
            def wait_for_connection():
                client_socket, addr = server_socket.accept()
                broadcast_stop.set()

    
                if username not in active_connections:
                    active_connections[username] = client_socket

                threading.Thread(target=receive_file, args=(client_socket,), daemon=True).start()

            threading.Thread(target=wait_for_connection, daemon=True).start()

            return {'success': True, 'message': f'{username} is now listening.'}, 200

        except Exception as e:
            server_socket.close()
            return {'success': False, 'message': f'Error setting up listener: {str(e)}'}, 500

    except Exception as e:
        return {'success': False, 'message': f'Unexpected error: {str(e)}'}, 500
