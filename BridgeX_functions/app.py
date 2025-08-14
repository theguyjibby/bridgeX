import os
from flask import Flask, request, redirect, url_for, render_template, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
#my functions
from BridgeX_accept import start_broadcast_listener, connect_to_peer
from BridgeX_connect import connect
from BridgeX_send import send_files
from BridgeX_accept import accept_connection
from shared import active_connections



app = Flask(__name__, template_folder='../templates', static_folder='../static')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisoursecretkey'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False





db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"



#Authentication DB
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username= db.Column(db.String(20), nullable=False,unique=True)
    password = db.Column(db.String(80), nullable=False)

#starting listening for sctive users immedistely the app starts 
start_broadcast_listener()



#History DB
class ReceivedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filesize = db.Column(db.Integer, nullable=False)
    filepath = db.Column(db.String(300), nullable=False)
    sender_ip = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    






@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')



#signup
@app.route('/signup', methods=['POST'])
def signup():

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user or len(username) < 4:
        return jsonify({'success': False, 'message': 'choose another username'}), 400 
    elif len(password) < 6:
        return jsonify({'success': False, 'message': 'password should be greater than 5 characters'}), 400
    

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    user = User(username= username, password=hashed_password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success' : True})


#login
@app.route('/login', methods=['POST'])
def login():
    
    data = request.get_json()
    if not data:
        return jsonify({'success' : False, 'message' : 'missing json'}), 400
    
    username = data.get('username')
    password = data.get('password')
    remember_me = data.get('remember_me', False)
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        login_user(user, remember=remember_me)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    

#logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'success' : True})


#routes for  user-defined functions!!!!!!!


@app.route("/accept", methods=["POST"])
@login_required
def accept():
    data = request.json
    target_user = data.get("target_user") 

    if not target_user:
        return jsonify({"status": "error", "message": "target_user required"}), 400

    username = current_user.username
    try:
        accept_connection(username, target_user)
        return jsonify({"status": "success", "message": f"Paired with {target_user}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/active_users", methods=["GET"])
def active_users():
    users = list(active_connections.keys())
    return jsonify({"active_users": users})



@app.route('/current-user', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        'username': current_user.username,
        'id': current_user.id
    })

@app.route('/connect', methods=['POST'])
@login_required
def connect_route():
    username = current_user.username
    response, status = connect(username)
    return jsonify(response), status

@app.route('/disconnect', methods=['POST'])
@login_required
def disconnect_route():
    username = current_user.username
    try:
        # Close any active connections for this user
        if username in active_connections:
            for connection in active_connections[username]:
                try:
                    connection.close()
                except:
                    pass
            del active_connections[username]
        
        return jsonify({"success": True, "message": "Disconnected successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    





@app.route('/upload-files', methods=['POST'])
@login_required
def upload_files():
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'success': False, 'message': 'No files selected'}), 400
        
        # Create upload directory
        upload_dir = os.path.expanduser("~/Documents/BridgeX/Uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_paths = []
        for file in files:
            if file.filename:
                # Save file temporarily for sending
                file_path = os.path.join(upload_dir, file.filename)
                file.save(file_path)
                file_paths.append(file_path)
        
        return jsonify({'success': True, 'file_paths': file_paths})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/send-files", methods=["POST"])
@login_required
def send_files_route():
    data = request.get_json()
    target = data.get("target_username")
    files = data.get("file_paths") 

    if not target or not files:
        return jsonify({"success": False, "message": "target_username and file_paths required"}), 400

    # Use current logged-in user's username
    current_username = current_user.username
    result = send_files(target, files)
    return jsonify(result), (200 if result["success"] else 500)

@app.route('/received-files', methods=['GET'])
@login_required
def get_received_files():
    try:
        files = ReceivedFile.query.order_by(ReceivedFile.timestamp.desc()).limit(50).all()
        files_data = []
        for file in files:
            files_data.append({
                'filename': file.filename,
                'filesize': file.filesize,
                'sender_ip': file.sender_ip,
                'timestamp': file.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'filepath': file.filepath
            })
        return jsonify({'success': True, 'files': files_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/update-username', methods=['POST'])
@login_required
def update_username():
    data = request.get_json()
    new_username = data.get('username')
    
    if not new_username or len(new_username) < 4:
        return jsonify({'success': False, 'message': 'Username must be at least 4 characters'}), 400
    
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user and existing_user.id != current_user.id:
        return jsonify({'success': False, 'message': 'Username already taken'}), 400
    
    try:
        current_user.username = new_username
        db.session.commit()
        return jsonify({'success': True, 'message': 'Username updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    




if __name__== "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)
