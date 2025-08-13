
import socket
import json
import threading
from BridgeX_receive import receive_file
from shared import active_connections  

active_peers = {}  # username: { ip, port }


def start_broadcast_listener():
    def listen_loop():
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('', 4444))
        
        while True:
            try:
                data, addr = udp_socket.recvfrom(1024)
                message = json.loads(data.decode())
                username = message.get("username")
                ip = message.get("ip") or addr[0] 
                port = message.get("port", 1234)

                if username:
                    active_peers[username] = {"ip": ip, "port": port}
            except:
                continue

    if not any(t.name == "PeerListener" for t in threading.enumerate()):
        t = threading.Thread(target=listen_loop, daemon=True, name="PeerListener")
        t.start()



def connect_to_peer(username):
    if username not in active_peers:
        return {"status": "error", "message": "User not found."}

    if username in active_connections:
        return {"status": "success", "message": f"Already connected to {username}"}

    target = active_peers[username]
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((target["ip"], target["port"]))
        
       
        active_connections[username] = sock

        
        threading.Thread(target=receive_file, args=(sock,), daemon=True).start()

        return {"status": "success", "message": f"Connected to {username}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
