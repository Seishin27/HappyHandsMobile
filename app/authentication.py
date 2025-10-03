from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt, decode_token,
    set_access_cookies, unset_jwt_cookies
)
import os

# Try to import forms, create a simple class if not available
try:
    from .forms import SellerSignupForm
except ImportError:
    # Create a simple form class if forms.py is not available
    class SellerSignupForm:
        def __init__(self):
            pass
        def validate_on_submit(self):
            return False

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "babybloomph@gmail.com"
ADMIN_PASSWORD = "babybloomph123"

# Get the parent directory (Neverlonely folder)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(parent_dir, 'templates')
static_dir = os.path.join(parent_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your-secret-key-here'  
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string')

app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  
# Use cookies for JWT storage so browser requests (and logout) can work without Authorization header
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
# Keep the cookie name consistent with other places in the code (we read/write 'access_token')
# flask_jwt_extended defaults to 'access_token_cookie', but earlier code sets/reads
# a cookie named 'access_token', so configure the manager to use that name.
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
# For development on HTTP set to False. In production set True and serve over HTTPS.
app.config['JWT_COOKIE_SECURE'] = False
# Whether CSRF protection for cookies is enabled. For simplicity keep False for now and enable later.
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'

jwt = JWTManager(app)

BLOCKLIST = set()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get('jti')
    return jti in BLOCKLIST

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


# JWT error handlers to return JSON responses (helps the client understand 401/422 reasons)
@jwt.unauthorized_loader
def custom_unauthorized_response(err_str):
    # No JWT present in the request
    return jsonify({'msg': 'Missing JWT (authorization required)', 'error': err_str}), 401


@jwt.invalid_token_loader
def custom_invalid_token_response(err_str):
    return jsonify({'msg': 'Invalid JWT', 'error': err_str}), 422


@jwt.expired_token_loader
def custom_expired_token_response(jwt_header, jwt_payload):
    return jsonify({'msg': 'JWT has expired'}), 401


@jwt.revoked_token_loader
def custom_revoked_token_response(jwt_header, jwt_payload):
    return jsonify({'msg': 'JWT has been revoked'}), 401



@app.context_processor
def inject_user():
    """Inject a `user` object into templates when an access token cookie is present.

    The token is decoded (not required on the route) and the identity returned by
    create_access_token (whatever structure you passed as identity) is exposed as `user`.
    If decoding fails or no token exists, no `user` is injected.
    """
    # First, prefer server-side session if set (ensures immediate UI update after login)
    try:
        sess_user = session.get('user')
        if sess_user:
            return {'user': sess_user}
    except Exception:
        pass

    token = None
    try:
        token = request.cookies.get('access_token')
    except Exception:
        return {}

    if not token:
        return {}

    try:
        decoded = decode_token(token)
        # flask-jwt-extended stores the identity under 'sub'
        identity = decoded.get('sub') if isinstance(decoded, dict) else None

        # If identity contains a numeric userID, try to fetch full user info from DB
        if identity and isinstance(identity, dict) and identity.get('userID'):
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT userID, username, email FROM users WHERE userID = %s', (identity.get('userID'),))
                    row = cursor.fetchone()
                    if row:
                        user_obj = {'userID': row[0], 'username': row[1], 'email': row[2]}
                        return {'user': user_obj}
                except Exception:
                    pass
                finally:
                    try:
                        if conn.is_connected():
                            cursor.close()
                            conn.close()
                    except Exception:
                        pass

        # Fallback: expose whatever identity was in the token
        return {'user': identity}
    except Exception:
        # Any decoding error (expired/invalid) -> treat as anonymous
        return {}


@app.route('/profile')
def profile():
    token = None
    try:
        token = request.cookies.get('access_token')
    except Exception:
        token = None

    if not token:
        return redirect(url_for('login'))

    try:
        decoded = decode_token(token)
        identity = decoded.get('sub') if isinstance(decoded, dict) else None
        if not identity:
            return redirect(url_for('login'))
        return render_template('profile.html', user=identity)
    except Exception:
        return redirect(url_for('login'))

@app.route('/')
def home():
    # Rely on the context processor `inject_user` to provide `user` to templates.
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        access_token = create_access_token(identity={'userID': 0, 'username': ADMIN_USERNAME, 'email': ADMIN_EMAIL})
        session['user'] = {'userID': 0, 'username': ADMIN_USERNAME, 'email': ADMIN_EMAIL}
        resp = make_response(redirect(url_for('admin_dashboard')))
        resp.set_cookie('access_token', access_token, httponly=True, secure=False, samesite='Lax', max_age=3600)
        return resp
    
    if not username or not password:
        flash('Please fill in all fields', 'danger')
        return render_template('login.html')
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return render_template('login.html')
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT userID, username, password, email FROM users WHERE username = %s OR email = %s', (username, username))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[2], password):
            access_token = create_access_token(identity={'userID': user[0], 'username': user[1]})
            # Also set session so server-side templates can access the user immediately
            user_email = user[3] if len(user) > 3 else None
            session['user'] = {'userID': user[0], 'username': user[1], 'email': user_email}

            resp = make_response(redirect(url_for('home')))
            # Set the JWT cookie
            set_access_cookies(resp, access_token)
            return resp
        else:
            flash('Invalid username or password', 'danger')
            return render_template('login.html')
            
    except mysql.connector.Error as err:
        flash('Login error occurred', 'danger')
        print(f"Login error: {err}")
        return render_template('login.html')
    finally:
        try:
            if conn.is_connected():
                cursor.close()
                conn.close()
        except Exception:
            pass


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Example protected endpoint. Client must send Authorization: Bearer <token>
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200


@app.route('/logout', methods=['POST'])
def logout():
    try:
        # Clear the session
        session.clear()
        print("Logout: Session cleared successfully")
        return jsonify({'success': True, 'msg': 'Logged out successfully'}), 200
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'success': False, 'msg': 'Logout failed', 'error': str(e)}), 500


# Development helper: inspect the raw access_token cookie and try decoding it.
# WARNING: This endpoint leaks token contents and should only be used in development.
@app.route('/debug/token', methods=['GET'])
def debug_token():
    # Only allow when Flask debug is enabled
    if not app.debug:
        return jsonify({'msg': 'Not available in production'}), 403

    cookie_name = app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token')
    token = request.cookies.get(cookie_name)
    if not token:
        return jsonify({'present': False, 'cookie_name': cookie_name, 'msg': 'No token cookie found'}), 200

    try:
        decoded = decode_token(token)
        return jsonify({'present': True, 'cookie_name': cookie_name, 'decoded': decoded}), 200
    except Exception as e:
        return jsonify({'present': True, 'cookie_name': cookie_name, 'error': str(e)}), 200

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

# Seller Routes
@app.route('/seller_homepage')
def seller_homepage():
    return render_template('seller_homepage.html')

@app.route('/seller_signup', methods=['GET', 'POST'])
def seller_signup():
    """Seller registration form"""
    if request.method == 'POST':
        # Handle seller registration - simple form handling without WTForms
        business_name = request.form.get('business_name')
        business_type = request.form.get('business_type')
        business_description = request.form.get('business_description')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address_line1 = request.form.get('address_line1')
        address_line2 = request.form.get('address_line2')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        agree_terms = request.form.get('agree_terms')
        marketing_emails = request.form.get('marketing_emails')

        # Basic validation
        if not all([business_name, business_type, first_name, last_name, email, phone, password, agree_terms]):
            flash('Please fill in all required fields', 'error')
            return render_template('seller_signup.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('seller_signup.html')

        # For now, just show success message (since we don't have the database table yet)
        flash('Thank you for your interest! We will contact you soon to set up your seller account.', 'success')
        return redirect(url_for('become_seller'))

    return render_template('seller_signup.html')

@app.route('/rider_homepage')
def rider_homepage():
    return render_template('rider_homepage.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')