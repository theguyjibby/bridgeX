import os
import json
import struct
import time
from typing import List, Dict
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad

from shared import active_connections 


SHARED_SECRET = "supersecurepassword"
SALT = b'some_random_salt'
PBKDF2_ITERS = 100_000
AES_BLOCK = AES.block_size  

def derive_key_and_iv(password: str, salt: bytes, key_len=32, iv_len=16):
    dkey = PBKDF2(password, salt, dkLen=key_len + iv_len, count=PBKDF2_ITERS)
    return dkey[:key_len], dkey[key_len:key_len+iv_len]

def _send_single_file_over_sock(sock, file_path: str, timeout: float = 20.0) -> Dict:
    
    if not os.path.isfile(file_path):
        return {"success": False, "message": f"File not found: {file_path}"}

    filename = os.path.basename(file_path)

    try:
        # read file 
        with open(file_path, "rb") as f:
            raw = f.read()

        # encrypt
        key, iv = derive_key_and_iv(SHARED_SECRET, SALT)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(pad(raw, AES_BLOCK))
        encrypted_size = len(encrypted)

        # prepare header
        header = json.dumps({"filename": filename, "filesize": encrypted_size})
        header_bytes = header.encode("utf-8")

        # send 4-byte header length
        sock.sendall(struct.pack(">I", len(header_bytes)))

        # send header
        sock.sendall(header_bytes)

        #send encrypted file in chunks
        CHUNK = 4096
        sent = 0
        while sent < encrypted_size:
            chunk = encrypted[sent:sent+CHUNK]
            sock.sendall(chunk)
            sent += len(chunk)

        # 4) optionally wait for ACK from receiver
        sock.settimeout(timeout)
        try:
            ack = sock.recv(1024)
            if ack is None:
                return {"success": False, "message": "No ACK from receiver."}
            # accept either b'RECEIVED' or JSON ack
            if ack.strip().upper().startswith(b"RECEIVED") or b'"success":' in ack:
                return {"success": True, "message": f"Sent '{filename}' ({encrypted_size} bytes)."}
            else:
                return {"success": False, "message": f"Unexpected ACK from receiver: {ack!r}"}
        except Exception as e:
            return {"success": False, "message": f"Timeout/waiting for ACK: {e}"}
        finally:
            sock.settimeout(None)

    except Exception as e:
        return {"success": False, "message": f"Error sending '{file_path}': {str(e)}"}


def send_files(target_username: str, file_paths: List[str]) -> Dict:
    
    if target_username not in active_connections:
        return {"success": False, "message": "Not connected to target user.", "details": []}

    sock = active_connections[target_username]
    results = []
    for path in file_paths:
        res = _send_single_file_over_sock(sock, path)
        results.append({"file": os.path.basename(path), **res})
        # small pause
        time.sleep(0.1)

    overall_success = all(r["success"] for r in results)
    return {"success": overall_success, "message": "Files processed", "details": results}

