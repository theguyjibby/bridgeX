# shared_sockets.py
active_connections = {}  # {username: socket_object}
# shared.py - Global variables shared across modules
active_connections = {}  # username: socket_object
active_peers = {}        # username: { ip, port }
