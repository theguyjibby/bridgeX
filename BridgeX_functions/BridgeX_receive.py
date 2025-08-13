import os
import json
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import unpad
from flask import jsonify
from shared import active_connections

from app import db, ReceivedFile

SHARED_SECRET = "supersecurepassword"
SALT = b'some_random_salt'


def derive_key_and_iv(password, salt, key_len=32, iv_len=16):
    dkey = PBKDF2(password, salt, dkLen=key_len + iv_len, count=100_000)
    return dkey[:key_len], dkey[key_len:]


def receive_file(sock):
    try:
        peer_ip = sock.getpeername()[0]

        while True:
            header = sock.recv(1024)
            if not header:
                break

            try:
                file_info = json.loads(header.decode())
                filename = file_info["filename"]
                filesize = file_info["filesize"]
            except (json.JSONDecodeError, UnicodeDecodeError):
                return jsonify({
                    'success': False,
                    'message': 'Invalid file header received.'
                }), 400

            # Create save directory
            save_dir = os.path.expanduser("~/Documents/BridgeX/Received")
            os.makedirs(save_dir, exist_ok=True)

            # Avoid overwriting existing files
            base, ext = os.path.splitext(filename)
            full_path = os.path.join(save_dir, filename)
            count = 1
            while os.path.exists(full_path):
                full_path = os.path.join(save_dir, f"{base}({count}){ext}")
                count += 1

            # decryption
            key, iv = derive_key_and_iv(SHARED_SECRET, SALT)
            cipher = AES.new(key, AES.MODE_CBC, iv)

            # Receive the encrypted file data
            encrypted_data = b''
            received = 0
            while received < filesize:
                data = sock.recv(4096)
                if not data:
                    break
                encrypted_data += data
                received += len(data)

            # Decrypt and save file
            try:
                decrypted_data = unpad(cipher.decrypt(encrypted_data),
                                       AES.block_size)
            except ValueError:
                return jsonify({
                    'success':
                    False,
                    'message':
                    'Decryption failed or incorrect padding.'
                }), 400

            with open(full_path, "wb") as f:
                f.write(decrypted_data)

            # Save metadata to database
            file_record = ReceivedFile(filename=filename,
                                       filesize=filesize,
                                       filepath=full_path,
                                       sender_ip=peer_ip)
            db.session.add(file_record)
            db.session.commit()

            print(f"[RECEIVE] File saved as: {full_path}")

        return jsonify({
            'success': True,
            'message': 'All files received successfully.'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unexpected error receiving file: {str(e)}'
        }), 500
