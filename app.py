from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import base64
import os

app = Flask(__name__)

# Login Configuration
app.config['SECRET_KEY'] = 'thisisasecretkey1'  # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model 
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)  # Added email column
    password_hash = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:      
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']  # Added email field
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():  # Check if email already exists
            flash('Email already exists')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)  # Added email
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        compound_name = request.form['compound']
        data, error = get_compound_data(compound_name)
        return render_template('index.html', data=data, error=error)
    return render_template('index.html', data=None, error=None)

# Login Manager Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_compound_data(compound_name):
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"
    properties = [
        "IUPACName",
        "MolecularFormula",
        "MolecularWeight",
        "CanonicalSMILES",
        "XLogP"
    ]
    
    try:
        # Get CID (Compound ID)
        cid_response = requests.get(f"{base_url}/{compound_name}/cids/JSON")
        if cid_response.status_code != 200:
            return None, "Compound not found"
        
        cid = cid_response.json()['IdentifierList']['CID'][0]

        # Get compound properties
        props_response = requests.get(
            f"{base_url}/{compound_name}/property/{','.join(properties)}/JSON"
        )
        
        if props_response.status_code != 200:
            return None, "Failed to fetch properties"

        properties_data = props_response.json()['PropertyTable']['Properties'][0]
        
        # Get structure image
        img_response = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG"
        )
        img_base64 = base64.b64encode(img_response.content).decode('utf-8')

        return {
            'name': compound_name,
            'iupac_name': properties_data.get('IUPACName', 'N/A'),
            'molecular_formula': properties_data.get('MolecularFormula', 'N/A'),
            'molecular_weight': properties_data.get('MolecularWeight', 'N/A'),
            'smiles': properties_data.get('CanonicalSMILES', 'N/A'),
            'xlogp': properties_data.get('XLogP', 'N/A'),
            'structure_image': img_base64,
            'cid': cid
        }, None
    
    except Exception as e:
        return None, str(e)

with app.app_context():
    db.create_all() 
    
if __name__ == '__main__':
    app.run(debug=True)
