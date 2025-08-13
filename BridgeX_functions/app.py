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
    password= data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):

        login_user(user)
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
def accept():
    data = request.json
    username = data.get("username")       
    target_user = data.get("target_user") 

    if not username or not target_user:
        return jsonify({"status": "error", "message": "username and target_user required"}), 400

    try:
        accept_connection(username, target_user)
        return jsonify({"status": "success", "message": f"Paired with {target_user}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/active_users", methods=["GET"])
def active_users():
    users = list(active_connections.keys())
    return jsonify({"active_users": users})



@app.route('/connect', methods=['POST'])
def connect_route():
    data = request.get_json()
    if not data or 'username' not in data:
        return jsonify({'success': False, 'message': 'Username required'}), 400
    
    username = data['username']
    response, status = connect(username)
    return jsonify(response), status
    





@app.route("/send-files", methods=["POST"])
@login_required
def send_files_route():
    data = request.get_json()
    target = data.get("target_username")
    files = data.get("file_paths") 

    if not target or not files:
        return jsonify({"success": False, "message": "target_username and file_paths required"}), 400

    result = send_files(target, files)
    return jsonify(result), (200 if result["success"] else 500)
    




if __name__== "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
