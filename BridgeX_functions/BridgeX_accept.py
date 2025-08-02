import socket
import json
import time
import threading
import os
from BridgeX_receive import receive_file




#the accept code: example
active_peers = {}  # Format: { "ajibo": {"ip": "192.168.1.5", "port": 1234} }

def listen_for_peers():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', 4444))  # Listen on all interfaces(UDP), port 4444

    def listen_loop():
        while True:
            try:
                data, addr = udp_socket.recvfrom(1024)
                message = json.loads(data.decode())
                username = message["username"]
                ip = message["ip"]
                port = message.get("port", 1234)

                # Save the peer info
                active_peers[username] = {"ip": ip, "port": port}

            except Exception as e:
                print(f"Error receiving broadcast: {e}")

    # Start in listening in the background
    threading.Thread(target=listen_loop, daemon=True).start()

def accept():
    print("🟡 Listening for available peers on LAN...")
    listen_for_peers()

    # display active users after 3 seconds
    time.sleep(3)

    while True:
        print("\nAvailable devices:")
        for username, info in active_peers.items():
            print(f"- {username} ")

        selected_user = input("Enter the username to connect to (or 'refresh'): ").strip()

        if selected_user.lower() == "refresh":
            continue

        if selected_user not in active_peers:
            print("❌ Username not found. Try again.")
            continue

        # Get selected user's info
        target = active_peers[selected_user]
        target_ip = target["ip"]
        target_port = target["port"]

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((target_ip, target_port))

            #recieve function running in the background
            
            threading.Thread(target=receive_file, args=(client_socket,), daemon=True).start()


            print(f"✅ Connected to {selected_user} at {target_ip}:{target_port}")
            return client_socket
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return None



