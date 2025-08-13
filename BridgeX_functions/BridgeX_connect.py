
import socket
import threading
import time
import json
from shared import active_connections

def connect(username):
    """
    Start broadcasting this user's presence to the network
    """
    try:
        # Start broadcasting in a separate thread
        broadcast_thread = threading.Thread(
            target=broadcast_presence, 
            args=(username,), 
            daemon=True
        )
        broadcast_thread.start()
        
        # Start TCP server to accept connections
        server_thread = threading.Thread(
            target=start_tcp_server, 
            args=(username,), 
            daemon=True
        )
        server_thread.start()
        
        return {"success": True, "message": f"Started broadcasting as {username}"}, 200
    
    except Exception as e:
        return {"success": False, "message": f"Failed to start connection: {str(e)}"}, 500

def broadcast_presence(username):
    """
    Broadcast user presence via UDP
    """
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            message = json.dumps({
                "username": username,
                "ip": get_local_ip(),
                "port": 1234
            })
            
            sock.sendto(message.encode(), ('<broadcast>', 4444))
            sock.close()
            time.sleep(5)  # Broadcast every 5 seconds
            
        except Exception as e:
            print(f"Broadcast error: {e}")
            time.sleep(5)

def start_tcp_server(username):
    """
    Start TCP server to accept file connections
    """
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 1234))
        server.listen(5)
        
        while True:
            client, addr = server.accept()
            # Handle each connection in a separate thread
            handler_thread = threading.Thread(
                target=handle_client_connection, 
                args=(client, addr, username), 
                daemon=True
            )
            handler_thread.start()
            
    except Exception as e:
        print(f"TCP server error: {e}")

def handle_client_connection(client, addr, username):
    """
    Handle incoming client connections
    """
    try:
        from BridgeX_receive import receive_file
        receive_file(client)
    except Exception as e:
        print(f"Client handling error: {e}")
    finally:
        client.close()

def get_local_ip():
    """
    Get the local IP address
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except:
        return "127.0.0.1"
