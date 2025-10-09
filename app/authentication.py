from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.security import check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt, decode_token,
    set_access_cookies, unset_jwt_cookies
)
import os
import requests
import uuid
from werkzeug.utils import secure_filename
from flask import send_from_directory
from datetime import datetime

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

    # admin quick-check (unchanged)
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
        # use dictionary cursor so we can read columns by name even if schema differs
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s LIMIT 1", (username, username))
        user = cursor.fetchone()

        if user:
            # tolerant column resolution
            hashed = user.get('password') or user.get('passwd') or user.get('sellerpassword') or ''
            if hashed and check_password_hash(hashed, password):
                user_id = user.get('userID') or user.get('id') or user.get('user_id')
                user_name = user.get('username') or user.get('name')
                user_email = user.get('email')

                access_token = create_access_token(identity={'userID': user_id, 'username': user_name, 'email': user_email})
                session['user'] = {'userID': user_id, 'username': user_name, 'email': user_email}
                resp = make_response(redirect(url_for('home')))
                set_access_cookies(resp, access_token)
                return resp

        flash('Invalid username or password', 'danger')
        return render_template('login.html')

    except mysql.connector.Error as err:
        app.logger.exception("Login DB error")
        flash('Login error occurred', 'danger')
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
    """Clear session and redirect to login."""
    session.clear()
    flash('You have been signed out.', 'success')
    return redirect(url_for('login'))  # redirect to seller login; change to 'login' if needed


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
    if request.method == 'POST':
        # Read form fields
        sellername = (request.form.get('sellername') or '').strip()
        selleremail = (request.form.get('selleremail') or '').strip()
        contactnumber = (request.form.get('contactnumber') or '').strip()
        storename = (request.form.get('storename') or '').strip()
        storedesc = (request.form.get('storedesc') or request.form.get('storedec') or '').strip()
        region = request.form.get('region')
        province = request.form.get('province')
        city = request.form.get('city')
        barangay = request.form.get('barangay')
        password = request.form.get('password') or request.form.get('sellerpassword') or ''
        confirmpassword = request.form.get('confirmpassword') or request.form.get('confirm_password') or ''

        # Basic validation (include password)
        required = [sellername, selleremail, contactnumber, storename, storedesc, region, province, city, barangay, password, confirmpassword]
        if not all(required):
            flash('Please fill in all required fields (including password)', 'error')
            return render_template('seller_signup.html')

        if password != confirmpassword:
            flash('Passwords do not match', 'error')
            return render_template('seller_signup.html')

        # hash the password
        hashed_password = generate_password_hash(password)

        # File objects (use request.files for uploads)
        logo_file = request.files.get('storelogo')
        permit_file = request.files.get('businesspermit')

        # prepare upload folder
        try:
            os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(parent_dir, 'uploads')), exist_ok=True)
        except Exception:
            app.logger.exception("Failed to ensure upload folder")
            flash('Server configuration error (uploads).', 'error')
            return render_template('seller_signup.html')

        logo_path = None
        permit_path = None

        if logo_file and logo_file.filename:
            if not allowed_file(logo_file.filename, ALLOWED_IMAGE_EXT):
                flash('Store logo must be an image (png/jpg/jpeg)', 'error')
                return render_template('seller_signup.html')
            filename = secure_filename(logo_file.filename)
            unique = f"logo_{uuid.uuid4().hex}_{filename}"
            logo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
            logo_path = unique

        if permit_file and permit_file.filename:
            if not allowed_file(permit_file.filename, ALLOWED_DOC_EXT):
                flash('Business permit must be PDF or image', 'error')
                return render_template('seller_signup.html')
            filename = secure_filename(permit_file.filename)
            unique = f"permit_{uuid.uuid4().hex}_{filename}"
            permit_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
            permit_path = unique

        # Insert into DB (adapt to actual password column)
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return render_template('seller_signup.html')

        try:
            cursor = conn.cursor()
            # detect password column name
            cursor.execute("SHOW COLUMNS FROM sellers")
            columns = [r[0] for r in cursor.fetchall()]
            if 'password' in columns:
                pw_col = 'password'
            elif 'sellerpassword' in columns:
                pw_col = 'sellerpassword'
            elif 'passwd' in columns:
                pw_col = 'passwd'
            else:
                flash('Database missing password column on sellers table. Please run migration to add a password column.', 'error')
                return render_template('seller_signup.html')

            cols = ['sellername', 'selleremail', 'contactnumber', 'storename', 'storedesc', pw_col, 'storelogo_path', 'businesspermit_path', 'region', 'province', 'city', 'barangay']
            placeholders = ','.join(['%s'] * len(cols))
            sql = "INSERT INTO sellers ({}) VALUES ({})".format(','.join(cols), placeholders)
            values = (sellername, selleremail, contactnumber, storename, storedesc, hashed_password, logo_path, permit_path, region, province, city, barangay)
            cursor.execute(sql, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            app.logger.exception("Seller signup DB error")
            flash('Error saving seller data', 'error')
            return render_template('seller_signup.html')
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        flash('Thank you for your interest! We will contact you soon to set up your seller account.', 'success')
        return redirect(url_for('seller_login'))

    return render_template('seller_signup.html')

@app.route('/rider_homepage')
def rider_homepage():
    return render_template('rider_homepage.html')

def admin_required():
    """Decorator to check if user is admin"""
    user = session.get('user')
    if not user or user.get('userID') != 0:  # Admin has userID 0
        return False
    return True

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not admin_required():
        return redirect(url_for('login'))

    # load sellers for the "Approve Store" section
    conn = get_db_connection()
    sellers = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT sellerID, sellername, selleremail, contactnumber, storename, storedesc,
                   region, province, city, barangay, storelogo_path, businesspermit_path
            FROM sellers
            ORDER BY sellerID DESC
        """)
        for row in cursor.fetchall():
            sellers.append({
                'sellerID': row.get('sellerID') or row.get('sellerID'.lower()) or row.get('sellerId'),
                'sellername': row.get('sellername'),
                'selleremail': row.get('selleremail'),
                'contactnumber': row.get('contactnumber'),
                'storename': row.get('storename'),
                'storedesc': row.get('storedesc') or '',
                'region': row.get('region'),
                'province': row.get('province'),
                'city': row.get('city'),
                'barangay': row.get('barangay'),
                'storelogo_path': row.get('storelogo_path'),
                'businesspermit_path': row.get('businesspermit_path'),
            })
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return render_template('admin_dashboard.html', sellers=sellers)

@app.route('/admin/stores')
def admin_stores():
    if not admin_required():
        return redirect(url_for('login'))
    # TODO: Implement stores management
    return render_template('admin_dashboard.html')

@app.route('/admin/coupons')
def admin_coupons():
    if not admin_required():
        return redirect(url_for('login'))
    # TODO: Implement coupon management
    return render_template('admin_dashboard.html')

@app.route('/admin/approve-store')
def admin_sellers():
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db_connection()
    sellers = []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sellername, selleremail, contactnumber, storename,
                   region, province, city, barangay, status, storelogo_path, businesspermit_path, created_at
            FROM sellers
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        for r in rows:
            sellers.append({
                'id': r[0],
                'sellername': r[1],
                'selleremail': r[2],
                'contactnumber': r[3],
                'storename': r[4],
                'region': r[5],
                'province': r[6],
                'city': r[7],
                'barangay': r[8],
                'status': r[9],
                'storelogo_path': r[10],
                'businesspermit_path': r[11],
                'created_at': r[12]
            })
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass
    return render_template('admin_sellers.html', sellers=sellers)


@app.route('/admin/sellers/<int:seller_id>/update', methods=['POST'])
def admin_update_seller(seller_id):
    if not admin_required():
        # for AJAX return JSON, for normal requests redirect to login
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'msg': 'Unauthorized'}), 403
        return redirect(url_for('login'))

    action = request.form.get('action')  # 'approve' or 'reject'
    if action not in ('approve', 'reject'):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'msg': 'Invalid action'}), 400
        flash('Invalid action', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_status = 'approved' if action == 'approve' else 'rejected'
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sellers
            SET status = %s, reviewed_at = %s, reviewer_id = %s
            WHERE id = %s
        """, (new_status, datetime.utcnow(), 0, seller_id))  # reviewer_id 0 = admin
        conn.commit()
    except Exception as e:
        app.logger.exception("Failed to update seller status")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'msg': 'DB error'}), 500
        flash('Database error updating seller', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    # If request is AJAX/fetch return JSON, otherwise redirect to admin dashboard
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'status': new_status}), 200

    flash(f'Seller has been {new_status}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/uploads/<path:filename>')
def admin_uploaded_file(filename):
    # Only admin may download business permits
    if not admin_required():
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
# ...existing code...

@app.route('/all-products')
def all_products():
    return render_template('all-products.html')

# Route to fetch regions
@app.route('/get_regions')
def get_regions():
    try:
        res = requests.get("https://psgc.gitlab.io/api/regions/", timeout=6)
        res.raise_for_status()
        data = res.json()
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch regions', 'details': str(e)}), 500

# Route to fetch provinces by region code
@app.route('/get_provinces/<region>')
def get_provinces(region):
    try:
        res = requests.get(f"https://psgc.gitlab.io/api/regions/{region}/provinces/", timeout=6)
        res.raise_for_status()
        data = res.json()
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch provinces', 'details': str(e)}), 500

# Route to fetch cities by province code
@app.route('/get_cities/<province>')
def get_cities(province):
    try:
        res = requests.get(f"https://psgc.gitlab.io/api/provinces/{province}/cities-municipalities/", timeout=6)
        res.raise_for_status()
        data = res.json()
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch cities', 'details': str(e)}), 500

# Route to fetch barangays by city/municipality code
@app.route('/get_city/<city>')
def get_city(city):
    try:
        res = requests.get(f"https://psgc.gitlab.io/api/cities-municipalities/{city}/barangays/", timeout=6)
        res.raise_for_status()
        data = res.json()
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch barangays', 'details': str(e)}), 500

@app.route('/get_barangay/<barangay>')
def get_barangay(barangay):
    try:
        res = requests.get(f"https://psgc.gitlab.io/api/cities-municipalities/{barangay}/barangays/", timeout=6)
        res.raise_for_status()
        data = res.json()
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch barangays', 'details': str(e)}), 500

# Upload configuration (place after app = Flask(...))
UPLOAD_DIR = os.path.join(parent_dir, 'uploads')   # c:\Users\admin\Documents\BabyStore\uploads
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024   # 5 MB limit
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOC_EXT = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

# Serve uploads (for business permit consider additional auth checks)
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # optional: restrict access to authenticated users
    # user = session.get('user'); if not user: redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/get_barangays/<city>')
def get_barangays(city):
    try:
        url = f"https://psgc.gitlab.io/api/cities-municipalities/{city}/barangays/"
        res = requests.get(url, timeout=6)
        res.raise_for_status()
        data = res.json()
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        app.logger.exception("Failed to fetch barangays")
        return jsonify({'error': 'Failed to fetch barangays', 'details': str(e)}), 500

@app.route('/seller_login', methods=['GET', 'POST'])
def seller_login():
    # seller-only authentication (robust to different column names)
    if request.method == 'POST':
        selleremail = (request.form.get('selleremail') or '').strip()
        password = request.form.get('sellerpassword') or ''
        remember = bool(request.form.get('remember'))

        if not selleremail or not password:
            flash('Please provide both email and password', 'error')
            return render_template('seller_login.html')

        conn = get_db_connection()
        if not conn:
            flash('Server error (db)', 'error')
            return render_template('seller_login.html')

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM sellers WHERE selleremail = %s LIMIT 1", (selleremail,))
            row = cursor.fetchone()
        except Exception:
            app.logger.exception("Seller login DB error")
            flash('Server error, please try later', 'error')
            return render_template('seller_login.html')
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        if not row:
            flash('Invalid credentials', 'error')
            return render_template('seller_login.html')

        # tolerant column resolution for hashed password & status
        hashed_pw = row.get('password') or row.get('sellerpassword') or row.get('passwd') or row.get('pwd') or ''
        status = row.get('status') or row.get('account_status') or 'approved'

        # status check
        if status != 'approved':
            flash('Seller account not approved yet', 'error')
            return render_template('seller_login.html')

        # verify password
        if not hashed_pw or not check_password_hash(hashed_pw, password):
            flash('Invalid credentials', 'error')
            return render_template('seller_login.html')

        # success: set seller session and redirect to seller dashboard
        user_id = row.get('id') or row.get('sellerID') or row.get('seller_id')
        user_name = row.get('sellername') or row.get('storename') or row.get('seller_name')
        session.clear()
        session['seller'] = {'id': user_id, 'name': user_name, 'email': selleremail}
        if remember:
            session.permanent = True

        flash('Signed in successfully', 'success')
        return redirect(url_for('seller_dashboard'))

    return render_template('seller_login.html')


@app.route('/baby-clothes')
def baby_clothes():
    return render_template('categories/baby-clothes.html')

@app.route('/comfort-toys')
def comfort_toys():
    return render_template('categories/comfort-toys.html')

@app.route('/educational-toys')
def educational_toys():
    return render_template('categories/educational-toys.html')

@app.route('/nursery-furniture')
def nursery_furniture():
    return render_template('categories/nursery-furniture.html')

@app.route('/safety-and-health')
def safety_and_health():
    return render_template('categories/safety-and-health.html')

@app.route('/stroller-gear')
def stroller_gear():
    return render_template('categories/stroller-gear.html')

@app.route('/admin/profile')
def admin_profile():
    if not admin_required():
        return redirect(url_for('login'))
    user = session.get('user') or {}
    return render_template('admin_profile.html', user=user)

@app.route('/api/admin/sellers')
def api_admin_sellers():
    if not admin_required():
        return jsonify({'error': 'unauthorized'}), 403
    conn = get_db_connection()
    sellers = []
    try:
        # use dictionary cursor so we can safely read columns by name
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, sellername, selleremail, contactnumber, storename, storedesc,
                   region, province, city, barangay, status, storelogo_path, businesspermit_path, created_at
            FROM sellers
            ORDER BY id DESC
        """)
        for row in cursor.fetchall():
            sellers.append({
              'id': row.get('id'),
              'sellername': row.get('sellername'),
              'selleremail': row.get('selleremail'),
              'contactnumber': row.get('contactnumber'),
              'storename': row.get('storename'),
              'storedesc': row.get('storedesc') or '',
              'region': row.get('region'),
              'province': row.get('province'),
              'city': row.get('city'),
              'barangay': row.get('barangay'),
              'status': row.get('status'),
              'storelogo_path': row.get('storelogo_path'),
              'businesspermit_path': row.get('businesspermit_path'),
              'created_at': str(row.get('created_at')) if row.get('created_at') else None
            })
    finally:
        try:
            cursor.close(); conn.close()
        except Exception:
            pass
    return jsonify(sellers)

@app.route('/seller-dashboard')
def seller_dashboard():
    return render_template('seller_dashboard.html')