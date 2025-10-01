from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Get the parent directory (Neverlonely folder)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(parent_dir, 'templates')
static_dir = os.path.join(parent_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key

def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="BabyStore",
            port="3306"
        )
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/product1')
def product1():
    return render_template('product1.html')

@app.route('/product2')
def product2():
    return render_template('product2.html')

@app.route('/product3')
def product3():
    return render_template('product3.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    # Handle POST request
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Please fill in all fields', 'danger')
        return render_template('login.html')
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return render_template('login.html')
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT userID, username, password FROM users WHERE username = %s OR email = %s', (username, username))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[2], password):
            # Login successful - you can add session management here
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
            return render_template('login.html')
            
    except mysql.connector.Error as err:
        flash('Login error occurred', 'danger')
        print(f"Login error: {err}")
        return render_template('login.html')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('reg-email')
    username = request.form.get('reg-username')
    password = request.form.get('reg-password')
    confirmpassword = request.form.get('reg-confirm-password')
    
    if not email or not username or not password or not confirmpassword:
        flash('Please fill in all fields', 'danger')
        return render_template('login.html')
    
    if password != confirmpassword:
        flash('Password does not match', 'danger')
        return render_template('login.html')
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return render_template('login.html')
    
    try:
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute('SELECT userID FROM users WHERE username = %s OR email = %s', (username, email))
        if cursor.fetchone():
            flash('Username or email already exists', 'danger')
            return render_template('login.html')
        
        # Create new user
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                      (username, email, hashed_password))
        conn.commit()
        
        flash('Account created successfully! Please login.', 'success')
        return render_template('login.html')
        
    except mysql.connector.Error as err:
        flash('Registration error occurred', 'danger')
        print(f"Registration error: {err}")
        return render_template('login.html')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()