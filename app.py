from flask import Flask, request, redirect, url_for, render_template, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime



app = Flask(__name__)

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


from datetime import datetime

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



#signup
@app.route('/signup', methods=['POST'])
def signup():

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user or len(username)  <  4:
        return jsonify({'success' : False , 'message': 'choose another username' }), 
    elif len(password) < 6:
        return jsonify({'success': False , 'message' : 'password should be greater than 5 characters'})
    

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


if __name__== "__main__":
    app.run(debug=True)
    with app.app_context():
        db.create_all()
