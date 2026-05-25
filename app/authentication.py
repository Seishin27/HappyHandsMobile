from flask import Flask, render_template, request, redirect, url_for
from flask import flash, session, jsonify, make_response, abort, g, has_app_context
from jinja2 import ChoiceLoader, FileSystemLoader, TemplateNotFound
from jinja2.loaders import BaseLoader
import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt, decode_token,
    set_access_cookies, unset_jwt_cookies
)
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import requests
import uuid
import json
from werkzeug.utils import secure_filename
from flask import send_from_directory
from dotenv import load_dotenv
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from threading import Thread
import time
import secrets
from functools import wraps
# Removed duplicate current_app import
import random
import re
import math
from typing import Optional
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
except Exception:
    pass
from app import chat, chat_routes, chat_socket, admin_support
from app.chat_models import build_human_room_name
from app.mobile_api import api_bp
from app.shipping_utils import DEFAULT_SHIPPING_FEE, estimate_shipping_fee

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "happyhands929@gmail.com"
ADMIN_PASSWORD = "happyhands929"
generate_hash_password = ADMIN_PASSWORD
ADMIN_COMPLIANCE_EMAIL = "happyhands929@gmail.com"

def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

DB_HOST = os.environ.get('HH_DB_HOST', 'localhost')
DB_PORT = _safe_int(os.environ.get('HH_DB_PORT', '3306'), 3306)
DB_USER = os.environ.get('HH_DB_USER', 'root')
DB_PASSWORD = os.environ.get('HH_DB_PASSWORD', '')
DB_NAME = os.environ.get('HH_DB_NAME') or os.environ.get('BABYSTORE_DB') or 'babystore'

_SELLER_ORDER_ITEMS_READY = False
_SELLER_ORDER_ITEMS_ERROR_CODES = {
    getattr(errorcode, 'ER_NO_SUCH_TABLE', 1146),
    1932,
}

# Get the parent directory (project root)
parent_dir = PROJECT_ROOT
UPLOAD_DIR = os.path.join(parent_dir, 'uploads')

DEFAULT_CATEGORY_CHOICES = [
    {'id': 11, 'categoryID': 11, 'category_id': 11, 'name': 'Baby Clothes', 'slug': 'baby-clothes'},
    {'id': 15, 'categoryID': 15, 'category_id': 15, 'name': 'Comfort Toys', 'slug': 'comfort-toys'},
    {'id': 16, 'categoryID': 16, 'category_id': 16, 'name': 'Educational Toys', 'slug': 'educational-toys'},
    {'id': 17, 'categoryID': 17, 'category_id': 17, 'name': 'Stollers & Gears', 'slug': 'stollers-gears'},
    {'id': 19, 'categoryID': 19, 'category_id': 19, 'name': 'Safety and Health', 'slug': 'safety-and-health'},
    {'id': 20, 'categoryID': 20, 'category_id': 20, 'name': 'Nursery Furniture', 'slug': 'nursery-furniture'},
]

CATEGORY_PAGE_SIZE = max(1, _safe_int(os.environ.get('HH_CATEGORY_PAGE_SIZE', '12'), 12))
CATEGORY_PAGE_MAX = max(CATEGORY_PAGE_SIZE, _safe_int(os.environ.get('HH_CATEGORY_PAGE_MAX', '60'), 60))
FEATURED_PAGE_SIZE = 12


def _extract_product_image_list(product):
    """Return the list of stored image filenames for a product row."""
    if not isinstance(product, dict):
        return []

    raw_value = (
        product.get('image_path')
        or product.get('image')
        or product.get('main_image')
        or product.get('imageurl')
    )
    if not raw_value or not isinstance(raw_value, str):
        return []

    return [segment.strip() for segment in raw_value.split(',') if segment.strip()]


def _select_primary_product_image(product):
    """Return the first image filename for a product row."""
    parts = _extract_product_image_list(product)
    return parts[0] if parts else None


def _load_featured_products(cursor, conn, requested_page, per_page):
    """Fetch paginated featured products with fallbacks for the homepage/API."""
    per_page = max(1, int(per_page or FEATURED_PAGE_SIZE))
    try:
        page = max(1, int(requested_page or 1))
    except (TypeError, ValueError):
        page = 1

    payload = {
        'products': [],
        'page': page,
        'total_pages': 1,
        'total_products': 0,
    }

    if not cursor:
        return payload

    def _calc_pagination(count):
        if count <= 0:
            return 1, 1, 0
        pages = max(1, math.ceil(count / per_page))
        safe_page = max(1, min(page, pages))
        offset = (safe_page - 1) * per_page
        return safe_page, pages, offset

    records = []
    total_products = 0
    safe_page = page
    total_pages = 1

    featured_count = 0
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM featured_products WHERE status = 'approved'")
        featured_count = int((cursor.fetchone() or {}).get('cnt') or 0)
    except Exception:
        featured_count = 0

    if featured_count > 0:
        safe_page, total_pages, offset = _calc_pagination(featured_count)
        total_products = featured_count
        try:
            cursor.execute(
                """
                SELECT p.*
                FROM products p
                JOIN featured_products f ON f.productID = p.productID AND f.status = 'approved'
                ORDER BY p.productID DESC
                LIMIT %s OFFSET %s
                """,
                (per_page, offset)
            )
            records = cursor.fetchall() or []

            # FALLBACK: If no records returned (orphaned featured_products), get all products instead
            if not records:
                try:
                    cursor.execute("SELECT COUNT(*) AS cnt FROM products")
                    total_products = int((cursor.fetchone() or {}).get('cnt') or 0)
                    safe_page, total_pages, offset = _calc_pagination(total_products)
                    cursor.execute(
                        "SELECT * FROM products ORDER BY productID DESC LIMIT %s OFFSET %s",
                        (per_page, offset)
                    )
                    records = cursor.fetchall() or []
                except Exception:
                    records = []
        except Exception:
            records = []
    else:
        fallback_count = 0
        try:
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM products p
                WHERE NOT EXISTS (
                    SELECT 1 FROM featured_products f WHERE f.productID = p.productID
                )
                """
            )
            fallback_count = int((cursor.fetchone() or {}).get('cnt') or 0)
        except Exception:
            fallback_count = 0

        if fallback_count <= 0:
            try:
                cursor.execute("SELECT COUNT(*) AS cnt FROM products")
                fallback_count = int((cursor.fetchone() or {}).get('cnt') or 0)
            except Exception:
                fallback_count = 0

        total_products = fallback_count
        if fallback_count > 0:
            safe_page, total_pages, offset = _calc_pagination(fallback_count)
            try:
                cursor.execute(
                    """
                    SELECT p.*
                    FROM products p
                    WHERE NOT EXISTS (
                        SELECT 1 FROM featured_products f WHERE f.productID = p.productID
                    )
                    ORDER BY p.productID DESC
                    LIMIT %s OFFSET %s
                    """,
                    (per_page, offset)
                )
                records = cursor.fetchall() or []
            except Exception:
                try:
                    cursor.execute(
                        "SELECT * FROM products ORDER BY productID DESC LIMIT %s OFFSET %s",
                        (per_page, offset)
                    )
                    records = cursor.fetchall() or []
                except Exception:
                    records = []
        else:
            safe_page, total_pages, _ = _calc_pagination(0)
            try:
                cursor.execute("SELECT * FROM products ORDER BY productID DESC LIMIT %s", (per_page,))
                records = cursor.fetchall() or []
                total_products = len(records)
            except Exception:
                records = []

    try:
        records = _filter_out_frozen_products(conn, records)
    except Exception:
        pass

    payload['products'] = records or []
    payload['page'] = safe_page
    payload['total_pages'] = total_pages
    payload['total_products'] = total_products
    return payload

# Discover all 'templates' and 'static' directories under project root so
# templates and static assets still resolve after reorganizing into per-user folders.
template_dirs = []
static_dirs = []

for root, dirs, files in os.walk(parent_dir):
    if 'templates' in dirs:
        template_dirs.append(os.path.join(root, 'templates'))
    if 'static' in dirs:
        static_dirs.append(os.path.join(root, 'static'))

# ensure the common top-level templates/static are first in the search order
top_templates = os.path.join(parent_dir, 'templates')
if top_templates not in template_dirs:
    template_dirs.insert(0, top_templates)
top_static = os.path.join(parent_dir, 'static')
if top_static not in static_dirs:
    static_dirs.insert(0, top_static)

# Clean up lists and fallback to sensible defaults
template_dirs = [p for p in template_dirs if os.path.isdir(p)]
static_dirs = [p for p in static_dirs if os.path.isdir(p)]
if not template_dirs:
    template_dirs = [os.path.join(parent_dir, 'templates')]
if not static_dirs:
    static_dirs = [os.path.join(parent_dir, 'static')]

# Create Flask app using the first static dir as app.static_folder (optional),
# but configure Jinja to search all discovered template dirs.
app = Flask(__name__, static_folder=static_dirs[0] if static_dirs and os.path.isdir(static_dirs[0]) else None)


@app.route('/favicon.ico')
def serve_favicon():
    """Serve a fallback favicon so browsers stop emitting 404 noise."""
    icon_dir = os.path.join(parent_dir, 'static', 'images')
    icon_file = 'toy1.png'
    try:
        return send_from_directory(icon_dir, icon_file)
    except FileNotFoundError:
        return ('', 204)

class FuzzyFilenameLoader(BaseLoader):
    """Loader that first tries normal resolution (ChoiceLoader), then
    falls back to searching each template directory for a file matching the
    requested template's basename. This preserves existing render_template
    calls that reference filenames without subpaths after reorganizing templates
    into subfolders.
    """
    def __init__(self, dirs):
        self.dirs = list(dirs)
        self.choice = ChoiceLoader([FileSystemLoader(d) for d in self.dirs])

    def get_source(self, environment, template):
        # Try normal resolution first
        try:
            return self.choice.get_source(environment, template)
        except Exception:
            # Fallback: find a file whose basename matches template
            name = os.path.basename(template)
            for base in self.dirs:
                for root, _dirs, files in os.walk(base):
                    if name in files:
                        rel = os.path.relpath(os.path.join(root, name), base).replace('\\', '/')
                        return FileSystemLoader(base).get_source(environment, rel)
        raise TemplateNotFound(template)

    def list_templates(self):
        # Delegate to ChoiceLoader for listing (good enough)
        try:
            return self.choice.list_templates()
        except Exception:
            return []


app.jinja_loader = FuzzyFilenameLoader(template_dirs)

@app.route('/static/<path:filename>')
def multi_static(filename):
    """Serve static files from any discovered static directories (first match wins)."""
    for d in static_dirs:
        try:
            full = os.path.join(d, filename)
            if os.path.exists(full):
                return send_from_directory(d, filename)
        except Exception:
            pass
    abort(404)
app.secret_key = 'your-secret-key-here'
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string')
app.config['UPLOAD_FOLDER'] = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)

# Mobile-friendly JWT: accept Authorization: Bearer <token>
# (Existing cookie-based flows can still work, but mobile clients should use headers.)
app.config.setdefault('JWT_TOKEN_LOCATION', ['headers', 'cookies'])
app.config.setdefault('JWT_HEADER_NAME', 'Authorization')
app.config.setdefault('JWT_HEADER_TYPE', 'Bearer')

# Token lifetimes for mobile clients
from datetime import timedelta
app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))
app.config.setdefault('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))

# Disable JSON pretty printing
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# CORS for mobile integration — allow all origins on API, uploads, static, and auth routes
CORS(app, resources={
    r"/api/*":       {"origins": "*", "allow_headers": ["Content-Type", "Authorization", "Accept"],
                      "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]},
    r"/uploads/*":   {"origins": "*"},
    r"/static/*":    {"origins": "*"},
    r"/seller/*":    {"origins": "*", "allow_headers": ["Content-Type", "Authorization", "Accept"],
                      "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]},
    r"/rider/*":     {"origins": "*", "allow_headers": ["Content-Type", "Authorization", "Accept"],
                      "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]},
    r"/socket.io/*": {"origins": "*"},
})

# Register mobile REST API blueprint
app.register_blueprint(api_bp)

# API-only mode for mobile deployments: disable all HTML/template routes.
# To avoid accidental lockout during local dev, this requires BOTH:
# - HH_API_ONLY=1 (or true/yes/on)
# - HH_API_ONLY_CONFIRM=YES
@app.before_request
def _api_only_guard():
    try:
        api_only = str(os.environ.get('HH_API_ONLY', '0')).strip().lower() in ('1', 'true', 'yes', 'on')
        confirmed = str(os.environ.get('HH_API_ONLY_CONFIRM', '')).strip().upper() == 'YES'
    except Exception:
        api_only = False
        confirmed = False
    if not (api_only and confirmed):
        return None
    path = request.path or ''
    if path.startswith('/api/'):
        return None
    # Allow static/uploads so product images can still be loaded.
    if path.startswith('/static/') or path.startswith('/uploads/') or path == '/favicon.ico':
        return None
    return jsonify({
        "status": "error",
        "message": "API-only mode enabled",
        "data": {"hint": "Use /api/* endpoints"},
    }), 404

# Mail config — read from environment (.env). Defaults preserve previous
# hardcoded behavior so existing local setups keep working.
def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ('1', 'true', 'yes', 'on')

app.config['MAIL_SERVER']   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT']     = _safe_int(os.environ.get('MAIL_PORT', '587'), 587)
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'johnpaulbajao50@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'vrfz hkco hqxp pisf')
app.config['MAIL_USE_TLS']  = _bool_env('MAIL_USE_TLS', True)
app.config['MAIL_USE_SSL']  = _bool_env('MAIL_USE_SSL', False)
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get(
    'MAIL_DEFAULT_SENDER',
    'Happy Hands PH <johnpaulbajao50@gmail.com>',
)

mail = Mail(app)

# Simple in-memory caches for performance
EMAIL_EXISTS_CACHE = {}
EMAIL_EXISTS_CACHE_TTL = 60
PW_RESET_SEND_STATUS = {}

# Mobile API: stateless OTP storage keyed by email
API_PW_RESET_OTPS = {}
# Structure: {email: {otp, expires_iso, user_type, attempts, rate: {count, window_start_iso, last_send_iso}}}

# Mobile API: verified reset tokens keyed by UUID
API_PW_RESET_TOKENS = {}
# Structure: {token: {email, user_type, expires_iso}}

from collections import deque
EMAIL_QUEUE = deque()
EMAIL_WORKER_STARTED = False

def _is_test_mode() -> bool:
    try:
        return bool(app.config.get('TESTING')) or ('PYTEST_CURRENT_TEST' in os.environ)
    except Exception:
        return False

def _validate_email_address(addr: str) -> bool:
    try:
        if not isinstance(addr, str):
            return False
        s = addr.strip()
        if not s or '@' not in s or len(s) > 254:
            return False
        import re as _re
        return bool(_re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", s))
    except Exception:
        return False

def _send_email_direct(subject: str, recipients: list[str], body: str, html: str | None = None) -> tuple[bool, str | None, int]:
    t0 = time.perf_counter()
    try:
        if not recipients or not all(_validate_email_address(r) for r in recipients):
            dt = max(int((time.perf_counter() - t0) * 1000), 1)
            return False, 'invalid_recipient', dt
        with app.app_context():
            msg = Message(subject, recipients=recipients)
            if html:
                msg.html = html
            msg.body = body
            mail.send(msg)
        dt = max(int((time.perf_counter() - t0) * 1000), 1)
        return True, None, dt
    except Exception as e:
        dt = max(int((time.perf_counter() - t0) * 1000), 1)
        try: app.logger.error(f"email error: {e}")
        except Exception: pass
        return False, str(e), dt

def _email_worker():
    while True:
        try:
            job = EMAIL_QUEUE.popleft()
        except IndexError:
            time.sleep(0.1)
            continue
        subject = job.get('subject')
        recipients = job.get('recipients')
        body = job.get('body')
        html = job.get('html')
        attempts = int(job.get('attempts') or 0)
        ok, err, dt = _send_email_direct(subject, recipients, body, html)
        try:
            app.logger.info(f"email_send attempt={attempts+1} to={recipients} provider={app.config.get('MAIL_SERVER')} ms={dt} ok={ok} err={err}")
        except Exception:
            pass
        if not ok and attempts < 2:
            backoff = min(2 ** attempts, 8)
            time.sleep(backoff)
            job['attempts'] = attempts + 1
            EMAIL_QUEUE.append(job)

def _ensure_email_worker():
    global EMAIL_WORKER_STARTED
    if _is_test_mode():
        return
    if EMAIL_WORKER_STARTED:
        return
    try:
        Thread(target=_email_worker, daemon=True).start()
        EMAIL_WORKER_STARTED = True
    except Exception:
        EMAIL_WORKER_STARTED = False

def enqueue_email(subject: str, recipients: list[str], body: str, html: str | None = None):
    _ensure_email_worker()
    EMAIL_QUEUE.append({'subject': subject, 'recipients': recipients, 'body': body, 'html': html, 'attempts': 0})

def _cache_email_exists(email: str, exists: bool):
    try:
        EMAIL_EXISTS_CACHE[email.lower()] = {'exists': bool(exists), 'ts': time.time()}
    except Exception:
        pass

def _get_cached_email_exists(email: str):
    try:
        rec = EMAIL_EXISTS_CACHE.get(email.lower())
        if not rec:
            return None
        if (time.time() - float(rec.get('ts') or 0)) > EMAIL_EXISTS_CACHE_TTL:
            return None
        return bool(rec.get('exists'))
    except Exception:
        return None

def start_async_otp_email(target_email: str, otp_code: str):
    PW_RESET_SEND_STATUS[target_email] = {'status': 'pending', 'ms': None, 'error_code': None, 'ts': time.time()}
    def _runner():
        t0 = time.perf_counter()
        ok, err_code = send_otp_email(target_email, otp_code)
        dt_ms = int((time.perf_counter() - t0) * 1000)
        PW_RESET_SEND_STATUS[target_email] = {'status': ('sent' if ok else 'error'), 'ms': dt_ms, 'error_code': err_code, 'ts': time.time()}
    try:
        Thread(target=_runner, daemon=True).start()
    except Exception:
        try:
            ok, err_code = send_otp_email(target_email, otp_code)
            PW_RESET_SEND_STATUS[target_email] = {'status': ('sent' if ok else 'error'), 'ms': None, 'error_code': err_code, 'ts': time.time()}
        except Exception:
            PW_RESET_SEND_STATUS[target_email] = {'status': 'error', 'ms': None, 'error_code': 'unknown', 'ts': time.time()}

app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  
# Mobile + browser support:
# - Mobile clients: Authorization: Bearer <token>
# - Browser flows: cookies (legacy)
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
# Keep the cookie name consistent with other places in the code (we read/write 'access_token')
# flask_jwt_extended defaults to 'access_token_cookie', but earlier code sets/reads
# a cookie named 'access_token', so configure the manager to use that name.
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
# For development on HTTP set to False. In production set True and serve over HTTPS.
app.config['JWT_COOKIE_SECURE'] = False
# Whether CSRF protection for cookies is enabled. For simplicity keep False for now and enable later.
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'

ROLE_COOKIE_META = {
    'user': {'name': 'user_session', 'js_access': False},
    'admin': {'name': 'admin_session', 'js_access': False},
    'seller': {'name': 'seller_session', 'js_access': True},
    'rider': {'name': 'rider_session', 'js_access': False},
}

ROLE_SESSION_KEYS = {
    'user': ('user', 'user_id', 'user_type', 'user_token', 'user_session'),
    'admin': ('admin', 'admin_session'),
    'seller': ('seller', 'seller_id', 'seller_token', 'seller_session'),
    'rider': ('rider', 'rider_id', 'rider_token', 'rider_session'),
}


def _set_role_cookie(resp, role, value, *, max_age=None):
    meta = ROLE_COOKIE_META.get(role)
    if not resp or not meta or value is None:
        return resp
    try:
        resp.set_cookie(
            meta['name'],
            value,
            httponly=not meta.get('js_access', False),
            secure=app.config.get('JWT_COOKIE_SECURE', False),
            samesite=app.config.get('JWT_COOKIE_SAMESITE', 'Lax'),
            max_age=max_age,
            path='/',
        )
    except Exception:
        pass
    return resp


def _clear_role_cookie(resp, role):
    meta = ROLE_COOKIE_META.get(role)
    if not resp or not meta:
        return resp
    try:
        resp.delete_cookie(meta['name'], path='/')
    except Exception:
        pass
    return resp


def _set_active_role(role, active=True):
    try:
        roles = set(session.get('active_roles') or [])
        if active:
            roles.add(role)
        else:
            roles.discard(role)
        session['active_roles'] = list(roles)
        session.modified = True
    except Exception:
        pass


def _clear_role_session(role):
    try:
        for key in ROLE_SESSION_KEYS.get(role, ()):  # type: ignore[arg-type]
            session.pop(key, None)
        _set_active_role(role, active=False)
    except Exception:
        pass


def _current_admin_id():
    try:
        admin_obj = session.get('admin') or {}
        admin_id = admin_obj.get('adminID') or admin_obj.get('id') or admin_obj.get('userID')
        if admin_id is None:
            return None
        return int(admin_id)
    except Exception:
        return None

def admin_required(fn=None):
    """Admin access helper.

    Can be used either as a decorator::

        @admin_required
        def view(): ...

    or as a boolean check::

        if not admin_required():
            return redirect(url_for('login'))
    """

    def _is_admin():
        try:
            admin_obj = session.get('admin') or {}
            if admin_obj:
                aid = admin_obj.get('adminID') or admin_obj.get('id') or admin_obj.get('userID')
                if aid is not None:
                    return True
                username = admin_obj.get('username')
                email = admin_obj.get('email')
                if username == ADMIN_USERNAME or email == ADMIN_EMAIL:
                    return True

            # Primary convention from WARP: session.get('userID') == 0
            if session.get('user_type') == 'admin':
                return True
            if session.get('userID') == 0:
                return True
            user = session.get('user') or {}
            uid = user.get('userID') or user.get('id')
            if uid == 0:
                return True
            email = user.get('email')
            username = user.get('username') or user.get('name')
            if email and email == ADMIN_EMAIL:
                return True
            if username and username == ADMIN_USERNAME:
                return True
            return False
        except Exception:
            return False

    # When called with no function, behave as a plain boolean check
    if fn is None:
        return _is_admin()

    @wraps(fn)
    def _wrapped(*args, **kwargs):
        if not _is_admin():
            return redirect(url_for('login'))
        return fn(*args, **kwargs)

    return _wrapped


def rider_required(fn=None):
    """Decorator / boolean check for authenticated riders.

    Can be used as a boolean check::

        if not rider_required():
            return redirect(url_for('rider_login'))

    Or as a decorator on view functions. For API endpoints (path starts with
    '/api/') the decorator returns a JSON 401. For page views it redirects to
    the rider login page.
    """

    def _is_rider():
        try:
            rid = _get_rider_id_from_session()
            return bool(rid)
        except Exception:
            return False

    # When called as a boolean check
    if fn is None:
        return _is_rider()

    @wraps(fn)
    def _wrapped(*args, **kwargs):
        try:
            if not _is_rider():
                # For API endpoints return JSON 401 to match existing handlers
                try:
                    if request.path.startswith('/api/') or request.headers.get('Accept','').lower().find('application/json') != -1:
                        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
                except Exception:
                    pass
                return redirect(url_for('rider_login'))
            return fn(*args, **kwargs)
        except Exception:
            # Fail closed: treat exceptions as unauthorized to avoid leaking data
            try:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
            except Exception:
                pass
            return redirect(url_for('rider_login'))

    return _wrapped

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    upload_root = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)
    normalized = _normalize_upload_reference(filename)
    if not normalized:
        abort(404)
    return send_from_directory(upload_root, normalized)


@app.route('/admin/uploads/<path:filename>')
@admin_required
def admin_uploaded_file(filename):
    upload_root = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)
    return send_from_directory(upload_root, filename)


# Allowed extensions for common upload types used across the app
# Keep these sets here so template handlers and upload validators can reference them
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOC_EXT = {'pdf', 'png', 'jpg', 'jpeg'}
USER_ID_KEYS = ('userID', 'userid', 'id', 'user_id')
USER_AVATAR_COLUMNS = ('profile_path', 'avatar', 'avatar_path', 'image', 'profile_pic', 'picture')


def allowed_file(filename: str, allowed_exts) -> bool:
    """Return True if `filename` has an extension included in `allowed_exts`.

    `allowed_exts` may be a set/list/tuple or a comma-separated string.
    """
    try:
        if not filename or '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        if isinstance(allowed_exts, str):
            allowed = {x.strip().lower() for x in allowed_exts.split(',') if x.strip()}
        else:
            allowed = set(allowed_exts or [])
        return ext in allowed
    except Exception:
        return False


def _resolve_user_id_from_identity(identity):
    """Best-effort helper to pull a numeric user id from identity/session payloads."""
    def _coerce(value):
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return value

    candidates = []
    if isinstance(identity, dict):
        candidates.append(identity)
        nested = identity.get('user')
        if isinstance(nested, dict):
            candidates.append(nested)
    for candidate in candidates:
        for key in USER_ID_KEYS:
            if candidate.get(key) is not None:
                return _coerce(candidate.get(key))

    if isinstance(identity, str) and identity.isdigit():
        return int(identity)

    try:
        sess_user = session.get('user') or {}
        for key in USER_ID_KEYS:
            if sess_user.get(key) is not None:
                return _coerce(sess_user.get(key))
    except Exception:
        pass
    return None


def _avatar_url_from_path(path_value):
    return _build_upload_url(path_value)


def _build_user_payload_from_row(row):
    """Convert a DB row from `users` into the dict shape templates expect."""
    if not row:
        return {}
    lowered = {k.lower(): v for k, v in row.items() if isinstance(k, str)}
    payload = {}

    for key in USER_ID_KEYS:
        key_l = key.lower()
        if key_l in lowered and lowered[key_l] is not None:
            payload['userID'] = lowered[key_l]
            break

    username = lowered.get('username') or lowered.get('name')
    if username:
        payload['username'] = username

    email = lowered.get('email')
    if email:
        payload['email'] = email

    avatar_path = None
    for column in USER_AVATAR_COLUMNS:
        if column in lowered and lowered[column]:
            avatar_path = lowered[column]
            if column == 'profile_path':
                payload['profile_path'] = lowered[column]
            break

    if avatar_path:
        avatar_url = _avatar_url_from_path(avatar_path)
        if avatar_url:
            payload['avatar'] = avatar_url

    return payload


def _normalize_upload_reference(raw_value):
    """Return a sanitized upload reference or fully qualified URL."""
    if not raw_value:
        return None
    if isinstance(raw_value, (list, tuple, set)):
        for entry in raw_value:
            normalized = _normalize_upload_reference(entry)
            if normalized:
                return normalized
        return None
    if isinstance(raw_value, dict):
        for key in ('url', 'path', 'image', 'image_path', 'main_image', 'image0', 'image1', 'image2', 'image3'):
            if key in raw_value:
                normalized = _normalize_upload_reference(raw_value.get(key))
                if normalized:
                    return normalized
        return None
    candidate = str(raw_value).strip()
    if not candidate:
        return None
    candidate = candidate.replace('\\', '/')
    # Attempt to parse JSON-style payloads like ["img1","img2"] or {"url":"foo"}
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, (list, tuple, set)):
            return _normalize_upload_reference(parsed)
        if isinstance(parsed, dict):
            return _normalize_upload_reference(parsed)
        if isinstance(parsed, str):
            candidate = parsed.strip()
    except Exception:
        pass
    # Strip common wrapping characters
    if candidate.startswith('[') and candidate.endswith(']'):
        inner = candidate[1:-1]
        return _normalize_upload_reference(inner)
    if candidate.startswith('(') and candidate.endswith(')'):
        inner = candidate[1:-1]
        return _normalize_upload_reference(inner)
    if candidate.startswith('{') and candidate.endswith('}'):
        inner = candidate[1:-1]
        return _normalize_upload_reference(inner)
    for sep in (',', '|', ';'):
        if sep in candidate:
            first = candidate.split(sep)[0].strip()
            normalized = _normalize_upload_reference(first)
            if normalized:
                return normalized
    candidate = candidate.strip(' "\'')
    if not candidate or candidate.lower() in ('none', 'null'):
        return None
    if candidate.startswith(('http://', 'https://', '/uploads/', '/static/')):
        return candidate
    if ',' in candidate:
        candidate = candidate.split(',')[0].strip()
    while candidate.startswith('./'):
        candidate = candidate[2:].lstrip()
    while candidate.startswith('../'):
        candidate = candidate[3:].lstrip()
    candidate = candidate.lstrip('/')
    if candidate.startswith('uploads/'):
        candidate = candidate[len('uploads/'):]
    return candidate or None


def _build_upload_url(path_value, *, fallback=None, require_exists=False):
    normalized = _normalize_upload_reference(path_value)
    if not normalized:
        return fallback
    if normalized.startswith(('http://', 'https://', '/uploads/', '/static/')):
        return normalized
    upload_root = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)
    if require_exists:
        try:
            full_path = os.path.join(upload_root, normalized)
            if not os.path.exists(full_path):
                return fallback
        except Exception:
            return fallback
    try:
        return url_for('uploaded_file', filename=normalized)
    except Exception:
        return fallback


def _fetch_user_row(user_id):
    if not user_id:
        return None
    conn = get_db_connection()
    if not conn:
        return None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE userID = %s LIMIT 1', (user_id,))
        return cursor.fetchone()
    except Exception:
        try:
            app.logger.debug('Failed to load user profile data', exc_info=True)
        except Exception:
            pass
        return None
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn and getattr(conn, 'is_connected', lambda: False)():
                conn.close()
        except Exception:
            pass


def _get_rider_id_from_session():
    """Return an integer rider id from session['rider'] supporting multiple key names.

    This helper tolerates different session shapes produced elsewhere in the
    codebase and returns None when no authenticated rider is present.
    """
    # First, try JWT (mobile) when present
    try:
        token = _get_request_jwt_token()
    except Exception:
        token = None
    if token:
        try:
            decoded = decode_token(token)
            identity = extract_identity_from_decoded(decoded)
            candidates = []
            if isinstance(identity, dict):
                candidates.append(identity)
                maybe_nested = identity.get('rider')
                if isinstance(maybe_nested, dict):
                    candidates.append(maybe_nested)
            for candidate in candidates:
                for key in ('riderID', 'riderId', 'rider_id', 'id'):
                    if candidate.get(key) is not None:
                        try:
                            return int(candidate.get(key))
                        except Exception:
                            pass
        except Exception:
            pass

    try:
        rider = session.get('rider')
        if not rider:
            return None
        rid = rider.get('id') or rider.get('riderID') or rider.get('riderId') or rider.get('rider_id')
        if rid is None:
            return None
        try:
            return int(rid)
        except Exception:
            return None
    except Exception:
        return None


def _normalize_session_rider(
    rider_id=None,
    ridername=None,
    rideremail=None,
    status=None,
    image_path=None,
    profile_path=None,
):
    """Ensure session['rider'] contains a consistent set of keys used across views.

    Does not modify other session values. Returns the normalized dict.
    """
    try:
        r = session.get('rider') or {}
        if rider_id is not None:
            r['id'] = rider_id
            r['riderID'] = rider_id
        if ridername is not None:
            r['ridername'] = ridername
            r['name'] = ridername
        if rideremail is not None:
            r['rideremail'] = rideremail
            r['email'] = rideremail
        if status is not None:
            r['status'] = status
        if profile_path is not None:
            r['profile_path'] = profile_path
        if image_path is not None:
            r['image_path'] = image_path
        session['rider'] = r
        session.modified = True
        return r
    except Exception:
        return session.get('rider')


_RIDER_RESPONSE_AUDIT_READY = False
_SELLER_STATUS_ENUM_READY = False

def _ensure_rider_response_audit_table():
    """Create rider_response_audit table when first needed (no-op on failure)."""
    global _RIDER_RESPONSE_AUDIT_READY
    if _RIDER_RESPONSE_AUDIT_READY:
        return
    conn = get_db_connection()
    if not conn:
        return
    cur = None
    try:
        cur = conn.cursor(buffered=True)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rider_response_audit (
                id INT AUTO_INCREMENT PRIMARY KEY,
                riderID INT NOT NULL,
                sellerOrderID INT NOT NULL,
                action ENUM('accept','decline') NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY idx_rider_day (riderID, created_at),
                KEY idx_order (sellerOrderID)
            ) ENGINE=InnoDB
        """)
        conn.commit()
        _RIDER_RESPONSE_AUDIT_READY = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            app.logger.exception('Failed to ensure rider_response_audit table')
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def _log_rider_response(conn, rider_id, seller_order_id, action):
    """Best-effort audit log for rider accept/decline events."""
    cur = None
    try:
        _ensure_rider_response_audit_table()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO rider_response_audit (riderID, sellerOrderID, action) VALUES (%s, %s, %s)",
            (rider_id, seller_order_id, action)
        )
        try:
            conn.commit()
        except Exception:
            pass
    except Exception:
        try:
            app.logger.debug('Failed to log rider response', exc_info=True)
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass


def _filter_out_frozen_products(conn, products):
    """Remove products that belong to frozen sellers from public listings."""
    if not products or not conn:
        return products

    seller_ids = []
    for item in products:
        if not isinstance(item, dict):
            continue
        candidate = item.get('sellerID') or item.get('seller_id') or item.get('sellerId') or item.get('sellerid')
        if candidate is None:
            continue
        try:
            seller_ids.append(int(candidate))
        except (TypeError, ValueError):
            continue

    if not seller_ids:
        return products

    unique_ids = sorted({sid for sid in seller_ids if sid})
    if not unique_ids:
        return products

    status_map = {}
    cur = None
    meta_cur = None
    try:
        meta_cur = conn.cursor()
        meta_cur.execute("SHOW COLUMNS FROM sellers")
        seller_cols = [row[0] for row in (meta_cur.fetchall() or [])]
        id_col = None
        status_col = None
        for col in seller_cols:
            name_lower = (col or '').lower()
            if not id_col and name_lower in ('sellerid', 'seller_id', 'id'):
                id_col = col
            if not status_col and name_lower == 'status':
                status_col = col
        if not id_col or not status_col:
            return products

        placeholders = ','.join(['%s'] * len(unique_ids))
        cur = conn.cursor()
        cur.execute(
            f"SELECT {id_col}, {status_col} FROM sellers WHERE {id_col} IN ({placeholders})",
            tuple(unique_ids)
        )
        for row in cur.fetchall() or []:
            try:
                seller_id = int(row[0]) if row[0] is not None else None
            except (TypeError, ValueError):
                seller_id = None
            if seller_id is None:
                continue
            status_val = row[1] if len(row) > 1 else None
            status_map[seller_id] = (status_val or '').lower()
    except Exception:
        try:
            app.logger.debug('Failed to filter frozen sellers from product list', exc_info=True)
        except Exception:
            pass
        return products
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if meta_cur:
                meta_cur.close()
        except Exception:
            pass

    filtered = []
    for item in products:
        if not isinstance(item, dict):
            filtered.append(item)
            continue
        candidate = item.get('sellerID') or item.get('seller_id') or item.get('sellerId') or item.get('sellerid')
        sid = None
        try:
            sid = int(candidate)
        except (TypeError, ValueError):
            sid = None
        if sid and status_map.get(sid) == 'frozen':
            continue
        filtered.append(item)

    return filtered

def _ensure_seller_order_status_enum():
    """Ensure seller_orders.status enum supports all runtime statuses."""
    global _SELLER_STATUS_ENUM_READY
    if _SELLER_STATUS_ENUM_READY:
        return
    conn = get_db_connection()
    if not conn:
        return
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SHOW COLUMNS FROM seller_orders LIKE 'status'")
        row = cur.fetchone()
        column_type = None
        if row:
            # MySQL connector returns tuples by default; Type is index 1
            try:
                column_type = row[1]
            except Exception:
                try:
                    column_type = row.get('Type')
                except Exception:
                    column_type = None
        target_values = ['pending','packing','packed','assigned_to_rider','picked_up','on_the_way','delivered','cancelled']
        needs_alter = False
        if not column_type:
            needs_alter = True
        else:
            lowered = column_type.lower()
            for val in target_values:
                if f"'{val.lower()}'" not in lowered:
                    needs_alter = True
                    break
        if needs_alter:
            cur.execute("""
                ALTER TABLE seller_orders
                MODIFY status ENUM('pending','packing','packed','assigned_to_rider','picked_up','on_the_way','delivered','cancelled')
                NOT NULL DEFAULT 'pending'
            """)
            conn.commit()
        _SELLER_STATUS_ENUM_READY = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            app.logger.exception('Failed to ensure seller_orders.status enum')
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def _release_financials_for_order(conn, seller_order_id, context_note=None):
    """Release commissions/admin share for a delivered order once the buyer confirms receipt.

    Returns (released: bool, error: str | None).
    Relies on the caller to manage transactions/commit.
    """
    if not conn:
        return False, 'no_connection'

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT sellerOrderID, userID, sellerID, riderID, total_amount,
                   revenue_released, buyer_received
            FROM seller_orders
            WHERE sellerOrderID = %s
            LIMIT 1
            """,
            (seller_order_id,)
        )
        order_row = cur.fetchone()
        if not order_row:
            return False, 'not_found'
        if order_row.get('revenue_released'):
            return False, 'already_released'

        total_amount = Decimal(str(order_row.get('total_amount') or '0'))
        seller_id = order_row.get('sellerID')
        rider_id = order_row.get('riderID')

        # Commission rules (eventually centralize to config)
        COMMISSION_RATE = Decimal('0.05')
        PLATFORM_FEE_RATE = Decimal('0.02')
        RIDER_FLAT = Decimal('30.00')

        seller_commission = (total_amount * COMMISSION_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        rider_commission = RIDER_FLAT
        platform_fee = (total_amount * PLATFORM_FEE_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        seller_net = (total_amount - platform_fee - seller_commission).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        admin_share = (seller_commission + rider_commission + platform_fee).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        note_fragments = ['auto: released after buyer confirmation']
        if context_note:
            note_fragments.append(str(context_note))
        note_text = ' | '.join(note_fragments)

        # Avoid duplicate rows in financial_transactions
        try:
            cur.execute("SELECT id FROM financial_transactions WHERE order_id = %s LIMIT 1", (seller_order_id,))
            already_logged = cur.fetchone() is not None
        except Exception:
            already_logged = False

        if not already_logged:
            try:
                cur.execute(
                    """
                    INSERT INTO financial_transactions (
                        order_id, seller_id, rider_id, total_amount,
                        seller_commission, rider_commission, admin_share,
                        vat_amount, seller_net, note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        seller_order_id,
                        seller_id,
                        rider_id,
                        str(total_amount),
                        str(seller_commission),
                        str(rider_commission),
                        str(admin_share),
                        str(platform_fee),
                        str(seller_net),
                        note_text
                    )
                )
            except Exception:
                try:
                    cur.execute(
                        """
                        INSERT INTO financial_transactions (
                            order_id, seller_id, rider_id, total_amount,
                            seller_commission, rider_commission, admin_share, note
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            seller_order_id,
                            seller_id,
                            rider_id,
                            str(total_amount),
                            str(seller_commission),
                            str(rider_commission),
                            str(admin_share),
                            note_text
                        )
                    )
                except Exception:
                    app.logger.debug('financial_transactions insert failed for order %s', seller_order_id, exc_info=True)

        # Mark order as released
        try:
            cur.execute(
                "UPDATE seller_orders SET revenue_released = 1, revenue_released_at = NOW() WHERE sellerOrderID = %s",
                (seller_order_id,)
            )
        except Exception:
            app.logger.debug('Failed to flag revenue release for order %s', seller_order_id, exc_info=True)

        # Update platform stats (best-effort)
        try:
            stats_cur = conn.cursor()
            stats_cur.execute(
                "UPDATE platform_stats SET total_revenue = total_revenue + %s, total_orders = total_orders + 1 WHERE id = 1",
                (str(admin_share),)
            )
            stats_cur.close()
        except Exception:
            pass

        message_suffix = ''
        if seller_net is not None:
            message_suffix = f" Net to seller ₱{seller_net:.2f}"

        if seller_id:
            try:
                body = f"Order #{seller_order_id}: Total ₱{total_amount:.2f} • Platform Fee(2%) ₱{platform_fee:.2f}.{message_suffix}"
                cur.execute(
                    "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)",
                    (seller_id, 'Sale completed', body)
                )
                emit_notification_event('seller', seller_id, 'Sale completed', body)
            except Exception:
                app.logger.debug('Failed to notify seller for order %s release', seller_order_id, exc_info=True)

        if rider_id:
            try:
                rider_msg = f"Order #{seller_order_id}: Delivery earnings released. Rider commission ₱{rider_commission:.2f}."
                cur.execute(
                    "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('rider', %s, %s, %s)",
                    (rider_id, 'Delivery completed', rider_msg)
                )
                emit_notification_event('rider', rider_id, 'Delivery completed', rider_msg)
            except Exception:
                app.logger.debug('Failed to notify rider for order %s release', seller_order_id, exc_info=True)

        try:
            admin_msg = f"Order #{seller_order_id}: Platform Fee(2%) ₱{platform_fee:.2f} from total ₱{total_amount:.2f}"
            cur.execute(
                "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('admin', %s, %s, %s)",
                (0, 'Platform Fee collected', admin_msg)
            )
            emit_notification_event('admin', 0, 'Platform Fee collected', admin_msg)
        except Exception:
            pass

        return True, None
    except Exception:
        raise
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
def _normalize_int(val):
    try:
        if val is None:
            return None
        s = str(val).strip()
        if not s:
            return None
        if s.isdigit() or (s[0] == '-' and s[1:].isdigit()):
            return int(s)
    except Exception:
        return val
    return val


def _validate_user_seller_chat(user_id, seller_id, product_id=None):
    user_id = _normalize_int(user_id)
    seller_id = _normalize_int(seller_id)
    product_id = _normalize_int(product_id)
    if user_id is None or seller_id is None:
        return False, 'missing_ids'
    conn = get_db_connection()
    if not conn:
        return False, 'db_error'
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if product_id is not None:
            row = None
            try:
                cur.execute("SELECT sellerID FROM products WHERE productID = %s LIMIT 1", (product_id,))
                row = cur.fetchone()
            except Exception:
                row = None
            if not row:
                return False, 'product_not_found'
            try:
                owner = _normalize_int(row.get('sellerID'))
            except Exception:
                owner = None
            if owner is None or owner != seller_id:
                return False, 'seller_not_owner_of_product'
            return True, 'ok'
        row = None
        try:
            cur.execute("SELECT 1 FROM seller_orders WHERE userID = %s AND sellerID = %s LIMIT 1", (user_id, seller_id))
            row = cur.fetchone()
        except Exception:
            row = None
        if row:
            return True, 'ok'
        # Fallback: allow chat when there is at least one legacy chats row
        # between this user and seller, even if no seller_orders record
        # exists (e.g., pre-purchase product inquiries).
        try:
            cur.execute("SELECT 1 FROM chats WHERE userID = %s AND sellerID = %s LIMIT 1", (user_id, seller_id))
            row = cur.fetchone()
        except Exception:
            row = None
        if row:
            return True, 'ok'
        return False, 'no_related_order'
    except Exception:
        try:
            app.logger.exception('user/seller chat validation failed')
        except Exception:
            pass
        return False, 'exception'
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _rider_order_accepted(conn, rider_id, seller_order_id):
    rider_id = _normalize_int(rider_id)
    seller_order_id = _normalize_int(seller_order_id)
    if rider_id is None or seller_order_id is None:
        return False
    cur = None
    accepted = False
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT status FROM seller_orders WHERE sellerOrderID = %s AND riderID = %s LIMIT 1",
                (seller_order_id, rider_id),
            )
            row = cur.fetchone()
        except Exception:
            row = None
        if row:
            status = str(row.get('status') or '').lower()
            if status in ('assigned_to_rider', 'picked_up', 'on_the_way', 'delivered'):
                accepted = True
        if not accepted:
            try:
                _ensure_rider_response_audit_table()
            except Exception:
                pass
            try:
                cur.execute(
                    "SELECT action FROM rider_response_audit WHERE riderID = %s AND sellerOrderID = %s ORDER BY created_at DESC LIMIT 1",
                    (rider_id, seller_order_id),
                )
                rec = cur.fetchone()
            except Exception:
                rec = None
            if rec and str(rec.get('action') or '').lower() == 'accept':
                accepted = True
    except Exception:
        try:
            app.logger.exception('rider order acceptance check failed')
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
    return accepted


def _validate_user_rider_chat(user_id, rider_id, seller_order_id):
    user_id = _normalize_int(user_id)
    rider_id = _normalize_int(rider_id)
    seller_order_id = _normalize_int(seller_order_id)
    if user_id is None or rider_id is None or seller_order_id is None:
        return False, 'missing_ids'
    conn = get_db_connection()
    if not conn:
        return False, 'db_error'
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT userID, riderID, status FROM seller_orders WHERE sellerOrderID = %s LIMIT 1",
                (seller_order_id,),
            )
            row = cur.fetchone()
        except Exception:
            row = None
        if not row:
            return False, 'order_not_found'
        order_user = _normalize_int(row.get('userID'))
        order_rider = _normalize_int(row.get('riderID'))
        if order_user != user_id:
            return False, 'user_not_order_owner'
        if order_rider != rider_id:
            return False, 'rider_not_assigned'
        if not _rider_order_accepted(conn, rider_id, seller_order_id):
            return False, 'rider_not_accepted'
        return True, 'ok'
    except Exception:
        try:
            app.logger.exception('user/rider chat validation failed')
        except Exception:
            pass
        return False, 'exception'
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _validate_rider_seller_chat(rider_id, seller_id, seller_order_id):
    rider_id = _normalize_int(rider_id)
    seller_id = _normalize_int(seller_id)
    seller_order_id = _normalize_int(seller_order_id)
    if rider_id is None or seller_id is None:
        return False, 'missing_ids'
    conn = get_db_connection()
    if not conn:
        return False, 'db_error'
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if seller_order_id is not None:
            try:
                cur.execute(
                    "SELECT sellerID, riderID FROM seller_orders WHERE sellerOrderID = %s LIMIT 1",
                    (seller_order_id,),
                )
                row = cur.fetchone()
            except Exception:
                row = None
            if not row:
                return False, 'order_not_found'
            order_seller = _normalize_int(row.get('sellerID'))
            order_rider = _normalize_int(row.get('riderID'))
            if order_seller != seller_id:
                return False, 'seller_not_order_owner'
            if order_rider != rider_id:
                return False, 'rider_not_assigned'
            # Allow messaging immediately even if acceptance is still pending to let parties coordinate
            return True, 'ok'

        # Fallback path for legacy chats without an explicit sellerOrderID.
        matched_order_id = None
        try:
            cur.execute(
                "SELECT sellerOrderID FROM seller_orders WHERE riderID = %s AND sellerID = %s ORDER BY updated_at DESC LIMIT 1",
                (rider_id, seller_id),
            )
            alt_row = cur.fetchone()
        except Exception:
            alt_row = None
        if alt_row:
            matched_order_id = _normalize_int(alt_row.get('sellerOrderID'))
            if matched_order_id is not None:
                return True, 'ok'

        try:
            cur.execute("SHOW COLUMNS FROM chats LIKE 'riderID'")
            has_rider_col = bool(cur.fetchone())
        except Exception:
            has_rider_col = False

        legacy_chat = None
        if has_rider_col:
            try:
                cur.execute(
                    "SELECT 1 FROM chats WHERE riderID = %s AND sellerID = %s LIMIT 1",
                    (rider_id, seller_id),
                )
                legacy_chat = cur.fetchone()
            except Exception:
                legacy_chat = None
        if not legacy_chat:
            # Handle legacy schemas that recorded rider conversations without a riderID column
            try:
                cur.execute("SHOW COLUMNS FROM chats LIKE 'sender_role'")
                has_sender_role = bool(cur.fetchone())
            except Exception:
                has_sender_role = False
            if has_sender_role:
                try:
                    cur.execute(
                        "SELECT 1 FROM chats WHERE sellerID = %s AND sender_role IN ('rider','seller') AND (userID IS NULL OR userID = 0) ORDER BY chatID DESC LIMIT 1",
                        (seller_id,),
                    )
                    legacy_chat = cur.fetchone()
                except Exception:
                    legacy_chat = None
        if legacy_chat:
            return True, 'ok'
        return False, 'missing_order_context'
    except Exception:
        try:
            app.logger.exception('rider/seller chat validation failed')
        except Exception:
            pass
        return False, 'exception'
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _validate_rider_user_chat(rider_id, user_id, seller_order_id):
    rider_id = _normalize_int(rider_id)
    user_id = _normalize_int(user_id)
    seller_order_id = _normalize_int(seller_order_id)
    if rider_id is None or user_id is None or seller_order_id is None:
        return False, 'missing_ids'
    conn = get_db_connection()
    if not conn:
        return False, 'db_error'
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT userID, riderID, status FROM seller_orders WHERE sellerOrderID = %s LIMIT 1",
                (seller_order_id,),
            )
            row = cur.fetchone()
        except Exception:
            row = None
        if not row:
            return False, 'order_not_found'
        order_user = _normalize_int(row.get('userID'))
        order_rider = _normalize_int(row.get('riderID'))
        if order_user != user_id:
            return False, 'user_not_order_owner'
        if order_rider != rider_id:
            return False, 'rider_not_assigned'
        if not _rider_order_accepted(conn, rider_id, seller_order_id):
            return False, 'rider_not_accepted'
        return True, 'ok'
    except Exception:
        try:
            app.logger.exception('rider/user chat validation failed')
        except Exception:
            pass
        return False, 'exception'
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _validate_legacy_chat_pair(sender_role, sender_id, recipient_role, recipient_id, product_id=None):
    sr = (sender_role or '').lower()
    rr = (recipient_role or '').lower()
    sender_id = _normalize_int(sender_id)
    recipient_id = _normalize_int(recipient_id)
    product_id = _normalize_int(product_id)
    result = {
        'ok': False,
        'reason': None,
        'kind': None,
        'room': None,
        'sender_role': sr,
        'sender_id': sender_id,
        'recipient_role': rr,
        'recipient_id': recipient_id,
    }
    allowed = {('user', 'seller'), ('seller', 'user'), ('user', 'rider'), ('rider', 'user'), ('rider', 'seller'), ('seller', 'rider')}
    if (sr, rr) not in allowed and (rr, sr) not in allowed:
        result['reason'] = 'pair_not_allowed'
        return result
    try:
        room = build_human_room_name(sr, sender_id, rr, recipient_id)
    except Exception:
        room = None
    result['room'] = room
    if {sr, rr} == {'user', 'seller'}:
        user_id = sender_id if sr == 'user' else recipient_id
        seller_id = sender_id if sr == 'seller' else recipient_id
        ok, reason = _validate_user_seller_chat(user_id, seller_id, product_id)
        result['ok'] = ok
        result['reason'] = reason
        result['kind'] = 'user_seller'
        return result
    if {sr, rr} == {'user', 'rider'}:
        user_id = sender_id if sr == 'user' else recipient_id
        rider_id = sender_id if sr == 'rider' else recipient_id
        ok, reason = _validate_user_rider_chat(user_id, rider_id, product_id)
        result['ok'] = ok
        result['reason'] = reason
        result['kind'] = 'user_rider'
        return result
    if {sr, rr} == {'rider', 'seller'}:
        rider_id = sender_id if sr == 'rider' else recipient_id
        seller_id = sender_id if sr == 'seller' else recipient_id
        ok, reason = _validate_rider_seller_chat(rider_id, seller_id, product_id)
        result['ok'] = ok
        result['reason'] = reason
        result['kind'] = 'rider_seller'
        return result
    result['ok'] = False
    result['reason'] = 'unsupported_pair'
    return result


jwt = JWTManager(app)

# Initialize Socket.IO for real-time chat
# Uses 'threading' async mode by default to avoid requiring eventlet/gevent in dev.
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')
chat_socket.register_chat_socket_handlers(socketio)
app.register_blueprint(chat_routes.chat_bp)
app.register_blueprint(admin_support.support_bp)
try:
    from app.reports_api import reports_bp
    if 'reports' not in app.blueprints:
        app.register_blueprint(reports_bp)
except Exception:
    app.logger.exception("Failed to register reports blueprint")

# Mapping of connected identities to socket ids. Key format: "role:id" e.g. "user:123" or "seller:45"
# Value is a set of socket session ids (sids). Used to deliver private messages to online clients.
connected_users = {}
legacy_sid_identity = {}


@app.before_request
def enforce_seller_restrictions():
    seller = session.get('seller') or {}
    seller_id = seller.get('sellerID') or seller.get('id')
    if not seller_id:
        return
    path = request.path or ''
    if not (path.startswith('/seller') or path.startswith('/seller-')):
        return

    state = _load_seller_restriction_state(seller_id)
    g.seller_restriction_state = state
    if not state:
        return

    level = state.get('level') or 0
    if level < 3:
        return

    allowed_paths = {
        '/seller/dashboard',
        '/seller-dashboard',
        '/seller/restrictions/explanation',
        '/seller/restrictions/appeal',
    }
    allowed_prefixes = ('/seller/restrictions',)
    if path in allowed_paths or any(path.startswith(prefix) for prefix in allowed_prefixes):
        return
    if path in ('/seller-logout', '/logout', '/seller/logout'):
        return

    if request.method.upper() == 'GET':
        return redirect(url_for('seller_dashboard'))

    return jsonify({'success': False, 'msg': 'restricted'}), 403

def emit_notification_event(recipient_type, recipient_id, title, body, extra=None):
    if not recipient_type or recipient_id is None:
        return
    try:
        room = f'{recipient_type}_{recipient_id}'
        payload = {
            'recipient_type': recipient_type,
            'recipient_id': recipient_id,
            'title': title,
            'body': body,
            'created_at': datetime.utcnow().isoformat()
        }
        if isinstance(extra, dict):
            payload.update(extra)
        socketio.emit('notification', payload, room=room)
    except Exception:
        try:
            app.logger.debug('emit_notification_event failed', exc_info=True)
        except Exception:
            pass

BLOCKLIST = set()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload.get('jti')
    return jti in BLOCKLIST

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        try:
            _ensure_seller_order_items_table(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            raise
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None
    except Exception as err:
        print(f"Database setup error: {err}")
        return None

def ensure_database_exists():
    """Ensure the BabyStore database exists before table creation.
    Uses root connection without selecting a database.
    """
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cur.close()
        conn.close()
    except Exception as e:
        # Log but do not raise to avoid breaking startup; routes will surface DB issues
        try:
            app.logger.warning(f"ensure_database_exists: {e}")
        except Exception:
            print(f"ensure_database_exists: {e}")


def _ensure_seller_order_items_table(conn):
    """Ensure the seller_order_items table exists and is readable on this connection."""
    global _SELLER_ORDER_ITEMS_READY
    if _SELLER_ORDER_ITEMS_READY or not conn:
        return

    def _create(cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `seller_order_items` (
              `itemID` int(11) NOT NULL AUTO_INCREMENT,
              `sellerOrderID` int(11) NOT NULL,
              `productID` int(11) NOT NULL,
              `quantity` int(11) NOT NULL,
              `price` decimal(10,2) NOT NULL,
              `total_price` decimal(10,2) NOT NULL,
              `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
              PRIMARY KEY (`itemID`),
              KEY `idx_seller_order` (`sellerOrderID`),
              KEY `idx_product` (`productID`),
              CONSTRAINT `fk_seller_order_items_order` FOREIGN KEY (`sellerOrderID`) REFERENCES `seller_orders` (`sellerOrderID`) ON DELETE CASCADE,
              CONSTRAINT `fk_seller_order_items_product` FOREIGN KEY (`productID`) REFERENCES `products` (`productID`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
            """
        )

    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            LIMIT 1
            """,
            ('seller_order_items',)
        )
        exists = cur.fetchone() is not None
        if not exists:
            _create(cur)
        else:
            try:
                cur.execute("SELECT 1 FROM seller_order_items LIMIT 1")
                cur.fetchall() # Consume result
            except mysql.connector.Error as err:
                if getattr(err, 'errno', None) in _SELLER_ORDER_ITEMS_ERROR_CODES:
                    try:
                        app.logger.warning(
                            "seller_order_items inaccessible; recreating table (existing data may be unavailable): %s",
                            err,
                        )
                    except Exception:
                        print(
                            "seller_order_items inaccessible; recreating table (existing data may be unavailable):",
                            err,
                        )
                    cur.execute("DROP TABLE IF EXISTS seller_order_items")
                    _create(cur)
                else:
                    raise
        _SELLER_ORDER_ITEMS_READY = True
    except mysql.connector.Error as err:
        message = f"_ensure_seller_order_items_table failed: {err}"
        try:
            app.logger.warning(message)
        except Exception:
            print(message)
        # Propagate so callers know setup is incomplete
        raise
    finally:
        if cur:
            cur.close()


def _slugify_category_name(name):
    try:
        if not name or not isinstance(name, str):
            return None
        slug = re.sub(r'[^a-z0-9]+', '-', name.strip().lower()).strip('-')
        return slug or None
    except Exception:
        return None


def _normalize_category_rows(rows):
    normalized = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        raw_id = row.get('categoryID') or row.get('category_id') or row.get('id')
        name = row.get('name') or row.get('category_name')
        if raw_id is None or not name:
            continue
        try:
            cat_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        slug = row.get('slug') or _slugify_category_name(name)
        normalized.append({
            'categoryID': cat_id,
            'category_id': cat_id,
            'id': cat_id,
            'name': name,
            'slug': slug,
        })
    return normalized


def _split_legacy_category_string(raw):
    if not raw:
        return []
    try:
        parts = [segment.strip() for segment in str(raw).split(',')]
        return [p for p in parts if p]
    except Exception:
        return []


def _fetch_all_categories(conn):
    rows = []
    cur = None
    if conn:
        cur = None
        try:
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute("SELECT categoryID, name, slug FROM categories ORDER BY name ASC")
            except mysql.connector.Error as err:
                if getattr(err, 'errno', None) == errorcode.ER_BAD_FIELD_ERROR:
                    cur.execute("SELECT categoryID, name FROM categories ORDER BY name ASC")
                else:
                    raise
            rows = cur.fetchall() or []
        except mysql.connector.Error as err:
            if getattr(err, 'errno', None) == errorcode.ER_NO_SUCH_TABLE:
                try:
                    app.logger.warning('categories table missing; using fallback list')
                except Exception:
                    pass
            else:
                try:
                    app.logger.debug('Failed to load categories', exc_info=True)
                except Exception:
                    pass
        except Exception:
            try:
                app.logger.debug('Failed to load categories', exc_info=True)
            except Exception:
                pass
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
    if rows:
        return _normalize_category_rows(rows)
    return [c.copy() for c in DEFAULT_CATEGORY_CHOICES]


def _fetch_seller_allowed_categories(conn, seller_id, fallback_to_all=False):
    if not conn or not seller_id:
        return (_fetch_all_categories(conn) if fallback_to_all else []), True

    cur = None
    rows = []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT c.categoryID, c.name, c.slug
            FROM seller_categories sc
            JOIN categories c ON c.categoryID = sc.category_id
            WHERE sc.seller_id = %s
            ORDER BY c.name ASC
            """,
            (seller_id,)
        )
        rows = cur.fetchall() or []
    except mysql.connector.Error as err:
        if getattr(err, 'errno', None) == errorcode.ER_BAD_FIELD_ERROR:
            try:
                cur.execute(
                    """
                    SELECT c.categoryID, c.name, c.slug
                    FROM seller_categories sc
                    JOIN categories c ON c.categoryID = sc.categoryID
                    WHERE sc.sellerID = %s
                    ORDER BY c.name ASC
                    """,
                    (seller_id,)
                )
                rows = cur.fetchall() or []
            except mysql.connector.Error as err2:
                if getattr(err2, 'errno', None) not in (errorcode.ER_NO_SUCH_TABLE, errorcode.ER_BAD_FIELD_ERROR):
                    try:
                        app.logger.debug('Failed to fetch seller category permissions', exc_info=True)
                    except Exception:
                        pass
            except Exception:
                try:
                    app.logger.debug('Failed to fetch seller category permissions', exc_info=True)
                except Exception:
                    pass
        elif getattr(err, 'errno', None) not in (errorcode.ER_NO_SUCH_TABLE, errorcode.ER_BAD_FIELD_ERROR):
            try:
                app.logger.debug('Failed to fetch seller category permissions', exc_info=True)
            except Exception:
                pass
    except Exception:
        try:
            app.logger.debug('Failed to fetch seller category permissions', exc_info=True)
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass

    normalized = _normalize_category_rows(rows)
    if normalized:
        return normalized, False

    legacy_rows = []
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT seller_category FROM sellers WHERE sellerID = %s", (seller_id,))
        legacy_val = (cur.fetchone() or {}).get('seller_category')
        legacy_names = _split_legacy_category_string(legacy_val)
        if legacy_names:
            placeholders = ','.join(['%s'] * len(legacy_names))
            try:
                cur.execute(
                    f"SELECT categoryID, name, slug FROM categories WHERE name IN ({placeholders})",
                    tuple(legacy_names),
                )
            except mysql.connector.Error as err:
                if getattr(err, 'errno', None) == errorcode.ER_BAD_FIELD_ERROR:
                    cur.execute(
                        f"SELECT categoryID, name FROM categories WHERE name IN ({placeholders})",
                        tuple(legacy_names),
                    )
                else:
                    raise
            legacy_rows = cur.fetchall() or []
    except mysql.connector.Error as err:
        if getattr(err, 'errno', None) not in (errorcode.ER_NO_SUCH_TABLE, errorcode.ER_BAD_FIELD_ERROR):
            try:
                app.logger.debug('Failed legacy seller category lookup', exc_info=True)
            except Exception:
                pass
    except Exception:
        try:
            app.logger.debug('Failed legacy seller category lookup', exc_info=True)
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass

    normalized_legacy = _normalize_category_rows(legacy_rows)
    if normalized_legacy:
        return normalized_legacy, True

    if fallback_to_all:
        return _fetch_all_categories(conn), True
    return [], True


def _assign_categories_to_seller(conn, seller_id, category_ids):
    if not conn or not seller_id or not category_ids:
        return
    payload = []
    for cid in category_ids:
        try:
            payload.append((int(seller_id), int(cid)))
        except (TypeError, ValueError):
            continue
    if not payload:
        return

    cur = None
    try:
        cur = conn.cursor()
        try:
            cur.executemany(
                "INSERT IGNORE INTO seller_categories (seller_id, category_id) VALUES (%s, %s)",
                payload,
            )
        except mysql.connector.Error as err:
            if getattr(err, 'errno', None) == errorcode.ER_BAD_FIELD_ERROR:
                cur.executemany(
                    "INSERT IGNORE INTO seller_categories (sellerID, categoryID) VALUES (%s, %s)",
                    payload,
                )
            elif getattr(err, 'errno', None) == errorcode.ER_NO_SUCH_TABLE:
                try:
                    app.logger.warning('seller_categories table missing; run migrations to enable category restrictions')
                except Exception:
                    pass
            else:
                raise
    except mysql.connector.Error as err:
        if getattr(err, 'errno', None) == errorcode.ER_NO_SUCH_TABLE:
            try:
                app.logger.warning('seller_categories table missing; run migrations to enable category restrictions')
            except Exception:
                pass
        else:
            raise
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass

def _ensure_restriction_tables(conn):
    """Create seller restriction helper tables when missing."""
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS seller_restrictions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sellerID INT NOT NULL,
                restriction_type VARCHAR(50),
                restriction_end DATETIME,
                report_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_seller_restriction (sellerID, restriction_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''
        )
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS seller_restriction_responses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sellerID INT NOT NULL,
                report_id INT NULL,
                offense_level INT NOT NULL,
                response_type VARCHAR(20) NOT NULL,
                subject VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                attachment_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''
        )
        conn.commit()
    except Exception:
        try:
            app.logger.debug('ensure restriction tables failed', exc_info=True)
        except Exception:
            pass
    finally:
        try:
            cur.close()
        except Exception:
            pass

    # Bring existing schemas in line when the tables were created earlier without new columns/keys.
    try:
        alter_cur = conn.cursor(buffered=True)
        alter_cur.execute("SHOW COLUMNS FROM seller_restrictions LIKE 'report_id'")
        if not alter_cur.fetchone():
            alter_cur.execute("ALTER TABLE seller_restrictions ADD COLUMN report_id INT NULL AFTER restriction_end")

        alter_cur.execute("SHOW INDEX FROM seller_restrictions WHERE Key_name = 'unique_seller_restriction'")
        if not alter_cur.fetchone():
            alter_cur.execute("ALTER TABLE seller_restrictions ADD UNIQUE KEY unique_seller_restriction (sellerID, restriction_type)")

        conn.commit()
    except Exception:
        try:
            app.logger.debug('ensure restriction table alignment failed', exc_info=True)
        except Exception:
            pass
    finally:
        try:
            alter_cur.close()
        except Exception:
            pass


def _dt_to_iso(value):
    if not value:
        return None
    try:
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)
    except Exception:
        return None


def _ensure_seller_offense_tables(conn):
    """Ensure seller offense history table and seller columns are present."""
    if not conn:
        return

    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS seller_offenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sellerID INT NOT NULL,
                offense_level INT NOT NULL,
                reason TEXT,
                report_id INT NULL,
                applied_by INT NULL,
                auto_reset_days INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                appeal_deadline DATETIME NULL,
                resolved_at DATETIME NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            app.logger.debug('ensure seller_offenses table failed', exc_info=True)
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass

    column_specs = [
        ('offense_level', "INT NOT NULL DEFAULT 0"),
        ('offense_reason', "TEXT NULL"),
        ('offense_last_updated', "DATETIME NULL"),
        ('appeal_deadline', "DATETIME NULL"),
        ('is_frozen', "TINYINT(1) NOT NULL DEFAULT 0"),
    ]

    for column_name, ddl in column_specs:
        check_cur = None
        try:
            check_cur = conn.cursor()
            check_cur.execute("SHOW COLUMNS FROM sellers LIKE %s", (column_name,))
            if not check_cur.fetchone():
                check_cur.execute(f"ALTER TABLE sellers ADD COLUMN {column_name} {ddl}")
                conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                app.logger.debug('ensure sellers.%s column failed', column_name, exc_info=True)
            except Exception:
                pass
        finally:
            try:
                if check_cur:
                    check_cur.close()
            except Exception:
                pass


def _fetch_seller_row(conn, seller_id):
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT sellerID, status, offense_level, offense_reason, offense_last_updated, appeal_deadline, is_frozen FROM sellers WHERE sellerID = %s LIMIT 1",
            (seller_id,)
        )
        return cur.fetchone()
    except Exception:
        try:
            app.logger.debug('fetch seller row failed', exc_info=True)
        except Exception:
            pass
        return None
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass


def _clear_seller_offense_state(conn, seller_id, report_id=None, admin_id=None, reason=None):
    if not conn:
        return None

    _ensure_restriction_tables(conn)
    _ensure_seller_offense_tables(conn)

    cur = None
    try:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM seller_restrictions WHERE sellerID = %s", (seller_id,))
        except Exception:
            try:
                app.logger.debug('clear seller restrictions failed', exc_info=True)
            except Exception:
                pass

        try:
            cur.execute(
                """
                UPDATE sellers
                SET offense_level = 0,
                    offense_reason = NULL,
                    offense_last_updated = NOW(),
                    appeal_deadline = NULL,
                    is_frozen = 0
                WHERE sellerID = %s
                """,
                (seller_id,)
            )
        except Exception:
            try:
                app.logger.debug('clear seller offense columns failed', exc_info=True)
            except Exception:
                pass

        try:
            cur.execute("UPDATE sellers SET status = 'approved' WHERE sellerID = %s", (seller_id,))
        except Exception:
            pass

        try:
            cur.execute(
                """
                UPDATE featured_products f
                JOIN products p ON p.productID = f.productID
                SET f.status = 'approved'
                WHERE p.sellerID = %s AND f.status = 'restricted'
                """,
                (seller_id,)
            )
        except Exception:
            pass

        try:
            cur.execute(
                """
                INSERT INTO seller_offenses (sellerID, offense_level, reason, report_id, applied_by, auto_reset_days, appeal_deadline, resolved_at)
                VALUES (%s, 0, %s, %s, %s, NULL, NULL, NOW())
                """,
                (seller_id, reason, report_id, admin_id)
            )
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
    return None


def delete_seller_and_dependents(seller_id, conn=None):
    """Delete a seller and all linked records in a single transaction.

    The SQL batch executed (one statement at a time) is:

        START TRANSACTION;
        DELETE FROM seller_restriction_responses WHERE sellerID = ?;
        DELETE FROM seller_restrictions WHERE sellerID = ?;
        DELETE FROM seller_offenses WHERE sellerID = ?;
        DELETE FROM seller_categories WHERE seller_id = ?;
        DELETE cm FROM chat_messages cm
            JOIN chat_conversations cc ON cc.conversationID = cm.conversationID
            WHERE cc.sellerID = ?;
        DELETE FROM chat_conversations WHERE sellerID = ?;
        DELETE FROM chats WHERE sellerID = ?;
        DELETE soi FROM seller_order_items soi
            JOIN seller_orders so ON so.sellerOrderID = soi.sellerOrderID
            WHERE so.sellerID = ?;
        DELETE FROM seller_orders WHERE sellerID = ?;
        DELETE FROM products WHERE sellerID = ?;
        DELETE FROM featured_products WHERE sellerID = ?;
        DELETE FROM notifications WHERE recipient_type = 'seller' AND recipient_id = ?;
        DELETE FROM sellers WHERE sellerID = ?;
        COMMIT;

    Returns: (True, None) on success, (False, error_message) on failure.
    """
    manage_conn = False
    if conn is None:
        conn = get_db_connection()
        manage_conn = True

    if not conn:
        return False, 'database_unavailable'

    cur = None
    try:
        cur = conn.cursor()
        try:
            conn.start_transaction()
        except Exception:
            conn.autocommit = False

        statements = (
            "DELETE FROM seller_restriction_responses WHERE sellerID = %s",
            "DELETE FROM seller_restrictions WHERE sellerID = %s",
            "DELETE FROM seller_offenses WHERE sellerID = %s",
            "DELETE FROM seller_categories WHERE seller_id = %s",
            "DELETE cm FROM chat_messages cm JOIN chat_conversations cc ON cc.conversationID = cm.conversationID WHERE cc.sellerID = %s",
            "DELETE FROM chat_conversations WHERE sellerID = %s",
            "DELETE FROM chats WHERE sellerID = %s",
            "DELETE soi FROM seller_order_items soi JOIN seller_orders so ON so.sellerOrderID = soi.sellerOrderID WHERE so.sellerID = %s",
            "DELETE FROM seller_orders WHERE sellerID = %s",
            "DELETE fp FROM featured_products fp JOIN products p ON p.productID = fp.productID WHERE p.sellerID = %s",
            "DELETE FROM products WHERE sellerID = %s",
            "DELETE FROM notifications WHERE recipient_type = 'seller' AND recipient_id = %s",
            "DELETE FROM sellers WHERE sellerID = %s",
        )

        for sql in statements:
            try:
                cur.execute(sql, (seller_id,))
            except mysql.connector.Error as err:
                if getattr(err, 'errno', None) == errorcode.ER_NO_SUCH_TABLE:
                    continue
                if getattr(err, 'errno', None) == errorcode.ER_BAD_FIELD_ERROR and 'seller_categories' in sql:
                    fallback_sql = sql.replace('seller_id', 'sellerID')
                    cur.execute(fallback_sql, (seller_id,))
                    continue
                raise
            except Exception:
                raise

        # Commit transaction
        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return False, 'commit_failed'

        return True, None

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            app.logger.exception('delete_seller_and_dependents failed')
        except Exception:
            pass
        return False, str(e)
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        if manage_conn:
            try:
                conn.close()
            except Exception:
                pass


def delete_rider_and_dependents(rider_id, conn=None):
    """Delete a rider and clean up dependent records."""
    manage_conn = False
    if conn is None:
        conn = get_db_connection()
        manage_conn = True

    if not conn:
        return False, 'database_unavailable'

    cur = None
    try:
        cur = conn.cursor()
        try:
            conn.start_transaction()
        except Exception:
            conn.autocommit = False

        statements = (
            "DELETE FROM rider_response_audit WHERE riderID = %s",
            "DELETE cm FROM chat_messages cm JOIN chat_conversations cc ON cc.conversationID = cm.conversationID WHERE cc.riderID = %s",
            "DELETE FROM chat_conversations WHERE riderID = %s",
            "DELETE FROM chats WHERE riderID = %s",
            "DELETE FROM notifications WHERE recipient_type = 'rider' AND recipient_id = %s",
            "DELETE FROM financial_assistants WHERE riderID = %s",
            "UPDATE seller_orders SET riderID = NULL WHERE riderID = %s",
            "DELETE FROM riders WHERE riderID = %s",
        )

        for sql in statements:
            try:
                cur.execute(sql, (rider_id,))
            except mysql.connector.Error as err:
                if getattr(err, 'errno', None) == errorcode.ER_NO_SUCH_TABLE:
                    continue
                raise
            except Exception:
                raise

        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return False, 'commit_failed'

        return True, None

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            app.logger.exception('delete_rider_and_dependents failed')
        except Exception:
            pass
        return False, str(e)
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        if manage_conn:
            try:
                conn.close()
            except Exception:
                pass


def _auto_reset_seller_offense(conn, seller_id, seller_row):
    if not conn or not seller_row:
        return seller_row, False

    try:
        offense_level = int(seller_row.get('offense_level') or 0)
    except (TypeError, ValueError):
        offense_level = 0

    appeal_deadline = seller_row.get('appeal_deadline')
    if offense_level <= 0 or not appeal_deadline:
        return seller_row, False

    deadline_dt = None
    if hasattr(appeal_deadline, 'isoformat'):
        deadline_dt = appeal_deadline
    elif isinstance(appeal_deadline, str):
        try:
            deadline_dt = datetime.fromisoformat(appeal_deadline)
        except Exception:
            deadline_dt = None

    if not deadline_dt:
        return seller_row, False

    if deadline_dt <= datetime.utcnow():
        _clear_seller_offense_state(
            conn,
            seller_id,
            reason='Automatic offense reset after deadline',
        )
        refreshed = _fetch_seller_row(conn, seller_id) or seller_row
        return refreshed, True

    return seller_row, False


def _apply_seller_offense(conn, seller_id, offense_level, reason=None, report_id=None, admin_id=None, auto_reset_days=None):
    if not conn:
        return {}

    _ensure_restriction_tables(conn)
    _ensure_seller_offense_tables(conn)

    seller_row = _fetch_seller_row(conn, seller_id)
    if not seller_row:
        return {}

    if offense_level <= 0:
        _clear_seller_offense_state(conn, seller_id, report_id=report_id, admin_id=admin_id, reason=reason)
        return _load_seller_restriction_state(seller_id, conn=conn)

    try:
        offense_level = int(offense_level)
    except (TypeError, ValueError):
        offense_level = 0
    offense_level = max(0, min(offense_level, 3))

    try:
        auto_reset_days = int(auto_reset_days) if auto_reset_days not in (None, '') else None
        if auto_reset_days is not None and auto_reset_days < 1:
            auto_reset_days = None
    except (TypeError, ValueError):
        auto_reset_days = None

    appeal_deadline = None
    if auto_reset_days:
        try:
            appeal_deadline = datetime.utcnow() + timedelta(days=auto_reset_days)
        except Exception:
            appeal_deadline = None

    restriction_map = {
        1: 'compliance_warning',
        2: 'post_products',
        3: 'account_frozen',
    }
    restriction_type = restriction_map.get(offense_level)
    is_frozen = offense_level >= 3

    cur = conn.cursor()
    try:
        try:
            cur.execute("DELETE FROM seller_restrictions WHERE sellerID = %s", (seller_id,))
        except Exception:
            pass

        if restriction_type:
            try:
                cur.execute(
                    """
                    INSERT INTO seller_restrictions (sellerID, restriction_type, restriction_end, report_id)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        restriction_type = VALUES(restriction_type),
                        restriction_end = VALUES(restriction_end),
                        report_id = VALUES(report_id)
                    """,
                    (seller_id, restriction_type, appeal_deadline, report_id)
                )
            except Exception:
                cur.execute(
                    """
                    INSERT INTO seller_restrictions (sellerID, restriction_type, restriction_end, report_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (seller_id, restriction_type, appeal_deadline, report_id)
                )

        try:
            cur.execute(
                """
                UPDATE sellers
                SET offense_level = %s,
                    offense_reason = %s,
                    offense_last_updated = NOW(),
                    appeal_deadline = %s,
                    is_frozen = %s
                WHERE sellerID = %s
                """,
                (offense_level, reason, appeal_deadline, 1 if is_frozen else 0, seller_id)
            )
        except Exception:
            cur.execute(
                """
                UPDATE sellers
                SET offense_level = %s,
                    offense_reason = %s,
                    offense_last_updated = NOW(),
                    appeal_deadline = %s
                WHERE sellerID = %s
                """,
                (offense_level, reason, appeal_deadline, seller_id)
            )

        if is_frozen:
            try:
                cur.execute("UPDATE sellers SET status = 'frozen' WHERE sellerID = %s", (seller_id,))
            except Exception:
                pass
            try:
                cur.execute(
                    """
                    UPDATE featured_products f
                    JOIN products p ON p.productID = f.productID
                    SET f.status = 'restricted'
                    WHERE p.sellerID = %s
                    """,
                    (seller_id,)
                )
            except Exception:
                pass
        else:
            try:
                cur.execute("UPDATE sellers SET status = 'restricted' WHERE sellerID = %s", (seller_id,))
            except Exception:
                pass

        try:
            cur.execute(
                """
                INSERT INTO seller_offenses (sellerID, offense_level, reason, report_id, applied_by, auto_reset_days, appeal_deadline)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (seller_id, offense_level, reason, report_id, admin_id, auto_reset_days, appeal_deadline)
            )
        except Exception:
            pass
    finally:
        try:
            cur.close()
        except Exception:
            pass

    return _load_seller_restriction_state(seller_id, conn=conn)


def _load_seller_restriction_state(seller_id, conn=None):
    state = None
    manage_connection = False
    if conn is None:
        conn = get_db_connection()
        manage_connection = True

    if not conn:
        return None

    try:
        _ensure_restriction_tables(conn)
        _ensure_seller_offense_tables(conn)

        seller_row = _fetch_seller_row(conn, seller_id)
        if not seller_row:
            return None

        seller_row, auto_reset_applied = _auto_reset_seller_offense(conn, seller_id, seller_row)
        if auto_reset_applied:
            seller_row = _fetch_seller_row(conn, seller_id) or seller_row

        offense_level = 0
        try:
            offense_level = int(seller_row.get('offense_level') or 0)
        except (TypeError, ValueError):
            offense_level = 0
        offense_reason = seller_row.get('offense_reason')
        offense_last_updated = seller_row.get('offense_last_updated')
        appeal_deadline = seller_row.get('appeal_deadline')
        seller_is_frozen = bool(seller_row.get('is_frozen'))

        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT id, restriction_type, restriction_end, report_id FROM seller_restrictions WHERE sellerID = %s",
                (seller_id,)
            )
            rows = cur.fetchall() or []
        finally:
            try:
                cur.close()
            except Exception:
                pass

        now = datetime.utcnow()
        expired_ids = []
        active_rows = []
        for row in rows:
            end_ts = row.get('restriction_end')
            deadline = None
            if hasattr(end_ts, 'isoformat'):
                deadline = end_ts
            elif isinstance(end_ts, str):
                try:
                    deadline = datetime.fromisoformat(end_ts)
                except Exception:
                    deadline = None
            if deadline and deadline < now:
                expired_ids.append(row.get('id'))
                continue
            active_rows.append(row)

        if expired_ids:
            try:
                cleanup_cur = conn.cursor()
                cleanup_cur.execute(
                    "DELETE FROM seller_restrictions WHERE id IN (" + ','.join(['%s'] * len(expired_ids)) + ")",
                    tuple(expired_ids)
                )
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
            finally:
                try:
                    if 'cleanup_cur' in locals() and cleanup_cur:
                        cleanup_cur.close()
                except Exception:
                    pass

        type_priority = {'account_frozen': 3, 'post_products': 2, 'compliance_warning': 2}
        active_rows.sort(key=lambda r: type_priority.get(r.get('restriction_type'), 0), reverse=True)
        primary = active_rows[0] if active_rows else None
        restriction_level = type_priority.get((primary or {}).get('restriction_type'), 0)

        report = None
        report_id = (primary or {}).get('report_id')
        report_cur = conn.cursor(dictionary=True)
        try:
            if report_id:
                report_cur.execute("SELECT * FROM reports WHERE id = %s LIMIT 1", (report_id,))
                report = report_cur.fetchone()
            if not report:
                report_cur.execute(
                    "SELECT * FROM reports WHERE reported_shop_id = %s ORDER BY created_at DESC LIMIT 1",
                    (seller_id,)
                )
                report = report_cur.fetchone()
                if report and not report_id and primary:
                    try:
                        backfill_cur = conn.cursor()
                        backfill_cur.execute(
                            "UPDATE seller_restrictions SET report_id = %s WHERE id = %s",
                            (report.get('id'), primary.get('id'))
                        )
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    finally:
                        try:
                            if 'backfill_cur' in locals() and backfill_cur:
                                backfill_cur.close()
                        except Exception:
                            pass
        finally:
            try:
                report_cur.close()
            except Exception:
                pass

        resp_cur = conn.cursor(dictionary=True)
        responses = []
        try:
            resp_cur.execute(
                """
                SELECT id, offense_level, response_type, subject, message, attachment_path, created_at
                FROM seller_restriction_responses
                WHERE sellerID = %s
                ORDER BY created_at DESC
                """,
                (seller_id,)
            )
            for resp in resp_cur.fetchall() or []:
                responses.append({
                    'id': resp.get('id'),
                    'offense_level': resp.get('offense_level'),
                    'response_type': resp.get('response_type'),
                    'subject': resp.get('subject'),
                    'message': resp.get('message'),
                    'attachment_path': resp.get('attachment_path'),
                    'created_at': _dt_to_iso(resp.get('created_at')),
                })
        finally:
            try:
                resp_cur.close()
            except Exception:
                pass

        if not active_rows and offense_level <= 0 and not offense_reason and not responses:
            return None

        restriction_end = (primary or {}).get('restriction_end')
        state = {
            'level': max(restriction_level, offense_level),
            'restriction_type': (primary or {}).get('restriction_type'),
            'restriction_end': _dt_to_iso(restriction_end) if restriction_end else None,
            'report_id': (report or {}).get('id') or report_id,
            'report_offense_level': (report or {}).get('offense_level'),
            'report_status': (report or {}).get('status'),
            'responses': responses,
            'contact_email': ADMIN_COMPLIANCE_EMAIL,
            'offense_level': offense_level,
            'offense_reason': offense_reason,
            'offense_last_updated': _dt_to_iso(offense_last_updated),
            'appeal_deadline': _dt_to_iso(appeal_deadline),
            'is_frozen': seller_is_frozen or restriction_level >= 3,
        }

        if not state.get('restriction_end') and state.get('appeal_deadline'):
            state['restriction_end'] = state['appeal_deadline']

        return state
    except Exception:
        try:
            app.logger.debug('load seller restriction state failed', exc_info=True)
        except Exception:
            pass
        return None
    finally:
        if manage_connection:
            try:
                conn.close()
            except Exception:
                pass


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




# Helper to extract identity payload (supports older tokens where sub was dict)
def extract_identity_from_decoded(decoded):
    if not isinstance(decoded, dict):
        return None
    # prefer structured claims placed into additional_claims
    if decoded.get('user') and isinstance(decoded.get('user'), dict):
        return decoded.get('user')
    if decoded.get('seller') and isinstance(decoded.get('seller'), dict):
        return decoded.get('seller')
    if decoded.get('rider') and isinstance(decoded.get('rider'), dict):
        return decoded.get('rider')
    # fallback to sub (may be string or dict)
    sub = decoded.get('sub')
    if isinstance(sub, dict):
        return sub
    # if sub is string (we now use string subjects), return the string; caller can handle it
    return sub


def _get_request_jwt_token():
    """Return JWT string from Authorization header or cookie (if present)."""
    token = None
    try:
        authz = request.headers.get('Authorization') or ''
        if authz.lower().startswith('bearer '):
            token = authz.split(' ', 1)[1].strip()
    except Exception:
        token = None
    if token:
        return token
    try:
        return request.cookies.get(app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token'))
    except Exception:
        return None

def _get_authenticated_seller_id():
    """Best-effort helper to resolve the active seller's ID from either the JWT cookie or the session."""
    seller_id = None
    try:
        token = _get_request_jwt_token()
    except Exception:
        token = None

    if token:
        try:
            decoded = decode_token(token)

            identity = extract_identity_from_decoded(decoded)
            candidates = []
            if isinstance(identity, dict):
                candidates.append(identity)
                # Some tokens may nest seller info under a `seller` key
                maybe_nested = identity.get('seller')
                if isinstance(maybe_nested, dict):
                    candidates.append(maybe_nested)

            for candidate in candidates:
                for key in ('sellerID', 'sellerId', 'seller_id', 'id'):
                    if candidate.get(key) is not None:
                        seller_id = candidate.get(key)
                        break
                if seller_id:
                    break

        except Exception:
            seller_id = None

    if seller_id:
        return seller_id

    seller = session.get('seller') or {}
    for key in ('sellerID', 'sellerId', 'id'):
        if seller.get(key) is not None:
            return seller.get(key)
    return None

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
            if 'avatar' not in sess_user and sess_user.get('profile_path'):
                avatar_url = _avatar_url_from_path(sess_user.get('profile_path'))
                if avatar_url:
                    sess_user['avatar'] = avatar_url
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

        identity = extract_identity_from_decoded(decoded)

        # If identity contains a numeric userID, try to fetch full user info from DB
        if identity and isinstance(identity, dict) and identity.get('userID'):
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute('SELECT * FROM users WHERE userID = %s LIMIT 1', (identity.get('userID'),))
                    row = cursor.fetchone()
                    if row:
                        user_obj = _build_user_payload_from_row(row)
                        if not user_obj:
                            user_obj = {
                                'userID': row.get('userID') or row.get('userid') or row.get('id') or row.get('user_id'),
                                'username': row.get('username') or row.get('name'),
                                'email': row.get('email')
                            }
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

        # Fallback: expose whatever structured identity was in the token (dict) or string subject
        return {'user': identity}

    except Exception:
        # Any decoding error (expired/invalid) -> treat as anonymous
        return {}


@app.route('/api/change-password', methods=['POST'])
def change_password():
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({'success': False, 'msg': 'Not logged in'}), 401

    try:
        decoded = decode_token(token)
        identity = extract_identity_from_decoded(decoded)
    except Exception:
        return jsonify({'success': False, 'msg': 'Invalid token'}), 401

    if not identity:
        return jsonify({'success': False, 'msg': 'User not found'}), 404

    user_id = None
    if isinstance(identity, dict):
        user_id = identity.get('userID') or identity.get('id')
    elif isinstance(identity, str) and identity.isdigit():
        user_id = int(identity)

    if not user_id:
        return jsonify({'success': False, 'msg': 'User ID not found'}), 400

    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'msg': 'All fields are required'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'msg': 'New passwords do not match'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database error'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE userID = %s", (user_id,))
        user = cur.fetchone()

        if not user:
            return jsonify({'success': False, 'msg': 'User not found in DB'}), 404

        # Check if password is correct
        hashed = user.get('password') or user.get('passwd') or ''
        if not hashed:
             return jsonify({'success': False, 'msg': 'User has no password set'}), 400
             
        if not check_password_hash(hashed, current_password):
            return jsonify({'success': False, 'msg': 'Incorrect current password'}), 400

        hashed_password = generate_password_hash(new_password)
        # Update password column (assuming it is 'password')
        cur.execute("UPDATE users SET password = %s WHERE userID = %s", (hashed_password, user_id))
        conn.commit()
        
        return jsonify({'success': True, 'msg': 'Password updated successfully'})

    except Exception as e:
        app.logger.error(f"Error changing password: {e}")
        return jsonify({'success': False, 'msg': 'An error occurred'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Require login via access_token cookie

    token = request.cookies.get('access_token') if request.cookies else None
    if not token:
        return redirect(url_for('login'))

    try:
        decoded = decode_token(token)
        identity = extract_identity_from_decoded(decoded)
    except Exception:
        identity = None

    if not identity:
        return redirect(url_for('login'))

    if not isinstance(identity, dict):
        identity = {}

    try:
        sess_user = session.get('user')
        if sess_user and isinstance(sess_user, dict):
            merged = dict(identity)
            merged.update(sess_user)
            identity = merged
    except Exception:
        pass

    user_id = _resolve_user_id_from_identity(identity)
    if user_id and isinstance(identity, dict):
        identity.setdefault('userID', user_id)

    needs_avatar_data = user_id and (not identity.get('avatar') or not identity.get('profile_path'))
    if needs_avatar_data:
        hydrated_row = _fetch_user_row(user_id)
        hydrated_payload = _build_user_payload_from_row(hydrated_row)
        if hydrated_payload:
            identity.update(hydrated_payload)
            try:
                sess_user = session.get('user') or {}
                sess_user.update(hydrated_payload)
                session['user'] = sess_user
            except Exception:
                pass

    # On POST: handle profile updates (username, email, avatar upload)
    if request.method == 'POST':
        new_username = (request.form.get('username') or '').strip()
        new_email = (request.form.get('email') or '').strip()
        avatar_file = request.files.get('avatar') if request.files else None

        # Basic validation
        if not new_username or not new_email:
            flash('Please provide both name and email', 'danger')
            return render_template('profile.html', user=identity)

        if not user_id:
            user_id = _resolve_user_id_from_identity(identity)
        if not user_id:
            flash('Unable to determine the active user account', 'danger')
            return render_template('profile.html', user=identity)


        avatar_filename = None
        if avatar_file and avatar_file.filename:
            if allowed_file(avatar_file.filename, ALLOWED_IMAGE_EXT):
                fname = secure_filename(avatar_file.filename)
                # prefix with user id and timestamp to avoid collisions
                import time
                pref = f"user_{user_id or 'anon'}_{int(time.time())}_"

                avatar_filename = pref + fname
                try:
                    avatar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename))
                except Exception:
                    app.logger.exception('Failed to save uploaded avatar')
                    avatar_filename = None
            else:
                flash('Unsupported avatar file type', 'danger')
                return render_template('profile.html', user=identity)

        # Try to update the users table if possible
        conn = get_db_connection()
        if not conn:
            flash('Server error: cannot connect to database', 'danger')

            return render_template('profile.html', user=identity)


        try:
            cur = conn.cursor()
            # discover columns in users table
            try:
                cur.execute('SHOW COLUMNS FROM users')
                cols = [r[0].lower() for r in cur.fetchall()]
            except Exception:
                cols = []


            # pick primary id column name for WHERE clause
            id_col = None
            for c in ['userid', 'id', 'user_id']:
                if c in cols:
                    id_col = c

                    break
            # pick username/email columns
            uname_col = 'username' if 'username' in cols else ('name' if 'name' in cols else None)
            email_col = 'email' if 'email' in cols else None
            profile_path_col = 'profile_path' if 'profile_path' in cols else None
            avatar_col = None
            for cand in ['avatar', 'avatar_path', 'image', 'profile_pic', 'picture']:
                if cand in cols and cand != profile_path_col:
                    avatar_col = cand
                    break


            # Build update dynamically using only available columns
            updates = []
            params = []
            if uname_col:
                updates.append(f"{uname_col} = %s")
                params.append(new_username)
            if email_col:
                updates.append(f"{email_col} = %s")
                params.append(new_email)
            if avatar_filename:
                if profile_path_col:
                    updates.append(f"{profile_path_col} = %s")
                    params.append(avatar_filename)
                if avatar_col:
                    updates.append(f"{avatar_col} = %s")
                    params.append(avatar_filename)


            if updates and id_col and user_id:
                sql = f"UPDATE users SET {', '.join(updates)} WHERE {id_col} = %s"
                params.append(user_id)
                try:
                    cur.execute(sql, tuple(params))
                    conn.commit()

                except Exception:
                    # best-effort: try dictionary cursor and column name variants
                    app.logger.exception('Failed to update users table')
            else:

                app.logger.warning('Users table missing expected columns; skipping DB update')

            # Update session copy if present
            try:
                if 'user' in session and isinstance(session['user'], dict):
                    update_payload = {'username': new_username, 'email': new_email}
                    if avatar_filename:
                        update_payload['profile_path'] = avatar_filename
                        update_payload['avatar'] = _build_upload_url(avatar_filename)
                    session['user'].update(update_payload)
            except Exception:
                pass

            # Also refresh identity for template render
            if isinstance(identity, dict):
                identity['username'] = new_username
                identity['email'] = new_email
                if avatar_filename:
                    identity['profile_path'] = avatar_filename
                    identity['avatar'] = _build_upload_url(avatar_filename)

            refreshed_payload = {}
            if id_col and user_id:
                refresh_cur = None
                try:
                    refresh_cur = conn.cursor(dictionary=True)
                    refresh_cur.execute(f'SELECT * FROM users WHERE {id_col} = %s LIMIT 1', (user_id,))
                    refreshed_row = refresh_cur.fetchone()
                    refreshed_payload = _build_user_payload_from_row(refreshed_row)
                except Exception:
                    app.logger.debug('Unable to refresh user profile payload after update', exc_info=True)
                finally:
                    try:
                        if refresh_cur:
                            refresh_cur.close()
                    except Exception:
                        pass

            if refreshed_payload and isinstance(identity, dict):
                identity.update(refreshed_payload)
            if refreshed_payload:
                try:
                    sess_user = session.get('user') or {}
                    sess_user.update(refreshed_payload)
                    session['user'] = sess_user
                except Exception:
                    pass


            flash('Profile updated successfully', 'success')
            try:
                cur.close()
            except Exception:
                pass
        except Exception:
            app.logger.exception('Profile update failed')
            flash('Failed to update profile', 'danger')
        finally:
            try:
                if conn and getattr(conn, 'is_connected', lambda: True)():
                    conn.close()
            except Exception:
                pass

        return render_template('profile.html', user=identity)

    # GET: render profile dashboard with orders and recent activity
    orders = []
    recent_products = []
    recent_shops = []  # placeholder; can be wired to real shop browsing data later

    conn = get_db_connection() if user_id else None
    if conn:
        try:
            cur = conn.cursor(dictionary=True)

            # Pending orders (user_pending_orders + items + products)
            try:
                cur.execute(
                    '''
                    SELECT upo.pendingID AS order_id,
                           upo.created_at,
                           upo.status,
                           p.name AS product_name,
                           p.image_path
                    FROM user_pending_orders upo
                    JOIN user_pending_order_items upoi ON upo.pendingID = upoi.pendingID

                    JOIN products p ON upoi.productID = p.productID
                    WHERE upo.userID = %s
                    ORDER BY upo.created_at DESC
                    ''',
                    (user_id,)
                )
                for row in cur.fetchall() or []:
                    img_url = None
                    try:
                        img_url = _build_upload_url(row.get('image_path'))
                    except Exception:
                        img_url = None
                    orders.append({
                        'id': row.get('order_id'),
                        'order_number': row.get('order_id'),
                        'product_name': row.get('product_name') or 'Order item',
                        'product_image': img_url,
                        'status': row.get('status') or 'pending_confirmation',
                        'date': row.get('created_at'),
                        'detail_url': url_for('user_orders')
                    })
            except Exception:
                app.logger.exception('Failed to load pending orders for profile dashboard')

            # Confirmed orders (seller_orders + items + products), excluding cancelled
            try:
                cur.execute(
                    '''
                    SELECT so.sellerOrderID AS order_id,
                           so.created_at,
                           so.status,
                           p.name AS product_name,
                           p.image_path
                    FROM seller_orders so
                    JOIN seller_order_items soi ON so.sellerOrderID = soi.sellerOrderID
                    JOIN products p ON soi.productID = p.productID
                    WHERE so.userID = %s
                      AND (so.status IS NULL OR so.status != 'cancelled')
                    ORDER BY so.created_at DESC
                    ''',
                    (user_id,)
                )
                for row in cur.fetchall() or []:
                    img_url = None
                    try:
                        img_url = _build_upload_url(row.get('image_path'))
                    except Exception:
                        img_url = None
                    orders.append({
                        'id': row.get('order_id'),
                        'order_number': row.get('order_id'),
                        'product_name': row.get('product_name') or 'Order item',
                        'product_image': img_url,
                        'status': row.get('status') or 'processing',
                        'date': row.get('created_at'),
                        'detail_url': url_for('user_orders')
                    })
            except Exception:
                app.logger.exception('Failed to load confirmed orders for profile dashboard')

            # Build a simple recent_products list from the most recent ordered products
            seen_names = set()
            for o in orders:
                name = o.get('product_name')
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                recent_products.append({
                    'name': name,
                    # Link back to orders page for now; can be updated to a product detail route
                    'url': url_for('user_orders')
                })
                if len(recent_products) >= 8:
                    break

            try:
                cur.close()
            except Exception:
                pass
        except Exception:
            app.logger.exception('Failed to build profile dashboard data')
        finally:
            try:
                if conn and getattr(conn, 'is_connected', lambda: True)():
                    conn.close()
            except Exception:
                pass

    return render_template('profile.html', user=identity, orders=orders, recent_products=recent_products, recent_shops=recent_shops)


@app.route('/admin/delete-seller/<int:seller_id>', methods=['POST'])
def admin_delete_seller(seller_id):
    # Basic admin guard: only allow when admin session is present
    admin_session = session.get('admin') or {}
    if not admin_session:
        return jsonify({'success': False, 'msg': 'Admin auth required'}), 403

    if not seller_id:
        return jsonify({'success': False, 'msg': 'Missing seller_id'}), 400

    ok, err = delete_seller_and_dependents(seller_id)
    if not ok:
        return jsonify({'success': False, 'msg': 'Deletion failed', 'error': err}), 500

    return jsonify({'success': True, 'msg': 'Seller and related data deleted'}), 200


@app.route('/admin/delete-rider/<int:rider_id>', methods=['POST'])
def admin_delete_rider(rider_id):
    admin_session = session.get('admin') or {}
    if not admin_session:
        return jsonify({'success': False, 'msg': 'Admin auth required'}), 403

    if not rider_id:
        return jsonify({'success': False, 'msg': 'Missing rider_id'}), 400

    ok, err = delete_rider_and_dependents(rider_id)
    if not ok:
        return jsonify({'success': False, 'msg': 'Deletion failed', 'error': err}), 500

    return jsonify({'success': True, 'msg': 'Rider and related data deleted'}), 200

@app.route('/')
def landing():
    """Show marketing landing page for guests; redirect logged-in users to shop."""
    if session.get('user_id') or session.get('seller_id') or session.get('rider_id'):
        return redirect(url_for('home'))
    return render_template('landing.html')


@app.route('/home')
def home():
    """Render shop homepage and include products created by sellers."""
    products = []
    categories = []
    per_page = FEATURED_PAGE_SIZE
    current_page = max(1, _safe_int(request.args.get('page'), 1))
    featured_payload = {
        'products': [],
        'page': current_page,
        'total_pages': 1,
        'total_products': 0,
    }

    conn = get_db_connection()
    if conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            featured_payload = _load_featured_products(cursor, conn, current_page, per_page)
            products = featured_payload.get('products') or []
            current_page = featured_payload.get('page', current_page)

            # Fetch categories from database
            try:
                cursor.execute("SELECT * FROM categories ORDER BY name ASC")
                categories = cursor.fetchall() or []
            except Exception:
                # Fallback to hardcoded categories if categories table doesn't exist
                categories = [
                    {'id': 1, 'name': 'Baby Clothes & Accessories', 'slug': 'baby-clothes'},
                    {'id': 2, 'name': 'Comfort Toys', 'slug': 'comfort-toys'},
                    {'id': 3, 'name': 'Educational Toys', 'slug': 'educational-toys'},
                    {'id': 4, 'name': 'Nursery Furniture', 'slug': 'nursery-furniture'},
                    {'id': 5, 'name': 'Safety and Health', 'slug': 'safety-and-health'},
                    {'id': 6, 'name': 'Stroller Gear', 'slug': 'stroller-gear'},
                ]
                app.logger.warning("Categories table not found, using hardcoded categories")

            try:
                products = _filter_out_frozen_products(conn, products)
            except Exception:
                pass
                
        except Exception:
            app.logger.exception("Failed to load products for home")
            products = []
        finally:
            try:
                if cursor: cursor.close()
            except Exception:
                pass
            try:
                if conn.is_connected():
                    conn.close()
            except Exception:
                pass

    # Pass products and categories to template so seller-added items appear on index page
    return render_template(
        'index.html',
        products=products,
        categories=categories,
        featured_page=featured_payload.get('page', current_page),
        featured_total_pages=featured_payload.get('total_pages', 1),
        featured_total_products=featured_payload.get('total_products', len(products)),
        featured_page_size=per_page,
    )


@app.route('/api/featured-products')
def api_featured_products():
        page = max(1, _safe_int(request.args.get('page'), 1))
        per_page = FEATURED_PAGE_SIZE
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "status": "error",
                "message": "Database unavailable",
                "data": None,
            }), 500

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            payload = _load_featured_products(cursor, conn, page, per_page)
            rows = payload.get('products') or []
            default_image_url = url_for('static', filename='images/default.png')

            products = []
            for row in rows:
                product_id = (
                    row.get('productID')
                    or row.get('product_id')
                    or row.get('id')
                    or row.get('productId')
                )
                if not product_id:
                    continue

                name = row.get('name') or row.get('title') or f"Product {product_id}"
                image_list = _extract_product_image_list(row)
                image_name = image_list[0] if image_list else None
                try:
                    image_url = url_for('uploaded_file', filename=image_name) if image_name else default_image_url
                except Exception:
                    image_url = default_image_url

                price = row.get('price')
                if isinstance(price, Decimal):
                    try:
                        price_value = float(price)
                    except Exception:
                        price_value = str(price)
                else:
                    price_value = price

                products.append({
                    'id': product_id,
                    'name': name,
                    'price': price_value,
                    'image_url': image_url,
                    'images': [url_for('uploaded_file', filename=img) for img in image_list if img],
                    'stock': row.get('stock'),
                    'detail_url': url_for('product_detail', product_id=product_id),
                    'description': row.get('description') or row.get('desc') or row.get('details') or '',
                })

            return jsonify({
                "status": "success",
                "message": "Featured products fetched",
                "data": {
                    "items": products,
                    "page": payload.get('page', page),
                    "total_pages": payload.get('total_pages', 1),
                    "total_products": payload.get('total_products', len(products)),
                    "page_size": per_page,
                },
            }), 200
        except Exception:
            app.logger.exception('Failed to load featured products API')
            return jsonify({
                "status": "error",
                "message": "Server error fetching featured products",
                "data": None,
            }), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass
            try:
                if conn and getattr(conn, 'is_connected', lambda: True)():
                    conn.close()
            except Exception:
                pass


@app.route('/about')
def about_page():
    user = session.get('user')
    story_paragraphs = [
        "HappyHands began as a collaborative project between parents, riders, and neighborhood sellers who wanted a safer way to share baby essentials online.",
        "Today we blend carefully curated products, proactive chat support, and a reliable rider network so families can shop with heart and confidence."
    ]
    mission_text = (
        "Empower every parent and caregiver with joyful, trustworthy shopping while lifting up the local sellers and riders who serve them."
    )
    vision_text = (
        "Become the Philippines' most caring marketplace for early childhood needs—where every order feels personal, safe, and full of wonder."
    )
    pillars = [
        {
            'title': 'Trust & Safety',
            'description': 'We vet sellers, coach riders, and surface transparent product information so you always know what is arriving at your door.'
        },
        {
            'title': 'Joyful Service',
            'description': 'Between live chat, proactive notifications, and friendly support, every interaction is designed to feel warm and human.'
        },
        {
            'title': 'Community Growth',
            'description': 'Tools for sellers and opportunities for riders mean every fulfilled order creates wins across the HappyHands ecosystem.'
        }
    ]
    highlights = [
        {
            'icon': 'fas fa-puzzle-piece',
            'title': 'Curated Categories',
            'description': 'Shop clothes, toys, nursery furniture, safety gear, and stroller essentials tailored to every growth stage.'
        },
        {
            'icon': 'fas fa-comments',
            'title': 'Always-On Support',
            'description': 'Need help with an order? Launch built-in support or seller chat from any page and get answers fast.'
        },
        {
            'icon': 'fas fa-shipping-fast',
            'title': 'Dedicated Rider Network',
            'description': 'Our vetted riders treat every package like it was packed for their own family, with careful handling and timely updates.'
        },
        {
            'icon': 'fas fa-hand-holding-heart',
            'title': 'Seller Success Tools',
            'description': 'Dashboards, analytics, and guided onboarding help local entrepreneurs grow sustainable baby-focused businesses.'
        }
    ]
    stats = [
        {'value': '1,200+', 'label': 'Happy families served'},
        {'value': '900+', 'label': 'Local seller partners'},
        {'value': '45 min', 'label': 'Average rider dispatch time'}
    ]
    return render_template(
        'user/about.html',
        user=user,
        story_paragraphs=story_paragraphs,
        mission_text=mission_text,
        vision_text=vision_text,
        pillars=pillars,
        highlights=highlights,
        stats=stats
    )
    
    
@app.route('/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        return jsonify({'products': products})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    # Admin shortcut login using configured credentials
    if (username == ADMIN_EMAIL or username == ADMIN_USERNAME) and password == ADMIN_PASSWORD:
        access_token = create_access_token(
            identity=str(0),
            additional_claims={'user': {'userID': 0, 'username': ADMIN_USERNAME, 'email': ADMIN_EMAIL}}
        )
        session['user'] = {'userID': 0, 'username': ADMIN_USERNAME, 'email': ADMIN_EMAIL}
        session['user_id'] = 0
        session['user_token'] = access_token
        try:
            session['user_type'] = 'admin'
        except Exception:
            pass
        session['admin'] = {'adminID': 0, 'username': ADMIN_USERNAME, 'email': ADMIN_EMAIL}
        _set_active_role('admin')
        resp = make_response(redirect(url_for('admin_dashboard')))
        user_session_token = secrets.token_urlsafe(32)
        admin_session_token = secrets.token_urlsafe(32)
        session['user_session'] = user_session_token
        session['admin_session'] = admin_session_token
        resp.set_cookie('access_token', access_token, httponly=True, secure=False, samesite='Lax', max_age=3600)
        _set_role_cookie(resp, 'user', user_session_token, max_age=3600)
        _set_role_cookie(resp, 'admin', admin_session_token, max_age=3600)
        return resp

    if not username or not password:
        flash('Please fill in all fields', 'danger')
        return render_template('login.html')

    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return render_template('login.html')

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s LIMIT 1", (username, username))
        user = cursor.fetchone()

        if user:
            hashed = user.get('password') or user.get('passwd') or user.get('sellerpassword') or ''
            if hashed and check_password_hash(hashed, password):
                user_id = user.get('userID') or user.get('id') or user.get('user_id')
                user_name = user.get('username') or user.get('name')
                user_email = user.get('email')
                user_payload = _build_user_payload_from_row(user) or {}

                is_admin = False
                try:
                    if user_id == 0:
                        is_admin = True
                    elif user_email and user_email == ADMIN_EMAIL:
                        is_admin = True
                    elif user_name and user_name == ADMIN_USERNAME:
                        is_admin = True
                except Exception:
                    is_admin = False

                access_token = create_access_token(
                    identity=str(user_id),
                    additional_claims={'user': {'userID': user_id, 'username': user_name, 'email': user_email}}
                )
                session_user = dict(user_payload)
                session_user.setdefault('userID', user_id)
                session_user.setdefault('username', user_name)
                session_user.setdefault('email', user_email)
                session['user'] = session_user
                session['user_id'] = user_id
                session['user_token'] = access_token
                _set_active_role('user')
                try:
                    session['user_type'] = 'admin' if is_admin else 'user'
                except Exception:
                    pass
                if is_admin:
                    session['admin'] = {'adminID': user_id, 'username': user_name, 'email': user_email}
                    _set_active_role('admin')

                target_endpoint = 'admin_dashboard' if is_admin else 'home'
                resp = make_response(redirect(url_for(target_endpoint)))
                set_access_cookies(resp, access_token)
                user_session_token = secrets.token_urlsafe(32)
                session['user_session'] = user_session_token
                _set_role_cookie(resp, 'user', user_session_token)
                if is_admin:
                    admin_session_token = secrets.token_urlsafe(32)
                    session['admin_session'] = admin_session_token
                    _set_role_cookie(resp, 'admin', admin_session_token)
                return resp

        flash('Invalid username or password', 'danger')
        return render_template('login.html')

    except mysql.connector.Error:
        app.logger.exception("Login DB error")
        flash('Login error occurred', 'danger')
        return render_template('login.html')
    finally:
        try:
            if conn and getattr(conn, 'is_connected', lambda: True)():
                cursor.close()
                conn.close()
        except Exception:
            pass


def send_otp_email(target_email, otp_code):
    """Send OTP using Flask-Mail.

    Returns (True, None) on success. On failure returns (False, error_code)
    where error_code is a short string useful for debugging (not sensitive).
    """
    try:
        subject = 'Your password reset code'
        body = (
            f"Your one-time password (OTP) for resetting your BabyBloom password is: {otp_code}\n\n"
            "This code will expire in 10 minutes. If you did not request this, please ignore this email.\n\n— BabyBloom"
        )
        def _deliver():
            msg = Message(subject, recipients=[target_email])
            msg.body = body
            mail.send(msg)

        if has_app_context():
            _deliver()
        else:
            with app.app_context():
                _deliver()
        app.logger.info(f"Sent password reset OTP to {target_email}")
        return True, None
    except Exception as e:
        app.logger.exception(f"Failed to send OTP email to {target_email}: {e}")
        return False, 'email_error'


@app.route('/__debug/send_test_email', methods=['GET', 'POST'])
def __debug_send_test_email():
    """Debug-only endpoint to attempt sending a test email from the app context.

    - Only available when app.debug is True.
    - Accepts ?to=recipient@example.com as query string (or form field 'to').
    - Returns JSON with success:true/false and a short error code on failure.
    """
    if not app.debug:
        return jsonify({'success': False, 'msg': 'Not available in production'}), 403

    recipient = (request.args.get('to') or request.form.get('to') or app.config.get('MAIL_DEFAULT_SENDER'))
    if not recipient:
        return jsonify({'success': False, 'msg': 'No recipient provided'}), 400

    subject = 'BabyBloom debug test email'
    body = 'This is a test email sent from the application debug endpoint.'

    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        return jsonify({'success': True, 'to': recipient}), 200
    except Exception as e:
        app.logger.exception('Debug test email send failed')
        return jsonify({'success': False, 'error': 'email_error', 'details': str(e)}), 500


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        try:
            token = secrets.token_hex(16)
            session['csrf_token'] = token
        except Exception:
            session['csrf_token'] = str(uuid.uuid4())
        return render_template('auth/forgot_password.html')

    # POST: handle send_otp or verify_otp based on action
    action = (request.form.get('action') or '').lower()
    csrf = request.form.get('csrf_token') or ''
    if not csrf or csrf != session.get('csrf_token'):
        flash('Invalid request (CSRF)', 'danger')
        return render_template('auth/forgot_password.html')
    email = (request.form.get('email') or '').strip()
    otp = (request.form.get('otp') or '').strip()

    if not email:
        flash('Please provide your email address', 'danger')
        return render_template('auth/forgot_password.html', email=email)

    if not email:
        flash('Please provide your email address', 'danger')
        return render_template('auth/forgot_password.html', email=email)

    # Check if email exists in any of the tables (users, sellers, riders)
    user_type = None
    conn = get_db_connection()
    if not conn:
        flash('Server error (DB connection)', 'danger')
        return render_template('auth/forgot_password.html', email=email)
    try:
        cur = conn.cursor(dictionary=True)
        # Check users
        cur.execute('SELECT userID FROM users WHERE email = %s LIMIT 1', (email,))
        if cur.fetchone():
            user_type = 'user'
        else:
            # Check sellers
            cur.execute('SELECT sellerID FROM sellers WHERE selleremail = %s LIMIT 1', (email,))
            if cur.fetchone():
                user_type = 'seller'
            else:
                # Check riders
                cur.execute('SELECT riderID FROM riders WHERE rideremail = %s LIMIT 1', (email,))
                if cur.fetchone():
                    user_type = 'rider'
    except Exception:
        user_type = None
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

    if not user_type:
        flash('If the email exists in our system you will receive a code. Please check your inbox.', 'info')
        # Do not reveal whether email exists
        return render_template('auth/forgot_password.html', email=email)

    # Send OTP
    if action == 'send_otp':
        rl = session.get('pw_reset_rl') or {}
        now = datetime.utcnow()
        wnd_start_iso = rl.get('window_start')
        try:
            wnd_start = datetime.fromisoformat(wnd_start_iso) if wnd_start_iso else None
        except Exception:
            wnd_start = None
        if not wnd_start or (now - wnd_start) > timedelta(minutes=15):
            rl = {'window_start': now.isoformat(), 'count': 0, 'last_send': None}
        last_iso = rl.get('last_send')
        try:
            last_dt = datetime.fromisoformat(last_iso) if last_iso else None
        except Exception:
            last_dt = None
        if last_dt and (now - last_dt) < timedelta(seconds=60):
            flash('Please wait before requesting another code.', 'info')
            session['pw_reset_rl'] = rl
            return render_template('auth/forgot_password.html', email=email)
        if rl.get('count', 0) >= 3:
            flash('Too many requests. Try again later.', 'danger')
            session['pw_reset_rl'] = rl
            return render_template('auth/forgot_password.html', email=email)
        code = f"{random.randint(1000, 9999)}"
        expires = now + timedelta(minutes=10)
        session['pw_reset'] = {'email': email, 'otp': code, 'expires': expires.isoformat(), 'user_type': user_type}
        rl['count'] = rl.get('count', 0) + 1
        rl['last_send'] = now.isoformat()
        session['pw_reset_rl'] = rl
        start_async_otp_email(email, code)
        # Success: show green flash to indicate the OTP send was accepted.
        flash('Request accepted. Your code is being sent. Please wait...', 'success')
        return render_template('auth/forgot_password.html', email=email, check_otp_status=True)

    # Verify OTP
    if action == 'verify_otp':
        attempts = session.get('pw_reset_attempts') or {}
        now = datetime.utcnow()
        data = session.get('pw_reset') or {}
        saved_email = data.get('email')
        saved_otp = data.get('otp')
        saved_user_type = data.get('user_type') or 'user'
        expires_iso = data.get('expires')
        try:
            expires_dt = datetime.fromisoformat(expires_iso) if expires_iso else None
        except Exception:
            expires_dt = None

        if not saved_email or not saved_otp or not expires_dt:
            flash('No OTP request found. Please request a new code.', 'danger')
            return render_template('auth/forgot_password.html', email=email)

        if datetime.utcnow() > expires_dt:
            session.pop('pw_reset', None)
            flash('OTP expired. Please request a new code.', 'danger')
            return render_template('auth/forgot_password.html', email=email)

        att = attempts.get(saved_email) or {'count': 0}
        if att['count'] >= 5:
            session.pop('pw_reset', None)
            flash('Too many invalid attempts. Please request a new code.', 'danger')
            return render_template('auth/forgot_password.html', email=email)
        if otp and otp == saved_otp and email == saved_email:
            # mark verified in session and redirect to reset page
            session['pw_reset_verified'] = email
            session['pw_reset_verified_type'] = saved_user_type
            session['pw_reset_verified_at'] = now.isoformat()
            # remove the OTP to avoid reuse
            session.pop('pw_reset', None)
            return redirect(url_for('reset_password'))
        else:
            att['count'] = att.get('count', 0) + 1
            attempts[saved_email] = att
            session['pw_reset_attempts'] = attempts
            flash('Invalid code. Please try again.', 'danger')
            return render_template('auth/forgot_password.html', email=email)

    # Unknown action
    flash('Invalid request', 'danger')
    return render_template('auth/forgot_password.html', email=email)


@app.route('/api/otp_status')
def api_otp_status():
    email = (request.args.get('email') or '').strip()
    if not email:
        return jsonify({'success': False, 'msg': 'missing email'}), 400
    st = PW_RESET_SEND_STATUS.get(email)
    if not st:
        return jsonify({'success': True, 'status': 'none', 'ms': None}), 200
    return jsonify({'success': True, 'status': st.get('status'), 'ms': st.get('ms'), 'error_code': st.get('error_code')}), 200


@app.route('/api/mobile/forgot-password', methods=['POST'])
def api_mobile_forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400

    # DB lookup: find user_type
    user_type = None
    conn = get_db_connection()
    if not conn:
        return jsonify({'status': 'error', 'message': 'Server error'}), 500
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT userID FROM users WHERE email = %s LIMIT 1', (email,))
        if cur.fetchone():
            user_type = 'user'
        else:
            cur.execute('SELECT sellerID FROM sellers WHERE selleremail = %s LIMIT 1', (email,))
            if cur.fetchone():
                user_type = 'seller'
            else:
                cur.execute('SELECT riderID FROM riders WHERE rideremail = %s LIMIT 1', (email,))
                if cur.fetchone():
                    user_type = 'rider'
    except Exception:
        pass
    finally:
        try: cur.close() if cur else None
        except Exception: pass
        try: conn.close()
        except Exception: pass

    # Always return success to avoid email enumeration
    if not user_type:
        return jsonify({'status': 'success', 'message': 'If that email is registered, a code will be sent.'}), 200

    # Rate limiting (in-memory, no sessions)
    now = datetime.utcnow()
    entry = API_PW_RESET_OTPS.get(email) or {}
    rate = entry.get('rate') or {}
    wnd_iso = rate.get('window_start_iso')
    try:
        wnd_start = datetime.fromisoformat(wnd_iso) if wnd_iso else None
    except Exception:
        wnd_start = None
    if not wnd_start or (now - wnd_start) > timedelta(minutes=15):
        rate = {'count': 0, 'window_start_iso': now.isoformat(), 'last_send_iso': None}
    last_iso = rate.get('last_send_iso')
    try:
        last_dt = datetime.fromisoformat(last_iso) if last_iso else None
    except Exception:
        last_dt = None
    if last_dt and (now - last_dt) < timedelta(seconds=60):
        return jsonify({'status': 'error', 'message': 'Please wait before requesting another code.'}), 429
    if rate.get('count', 0) >= 3:
        return jsonify({'status': 'error', 'message': 'Too many requests. Try again later.'}), 429

    # Generate OTP
    code = f"{secrets.randbelow(9000) + 1000}"
    expires = now + timedelta(minutes=10)
    rate['count'] = rate.get('count', 0) + 1
    rate['last_send_iso'] = now.isoformat()
    API_PW_RESET_OTPS[email] = {
        'otp': code,
        'expires_iso': expires.isoformat(),
        'user_type': user_type,
        'attempts': 0,
        'rate': rate,
    }
    start_async_otp_email(email, code)
    return jsonify({'status': 'success', 'message': 'If that email is registered, a code will be sent.'}), 200


@app.route('/api/mobile/verify-otp', methods=['POST'])
def api_mobile_verify_otp():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    otp = (data.get('otp') or '').strip()
    if not email or not otp:
        return jsonify({'status': 'error', 'message': 'Email and OTP are required'}), 400

    entry = API_PW_RESET_OTPS.get(email)
    if not entry:
        return jsonify({'status': 'error', 'message': 'No OTP request found. Please request a new code.'}), 400

    now = datetime.utcnow()
    try:
        expires_dt = datetime.fromisoformat(entry['expires_iso'])
    except Exception:
        expires_dt = None
    if not expires_dt or now > expires_dt:
        API_PW_RESET_OTPS.pop(email, None)
        return jsonify({'status': 'error', 'message': 'OTP expired. Please request a new code.'}), 400

    if entry.get('attempts', 0) >= 5:
        API_PW_RESET_OTPS.pop(email, None)
        return jsonify({'status': 'error', 'message': 'Too many invalid attempts. Please request a new code.'}), 400

    if otp != entry['otp']:
        entry['attempts'] = entry.get('attempts', 0) + 1
        API_PW_RESET_OTPS[email] = entry
        return jsonify({'status': 'error', 'message': 'Invalid code. Please try again.'}), 400

    # OTP correct — generate reset token
    reset_token = str(uuid.uuid4())
    token_expires = now + timedelta(minutes=30)
    user_type = entry.get('user_type', 'user')
    API_PW_RESET_TOKENS[reset_token] = {
        'email': email,
        'user_type': user_type,
        'expires_iso': token_expires.isoformat(),
    }
    API_PW_RESET_OTPS.pop(email, None)
    return jsonify({'status': 'success', 'reset_token': reset_token, 'user_type': user_type}), 200


@app.route('/api/mobile/reset-password', methods=['POST'])
def api_mobile_reset_password():
    data = request.get_json(silent=True) or {}
    reset_token = (data.get('reset_token') or '').strip()
    new_password = data.get('new_password') or ''
    if not reset_token or not new_password:
        return jsonify({'status': 'error', 'message': 'reset_token and new_password are required'}), 400
    if len(new_password) < 6:
        return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters'}), 400

    token_data = API_PW_RESET_TOKENS.get(reset_token)
    if not token_data:
        return jsonify({'status': 'error', 'message': 'Invalid or expired reset token'}), 400

    now = datetime.utcnow()
    try:
        expires_dt = datetime.fromisoformat(token_data['expires_iso'])
    except Exception:
        expires_dt = None
    if not expires_dt or now > expires_dt:
        API_PW_RESET_TOKENS.pop(reset_token, None)
        return jsonify({'status': 'error', 'message': 'Reset token expired. Please start over.'}), 400

    email = token_data['email']
    user_type = token_data.get('user_type', 'user')
    hashed = generate_password_hash(new_password)

    conn = get_db_connection()
    if not conn:
        return jsonify({'status': 'error', 'message': 'Server error'}), 500
    try:
        cur = conn.cursor()
        if user_type == 'seller':
            cur.execute('UPDATE sellers SET sellerpass = %s WHERE selleremail = %s', (hashed, email))
        elif user_type == 'rider':
            cur.execute('UPDATE riders SET riderpass = %s WHERE rideremail = %s', (hashed, email))
        else:
            cur.execute('UPDATE users SET password = %s WHERE email = %s', (hashed, email))
        conn.commit()
    except Exception as e:
        app.logger.exception(f'Failed to update password for {email}: {e}')
        return jsonify({'status': 'error', 'message': 'Failed to update password'}), 500
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

    API_PW_RESET_TOKENS.pop(reset_token, None)
    return jsonify({'status': 'success', 'message': 'Password updated successfully'}), 200


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    verified_email = session.get('pw_reset_verified')
    verified_type = session.get('pw_reset_verified_type') or 'user'
    if not verified_email:
        flash('Unauthorized or expired reset flow. Please request a new code.', 'danger')
        return redirect(url_for('forgot_password'))

    try:
        v_at = session.get('pw_reset_verified_at')
        v_dt = datetime.fromisoformat(v_at) if v_at else None
        if not v_dt or (datetime.utcnow() - v_dt) > timedelta(minutes=30):
            session.pop('pw_reset_verified', None)
            session.pop('pw_reset_verified_at', None)
            session.pop('pw_reset_verified_type', None)
            flash('Reset session expired. Please request a new code.', 'danger')
            return redirect(url_for('forgot_password'))
    except Exception:
        pass

    if request.method == 'GET':
        try:
            token = secrets.token_hex(16)
            session['csrf_token'] = token
        except Exception:
            session['csrf_token'] = str(uuid.uuid4())
        return render_template('auth/reset_password.html')

    # POST: update password
    csrf = request.form.get('csrf_token') or ''
    if not csrf or csrf != session.get('csrf_token'):
        flash('Invalid request (CSRF)', 'danger')
        return render_template('auth/reset_password.html')
    password = request.form.get('password') or ''
    confirm = request.form.get('confirm_password') or ''
    if not password or not confirm:
        flash('Please fill in all fields', 'danger')
        return render_template('auth/reset_password.html')
    if password != confirm:
        flash('Passwords do not match', 'danger')
        return render_template('auth/reset_password.html')

    # No complexity restrictions: allow any password as requested.

    # update DB
    conn = get_db_connection()
    if not conn:
        flash('Server error (DB connection)', 'danger')
        return render_template('auth/reset_password.html')
    try:
        cur = conn.cursor()
        hashed = generate_password_hash(password)
        
        if verified_type == 'user':
            # tolerant column names
            # try to update users where email matches
            cur.execute("SHOW COLUMNS FROM users")
            cols = [r[0].lower() for r in cur.fetchall()]
            pw_col = 'password' if 'password' in cols else ('passwd' if 'passwd' in cols else None)
            if not pw_col:
                flash('Server misconfiguration: password column missing', 'danger')
                return render_template('auth/reset_password.html')
            sql = f"UPDATE users SET {pw_col} = %s WHERE email = %s"
            cur.execute(sql, (hashed, verified_email))
        elif verified_type == 'seller':
            cur.execute("SHOW COLUMNS FROM sellers")
            cols = [r[0].lower() for r in cur.fetchall()]
            pw_col = 'password' if 'password' in cols else ('sellerpassword' if 'sellerpassword' in cols else None)
            if not pw_col:
                flash('Server misconfiguration: password column missing', 'danger')
                return render_template('auth/reset_password.html')
            sql = f"UPDATE sellers SET {pw_col} = %s WHERE selleremail = %s"
            cur.execute(sql, (hashed, verified_email))
        elif verified_type == 'rider':
            cur.execute("SHOW COLUMNS FROM riders")
            cols = [r[0].lower() for r in cur.fetchall()]
            pw_col = 'riderpass' if 'riderpass' in cols else ('password' if 'password' in cols else None)
            if not pw_col:
                flash('Server misconfiguration: password column missing', 'danger')
                return render_template('auth/reset_password.html')
            sql = f"UPDATE riders SET {pw_col} = %s WHERE rideremail = %s"
            cur.execute(sql, (hashed, verified_email))

        conn.commit()
        flash('Password updated. You can now log in with your new password.', 'success')
        # clean session
        session.pop('pw_reset_verified', None)
        session.pop('pw_reset_verified_type', None)
        
        if verified_type == 'seller':
            return redirect(url_for('seller_login'))
        elif verified_type == 'rider':
            return redirect(url_for('rider_login'))
        else:
            return redirect(url_for('login'))
    except Exception as e:
        app.logger.exception('Failed to update password')
        flash('Failed to update password. Please try again.', 'danger')
        return render_template('auth/reset_password.html')
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

    


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Example protected endpoint. Client must send Authorization: Bearer <token>
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200


def _build_logout_response(message, redirect_endpoint):
    ctype = (request.headers.get('Content-Type') or '').lower()
    accept = (request.headers.get('Accept') or '').lower()
    is_xhr = (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest'
    wants_json = 'application/json' in ctype or 'application/json' in accept

    if request.method == 'POST' and (is_xhr or wants_json):
        return make_response(jsonify({'success': True, 'msg': message}), 200)
    return make_response(redirect(url_for(redirect_endpoint)))


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Clear only user-related session data and JWT cookies, then redirect to login."""
    _clear_role_session('user')
    resp = _build_logout_response('Signed out', 'login')
    try:
        # Clear JWT cookies set by flask_jwt_extended (respects JWT_ACCESS_COOKIE_NAME)
        unset_jwt_cookies(resp)
    except Exception:
        app.logger.debug('unset_jwt_cookies failed during logout', exc_info=True)

    try:
        resp.delete_cookie(
            app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token'),
            path='/',
            samesite=app.config.get('JWT_COOKIE_SAMESITE', 'Lax'),
            secure=app.config.get('JWT_COOKIE_SECURE', False)
        )
    except Exception:
        try:
            resp.delete_cookie(app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token'), path='/')
        except Exception:
            pass

    _clear_role_cookie(resp, 'user')

    try:
        flash('You have been signed out.', 'success')
    except Exception:
        pass
    return resp


@app.route('/admin-logout', methods=['GET', 'POST'])
def admin_logout():
    _clear_role_session('admin')
    resp = _build_logout_response('Admin signed out', 'login')

    cleared_user_context = False
    try:
        sess_user = session.get('user') or {}
        uid = sess_user.get('userID') or sess_user.get('id')
        username = sess_user.get('username')
        email = sess_user.get('email')
        if uid in (0, '0') or username == ADMIN_USERNAME or email == ADMIN_EMAIL:
            _clear_role_session('user')
            cleared_user_context = True
    except Exception:
        pass

    _clear_role_cookie(resp, 'admin')
    if cleared_user_context:
        _clear_role_cookie(resp, 'user')
        try:
            unset_jwt_cookies(resp)
        except Exception:
            pass
        try:
            resp.delete_cookie(
                app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token'),
                path='/',
                samesite=app.config.get('JWT_COOKIE_SAMESITE', 'Lax'),
                secure=app.config.get('JWT_COOKIE_SECURE', False)
            )
        except Exception:
            try:
                resp.delete_cookie(app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token'), path='/')
            except Exception:
                pass

    try:
        flash('Admin session ended.', 'success')
    except Exception:
        pass
    return resp


@app.route('/seller-logout', methods=['GET', 'POST'])
def seller_logout():
    _clear_role_session('seller')

    # Build response first so we can clear the seller_session cookie
    if request.method == 'POST' or request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest':
        resp = make_response(jsonify({'success': True, 'msg': 'Seller signed out'}), 200)
    else:
        resp = make_response(redirect(url_for('seller_login')))

    _clear_role_cookie(resp, 'seller')

    return resp


@app.route('/rider-logout', methods=['GET', 'POST'])
def rider_logout():
    _clear_role_session('rider')

    if request.method == 'POST' or request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest':
        resp = make_response(jsonify({'success': True, 'msg': 'Rider signed out'}), 200)
    else:
        resp = make_response(redirect(url_for('rider_login')))

    _clear_role_cookie(resp, 'rider')

    return resp


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
        # expose both raw decoded and extracted identity for debugging
        return jsonify({'present': True, 'cookie_name': cookie_name, 'decoded': decoded, 'identity': extract_identity_from_decoded(decoded)}), 200
    except Exception as e:
        return jsonify({'present': True, 'cookie_name': cookie_name, 'error': str(e)}), 200


@app.route('/__debug/whoami', methods=['GET'])
def __debug_whoami():
    """Return session info and whether an access token cookie is present.

    - Only available when app.debug is True.
    - Helps diagnose why endpoints that rely on `session['seller']` or JWT cookies return 401.
    """
    if not app.debug:
        return jsonify({'success': False, 'msg': 'Not available in production'}), 403

    cookie_name = app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token')
    token = request.cookies.get(cookie_name)
    decoded = None
    try:
        if token:
            decoded = decode_token(token)
    except Exception as e:
        decoded = {'error': str(e)}

    return jsonify({
        'success': True,
        'session_user': session.get('user'),
        'session_seller': session.get('seller'),
        'access_token_present': bool(token),
        'decoded_token': decoded
    }), 200


@app.route('/register', methods=['POST'])
def register():
    payload = request.get_json(silent=True) or request.form or {}
    email = (payload.get('reg-email') or payload.get('email') or '').strip()
    username = (payload.get('reg-username') or payload.get('username') or '').strip()
    password = payload.get('reg-password') or payload.get('password') or ''
    confirmpassword = payload.get('reg-confirm-password') or payload.get('confirm_password') or payload.get('confirmPassword') or ''
    region = (payload.get('reg-region') or payload.get('region') or '').strip()
    province = (payload.get('reg-province') or payload.get('province') or '').strip()
    city = (payload.get('reg-city') or payload.get('city') or '').strip()
    barangay = (payload.get('reg-barangay') or payload.get('barangay') or '').strip()
    home_address = (payload.get('reg-home-address') or payload.get('home_address') or '').strip()
    contact_number = (payload.get('reg-contact-number') or payload.get('contact_number') or '').strip()

    required = [email, username, password, confirmpassword, region, province, city, barangay, home_address, contact_number]
    if not all(required):
        flash('Please fill in all fields, including your permanent address.', 'danger')
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
        
        # Create new user and persist the permanent address in the shared address table.
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                      (username, email, hashed_password))
        user_id = cursor.lastrowid

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_saved_addresses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                userID INT NOT NULL UNIQUE,
                region VARCHAR(255),
                province VARCHAR(255),
                city VARCHAR(255),
                barangay VARCHAR(255),
                home_address TEXT,
                contact_number VARCHAR(64),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''
        )
        cursor.execute(
            '''
            INSERT INTO user_saved_addresses (userID, region, province, city, barangay, home_address, contact_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                region = VALUES(region),
                province = VALUES(province),
                city = VALUES(city),
                barangay = VALUES(barangay),
                home_address = VALUES(home_address),
                contact_number = VALUES(contact_number)
            '''
            , (user_id, region, province, city, barangay, home_address, contact_number)
        )
        conn.commit()
        
        flash('Account created successfully! Please login.', 'success')
        send_welcome_email(email, username)
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

@app.route('/cart/count')
def cart_count():
    """Get the current cart count for the logged-in user"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'count': 0})
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'count': 0})
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(quantity) as total_count 
            FROM cart 
            WHERE userID = %s AND status = 'active'
        """, (user_id,))
        
        result = cursor.fetchone()
        count = result[0] if result and result[0] else 0
        
        return jsonify({'count': int(count)})
        
    except Exception as e:
        app.logger.exception("Error getting cart count")
        return jsonify({'count': 0})
    finally:
        conn.close()


@app.route('/api/orders/cancel-confirmed/<int:seller_order_id>', methods=['POST'])
def api_user_cancel_confirmed_order(seller_order_id):
    """Allow a user to cancel a confirmed/to-track seller order.

    This marks the seller_orders row as cancelled (and, when possible,
    also updates the originating user_pending_orders row), and adds a
    status history entry. Further status changes are blocked by the
    seller status API once an order is cancelled.
    """
    user = session.get('user') or {}
    user_id = user.get('userID') or session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in'}), 401

    data = request.get_json(silent=True) or request.form or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
        return jsonify({'success': False, 'msg': 'Please provide a cancellation reason'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        # Verify the order belongs to this user and is cancellable
        cursor.execute(
            """
            SELECT sellerOrderID, userID, status, originalPendingID
            FROM seller_orders
            WHERE sellerOrderID = %s AND userID = %s
            LIMIT 1
            """,
            (seller_order_id, user_id),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'msg': 'Order not found'}), 404

        status = (row.get('status') or 'pending').lower()
        if status in {'delivered', 'cancelled'}:
            return jsonify({'success': False, 'msg': 'This order can no longer be cancelled.'}), 400

        # Grab ordered items so we can restock after cancellation
        order_items = []
        try:
            cursor.execute(
                "SELECT productID, quantity FROM seller_order_items WHERE sellerOrderID = %s",
                (seller_order_id,)
            )
            order_items = cursor.fetchall() or []
        except Exception:
            order_items = []

        # Update seller order status to cancelled (and capture reason in notes if possible)
        try:
            cursor.execute(
                "UPDATE seller_orders SET status = %s, updated_at = NOW(), notes = %s WHERE sellerOrderID = %s",
                ('cancelled', reason, seller_order_id),
            )
        except Exception:
            cursor.execute(
                "UPDATE seller_orders SET status = %s, updated_at = NOW() WHERE sellerOrderID = %s",
                ('cancelled', seller_order_id),
            )

        # Record status history entry for user cancellation
        msg = 'Order cancelled by user'
        if reason:
            msg += f' - {reason}'
        try:
            cursor.execute(
                """
                INSERT INTO order_status_history (sellerOrderID, status, message)
                VALUES (%s, %s, %s)
                """,
                (seller_order_id, 'cancelled', msg),
            )
        except Exception:
            pass

        # Restore product stock for the cancelled items
        for item in order_items:
            try:
                product_id = int(item.get('productID'))
                qty = int(item.get('quantity') or 0)
            except Exception:
                product_id = None
                qty = 0
            if not product_id or qty <= 0:
                continue
            try:
                cursor.execute(
                    "UPDATE products SET stock = stock + %s WHERE productID = %s",
                    (qty, product_id)
                )
            except Exception:
                try:
                    app.logger.warning('Failed to restock product %s after seller order cancellation', product_id)
                except Exception:
                    pass

        # Best-effort: mark originating pending order as cancelled too
        original_pending_id = row.get('originalPendingID')
        if original_pending_id:
            try:
                cursor.execute(
                    """
                    UPDATE user_pending_orders
                    SET status = 'cancelled'
                    WHERE pendingID = %s AND userID = %s
                    """,
                    (original_pending_id, user_id),
                )
            except Exception:
                pass

        conn.commit()
        return jsonify({'success': True, 'msg': 'Order cancelled successfully.'}), 200

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('Error cancelling confirmed order')
        return jsonify({'success': False, 'msg': f'Error cancelling order: {str(e)}'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/cart')
def cart():
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    # Require user to be logged in to view cart
    if not user_id:
        flash('Please log in to view your cart.', 'warning')
        return redirect(url_for('login'))
    
    cart_items = []
    user_info = None
    
    # Use database-based cart for logged-in users
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get cart items from database
            cursor.execute("""
                SELECT 
                    c.cartID,
                    c.productID as product_id,
                    p.name,
                    p.image_path as image,
                    p.stock as stock,
                    c.quantity,
                    c.price,
                    c.total_price,
                    c.added_at
                FROM cart c
                JOIN products p ON c.productID = p.productID
                WHERE c.userID = %s AND c.status = 'active'
                ORDER BY c.added_at DESC
            """, (user_id,))
            
            db_cart_items = cursor.fetchall()
            
            # Convert to cart format
            for item in db_cart_items:
                cart_items.append({
                    'product_id': item['product_id'],
                    'name': item['name'],
                    'price': float(item['price']),
                    'stock': int(item.get('stock') or 0),
                    'quantity': item['quantity'],
                    'image': item['image'],
                    'user_id': user_id,
                    'cart_id': f"db_{item['cartID']}"
                })
            
            # Get user info
            cursor.execute("SELECT userID as id, username, email FROM users WHERE userID = %s", (user_id,))
            user_info = cursor.fetchone()
            if user_info:
                user_info['id'] = user_id
            
        except Exception as e:
            app.logger.error(f"Error fetching cart from database: {e}")
        finally:
            conn.close()
    
    app.logger.info(f"Cart items: {cart_items}")
    
    return render_template('cart.html', cart_items=cart_items, user_id=user_id, user_info=user_info)


@app.route('/seller_signup', methods=['GET', 'POST'])
def seller_signup():
    # Fetch categories for the dropdown
    categories = []
    conn_cat = get_db_connection()
    if conn_cat:
        try:
            categories = _fetch_all_categories(conn_cat)
        finally:
            try:
                conn_cat.close()
            except Exception:
                pass
    if not categories:
        categories = [c.copy() for c in DEFAULT_CATEGORY_CHOICES]

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
        exact_address = (request.form.get('exact_address') or '').strip()
        # Handle multiple categories
        raw_category_ids = request.form.getlist('seller_category_ids') or request.form.getlist('seller_category')
        seller_category_ids = []
        for raw_id in raw_category_ids:
            try:
                seller_category_ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        # Preserve original selection order while removing duplicates
        seen = set()
        seller_category_ids = [cid for cid in seller_category_ids if not (cid in seen or seen.add(cid))]
        category_lookup = {
            int(cat.get('id') or cat.get('categoryID') or cat.get('category_id')): cat
            for cat in categories
            if (cat.get('id') or cat.get('categoryID') or cat.get('category_id')) is not None
        }
        selected_category_rows = [category_lookup.get(cid) for cid in seller_category_ids if category_lookup.get(cid)]
        if not selected_category_rows:
            flash('Please choose at least one product category.', 'error')
            return render_template('seller_signup.html', categories=categories)
        if len(selected_category_rows) != len(seller_category_ids):
            flash('One or more selected categories are invalid. Please refresh the page and try again.', 'error')
            return render_template('seller_signup.html', categories=categories)
        seller_category = ', '.join(row.get('name') for row in selected_category_rows if row.get('name'))
        
        password = request.form.get('password') or request.form.get('sellerpassword') or ''
        confirmpassword = request.form.get('confirmpassword') or request.form.get('confirm_password') or ''

        # Basic validation (include password)
        required = [sellername, selleremail, contactnumber, storename, storedesc, region, province, city, barangay, exact_address, password, confirmpassword]
        if not all(required):
            flash('Please fill in all required fields (including password)', 'error')
            return render_template('seller_signup.html', categories=categories)

        if password != confirmpassword:
            flash('Passwords do not match', 'error')
            return render_template('seller_signup.html', categories=categories)

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
            return render_template('seller_signup.html', categories=categories)

        logo_path = None
        permit_path = None

        if logo_file and logo_file.filename:
            if not allowed_file(logo_file.filename, ALLOWED_IMAGE_EXT):
                flash('Store logo must be an image (png/jpg/jpeg)', 'error')
                return render_template('seller_signup.html', categories=categories)
            filename = secure_filename(logo_file.filename)
            unique = f"logo_{uuid.uuid4().hex}_{filename}"
            logo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
            logo_path = unique

        if permit_file and permit_file.filename:
            if not allowed_file(permit_file.filename, ALLOWED_DOC_EXT):
                flash('Business permit must be PDF or image', 'error')
                return render_template('seller_signup.html', categories=categories)
            filename = secure_filename(permit_file.filename)
            unique = f"permit_{uuid.uuid4().hex}_{filename}"
            permit_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
            permit_path = unique

        logo_path = logo_path or ''
        permit_path = permit_path or ''

        # Insert into DB (adapt to actual password column)
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return render_template('seller_signup.html', categories=categories)

        try:
            cursor = conn.cursor()
            # detect columns on sellers table
            cursor.execute("SHOW COLUMNS FROM sellers")
            columns = [r[0].lower() for r in cursor.fetchall()]

            # resolve password column name
            if 'password' in columns:
                pw_col = 'password'
            elif 'sellerpassword' in columns:
                pw_col = 'sellerpassword'
            elif 'passwd' in columns:
                pw_col = 'passwd'
            else:
                flash('Database missing password column on sellers table. Please run migration to add a password column.', 'error')
                return render_template('seller_signup.html', categories=categories)

            # build column list for insert; include 'status' if available and set to 'pending'
            cols = ['sellername', 'selleremail', 'contactnumber', 'storename', 'storedesc', pw_col, 'storelogo_path', 'businesspermit_path', 'region', 'province', 'city', 'barangay']
            values = [sellername, selleremail, contactnumber, storename, storedesc, hashed_password, logo_path, permit_path, region, province, city, barangay]

            if 'status' in columns:
                cols.append('status')
                values.append('pending')

            if 'seller_category' in columns:
                cols.append('seller_category')
                values.append(seller_category)

            if 'exact_address' in columns:
                cols.append('exact_address')
                values.append(exact_address)

            placeholders = ','.join(['%s'] * len(cols))
            sql = "INSERT INTO sellers ({}) VALUES ({})".format(','.join(cols), placeholders)
            cursor.execute(sql, tuple(values))
            new_seller_id = getattr(cursor, 'lastrowid', None)
            if not new_seller_id:
                try:
                    cursor.execute(
                        "SELECT sellerID FROM sellers WHERE selleremail = %s ORDER BY sellerID DESC LIMIT 1",
                        (selleremail,),
                    )
                    row = cursor.fetchone()
                    if row:
                        new_seller_id = row[0]
                except Exception:
                    new_seller_id = None

            try:
                _assign_categories_to_seller(conn, new_seller_id, seller_category_ids)
            except Exception:
                app.logger.exception('Failed saving seller category mapping')
                raise
            conn.commit()
        except Exception as e:
            conn.rollback()
            app.logger.exception("Seller signup DB error")
            flash('Error saving seller data', 'error')
            return render_template('seller_signup.html', categories=categories)
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
        send_seller_welcome_email(selleremail, sellername)
        return redirect(url_for('seller_login'))

    return render_template('seller_signup.html', categories=categories)

@app.route('/rider_homepage')
def rider_homepage():
    return render_template('rider_homepage.html')

@app.route('/api/rider/status')
@rider_required
def api_rider_status():
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'status': 'unknown'}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({'status': 'db_error'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT status FROM riders WHERE riderID = %s LIMIT 1", (rider_id,))
        row = cur.fetchone()
        status = row.get('status') if row else (session.get('rider') or {}).get('status', 'pending')
        # --- Ensure session is refreshed with latest status ---
        _normalize_session_rider(status=status)
        return jsonify({'status': status}), 200
    except Exception:
        app.logger.exception('rider status check failed')
        return jsonify({'status': 'server_error'}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass

# Global cache for PSGC data
PSGC_CACHE = {}

def resolve_psgc(code, type_):
    """
    Resolve a PSGC code to a name using the external API, with caching.
    type_ should be one of: 'regions', 'provinces', 'cities-municipalities', 'barangays'
    """
    if not code or not code.isdigit():
        return code
    
    cache_key = f"{type_}:{code}"
    if cache_key in PSGC_CACHE:
        return PSGC_CACHE[cache_key]
    
    try:
        url = f"https://psgc.gitlab.io/api/{type_}/{code}"
        res = requests.get(url, timeout=5)
        if res.ok:
            data = res.json()
            name = data.get('name')
            if name:
                PSGC_CACHE[cache_key] = name
                return name
    except Exception:
        pass
    
    return code

# Rider APIs: list assigned orders, accept/decline, update status
@app.route('/api/rider/orders', methods=['GET'])
@rider_required
def api_rider_orders():
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT so.*, s.storename, s.sellername, s.region, s.province, s.city, s.barangay, s.exact_address
            FROM seller_orders so
            LEFT JOIN sellers s ON so.sellerID = s.sellerID
            WHERE so.riderID = %s AND LOWER(IFNULL(so.status, '')) NOT IN ('delivered', 'cancelled')
            ORDER BY so.created_at DESC
            """,
            (rider_id,)
        )
        rows = cur.fetchall() or []
        order_ids = [r.get('sellerOrderID') for r in rows if r.get('sellerOrderID') is not None]
        responses = {}
        if order_ids:
            placeholders = ','.join(['%s'] * len(order_ids))
            params = [rider_id] + order_ids
            cur.execute(f"""
                SELECT sellerOrderID, action, created_at
                FROM rider_response_audit
                WHERE riderID = %s AND sellerOrderID IN ({placeholders})
                ORDER BY created_at DESC
            """, tuple(params))
            audit_rows = cur.fetchall() or []
            for rec in audit_rows:
                oid = rec.get('sellerOrderID')
                if oid not in responses:
                    responses[oid] = rec.get('action')
        # map locations
        items = []
        for r in rows:
            # Resolve address codes to names if they look like codes
            barangay = resolve_psgc(r.get('barangay'), 'barangays')
            city = resolve_psgc(r.get('city'), 'cities-municipalities')
            province = resolve_psgc(r.get('province'), 'provinces')
            region = resolve_psgc(r.get('region'), 'regions')
            exact_address = r.get('exact_address')
            
            pickup_parts = [v for v in [exact_address, barangay, city, province, region] if v]
            pickup = ", ".join(pickup_parts)
            oid = r.get('sellerOrderID')
            last_action = responses.get(oid)
            items.append({
                'sellerOrderID': oid,
                'order_number': r.get('order_number'),
                'shop_name': r.get('storename') or r.get('sellername') or 'Shop',
                'pickup_location': pickup,
                'delivery_location': r.get('shipping_address'),
                'status': r.get('status'),
                'total_amount': float(r.get('total_amount') or 0.0),
                'sellerID': r.get('sellerID'),
                'seller_name': r.get('sellername'),
                'riderAccepted': last_action == 'accept'
            })
        return jsonify({'success': True, 'orders': items}), 200
    except Exception as e:
        app.logger.exception('rider orders fetch failed')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass

@app.route('/api/rider/orders/<int:seller_order_id>/respond', methods=['POST'])
@rider_required
def api_rider_respond(seller_order_id):
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    data = request.get_json(silent=True) or {}
    action = (data.get('action') or '').lower()
    reason = (data.get('reason') or '').strip()
    details = (data.get('details') or '').strip()
    if action not in ('accept', 'decline'):
        return jsonify({'success': False, 'msg': 'Invalid action'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        _ensure_seller_order_status_enum()
        cur = conn.cursor(dictionary=True)
        # Verify order assigned to this rider and get sellerID
        cur.execute("SELECT sellerID FROM seller_orders WHERE sellerOrderID = %s AND riderID = %s", (seller_order_id, rider_id))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'msg': 'Order not assigned to you'}), 404
        if action == 'accept':
            # Get order info
            cur.execute("SELECT order_number, userID FROM seller_orders WHERE sellerOrderID = %s LIMIT 1", (seller_order_id,))
            order_info = cur.fetchone() or {}
            order_number = order_info.get('order_number') or str(seller_order_id)
            user_id = order_info.get('userID')

            # Update status to assigned_to_rider (idempotent) and create history
            try:
                cur.execute("UPDATE seller_orders SET status = 'assigned_to_rider', updated_at = NOW() WHERE sellerOrderID = %s", (seller_order_id,))
            except Exception:
                pass
            try:
                cur.execute("INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s, %s, %s)", (seller_order_id, 'assigned_to_rider', f'Rider accepted assignment'))
            except Exception:
                pass
            # Note: We don't create "Rider accepted assignment" status - only "Seller assigns order to [ridername]" is shown
            # Notify seller
            cur.execute("INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)", 
                       (row.get('sellerID'), 'Rider accepted order', f'Order #{order_number} accepted by rider'))
            emit_notification_event('seller', row.get('sellerID'), 'Rider accepted order', f'Order #{order_number} accepted by rider')

            # Notify user that rider accepted (optional - can be used for chat availability)
            if user_id:
                try:
                    cur.execute("INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('user', %s, 'Rider Assigned', %s)", 
                               (user_id, f'Order #{order_number} has been accepted by a rider'))
                    emit_notification_event('user', user_id, 'Rider Assigned', f'Order #{order_number} has been accepted by a rider')
                except Exception:
                    pass
            # Seed a chat message linking this order, seller, user and rider so the rider
            # immediately sees a conversation thread. Use existing chat helper which
            # will only persist optional columns if they exist in the schema.
            try:
                try:
                    # compose a short seed message
                    seed_msg = f"Rider accepted assignment for order #{order_number}"
                    # chat.save_chat_message signature: (conn, room, sender_type, senderID, message, productID=None, sellerID=None, userID=None, riderID=None)
                    chat.save_chat_message(conn, f'order_{seller_order_id}', 'rider', rider_id, seed_msg, productID=seller_order_id, sellerID=row.get('sellerID'), userID=user_id, riderID=rider_id)
                except Exception:
                    # best-effort: don't fail the whole flow if chat seeding fails
                    app.logger.debug('Failed to seed chat message for rider accept', exc_info=True)
            except Exception:
                pass
        else:
            # Declined: create history entry with reason
            msg = 'Rider declined assignment'
            if reason:
                msg += f" - {reason}"
            if details:
                msg += f": {details}"
            cur.execute("INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s, %s, %s)", (seller_order_id, 'assigned_to_rider', msg))
            # Optionally set order back to packed
            try:
                cur.execute("UPDATE seller_orders SET status = 'packed', riderID = NULL, updated_at = NOW() WHERE sellerOrderID = %s", (seller_order_id,))
            except Exception:
                pass
            # Notify seller of rejection
            cur.execute("INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)", (row.get('sellerID'), 'Rider declined order', f"Order #{seller_order_id} declined by rider"))
            emit_notification_event('seller', row.get('sellerID'), 'Rider declined order', f"Order #{seller_order_id} declined by rider")
        _log_rider_response(conn, rider_id, seller_order_id, action)
        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('rider respond failed')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/rider/orders/<int:seller_order_id>/details', methods=['GET'])
@rider_required
def api_rider_order_details(seller_order_id):
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Fetch order details
        cur.execute("""
            SELECT so.*, s.storename, s.sellername, s.region, s.province, s.city, s.barangay, s.exact_address,
                   u.username as user_name
            FROM seller_orders so
            LEFT JOIN sellers s ON so.sellerID = s.sellerID
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.sellerOrderID = %s
        """, (seller_order_id,))
        order = cur.fetchone()
        if not order:
            return jsonify({'success': False, 'msg': 'Order not found'}), 404
        
        # Check if rider is assigned or if it's available (assigned_to_rider but not yet accepted by anyone else?)
        # For now, we allow viewing if the rider is assigned OR if the order is in a state where this rider can see it.
        
        if order.get('riderID') and int(order.get('riderID')) != int(rider_id):
             return jsonify({'success': False, 'msg': 'Order not assigned to you'}), 403

        # Fetch items
        cur.execute("""
            SELECT soi.*, p.name, p.image_path
            FROM seller_order_items soi
            LEFT JOIN products p ON soi.productID = p.productID
            WHERE soi.sellerOrderID = %s
        """, (seller_order_id,))
        items = cur.fetchall() or []
        
        # Resolve address
        barangay = resolve_psgc(order.get('barangay'), 'barangays')
        city = resolve_psgc(order.get('city'), 'cities-municipalities')
        province = resolve_psgc(order.get('province'), 'provinces')
        region = resolve_psgc(order.get('region'), 'regions')
        
        order_data = {
            'order_number': order.get('order_number'),
            'user_name': order.get('user_name'),
            'shop_name': order.get('storename') or order.get('sellername'),
            'contact_number': order.get('contact_number'),
            'total_amount': float(order.get('total_amount') or 0),
            'region': region,
            'province': province,
            'city': city,
            'barangay': barangay,
            'exact_address': order.get('exact_address'),
            'address': order.get('shipping_address'),
            'payment_method': order.get('payment_method'),
            'items': [{
                'name': i.get('name'),
                'quantity': i.get('quantity'),
                'price': float(i.get('price') or 0),
                'image': i.get('image_path')
            } for i in items]
        }
        
        return jsonify({'success': True, 'order': order_data}), 200
    except Exception as e:
        app.logger.exception('rider order details failed')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass


@app.route('/api/rider/orders/<int:seller_order_id>/status', methods=['POST'])
@rider_required
def api_rider_update_status(seller_order_id):
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip()
    if status not in ('on_the_way', 'delivered'):
        return jsonify({'success': False, 'msg': 'Invalid status'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        _ensure_seller_order_status_enum()
        cur = conn.cursor(dictionary=True)
        # Verify order assigned to rider and get sellerID & userID
        cur.execute("SELECT sellerID, userID FROM seller_orders WHERE sellerOrderID = %s AND riderID = %s", (seller_order_id, rider_id))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'msg': 'Order not assigned to you'}), 404
        cur.execute("UPDATE seller_orders SET status = %s, updated_at = NOW() WHERE sellerOrderID = %s", (status, seller_order_id))
        
        rider_name = ((session.get('rider') or {}).get('ridername') or '').strip()
        base_msg = 'Order is on the way' if status == 'on_the_way' else 'Order delivered'
        msg = f"{base_msg}{' by ' + rider_name if rider_name else ''}"
        cur.execute("INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s, %s, %s)", (seller_order_id, status, msg))
        
        # Notify user (for track order and confirmation prompt)
        try:
            if row.get('userID'):
                title = f"Order {status.replace('_',' ')}"
                body = f"Order #{seller_order_id}: {msg}."
                if status == 'delivered':
                    body += " Please confirm receipt or report any issues from the Orders page."
                cur.execute(
                    "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('user', %s, %s, %s)",
                    (row.get('userID'), title, body)
                )
                emit_notification_event('user', row.get('userID'), title, body)
        except Exception:
            pass

        if status == 'delivered':
            # Reset buyer confirmation flags so UI can render the "Order Received" button
            try:
                cur.execute(
                    "UPDATE seller_orders SET buyer_received = 0, buyer_received_at = NULL WHERE sellerOrderID = %s",
                    (seller_order_id,)
                )
            except Exception:
                app.logger.debug('Failed to reset buyer confirmation flags for order %s', seller_order_id, exc_info=True)

            # Inform seller that delivery completed and funds are pending confirmation
            try:
                seller_id = row.get('sellerID')
                if seller_id:
                    body = f"Order #{seller_order_id} marked delivered by rider. Awaiting buyer confirmation before revenue is released."
                    cur.execute(
                        "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)",
                        (seller_id, 'Delivery completed', body)
                    )
                    emit_notification_event('seller', seller_id, 'Delivery completed', body)
            except Exception:
                app.logger.debug('Failed to notify seller for delivered order %s', seller_order_id, exc_info=True)

            # Add informational history entry to assist tracking timeline
            try:
                cur.execute(
                    "INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s, %s, %s)",
                    (seller_order_id, 'delivered', 'Waiting for buyer confirmation to release funds')
                )
            except Exception:
                pass
        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('rider status update failed')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/admin/reports/<int:report_id>')
@admin_required
def admin_get_report(report_id):
    """Return JSON details for a single report for the admin dashboard modal."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM reports WHERE id = %s LIMIT 1", (report_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'msg': 'not_found'}), 404

        product_name = None
        product_image_path = None
        product_image_url = None
        seller_name = None
        reported_product_id = row.get('reported_product_id')
        reported_seller_id = row.get('reported_shop_id')

        if reported_product_id:
            try:
                cur.execute("SELECT name, image_path FROM products WHERE productID = %s LIMIT 1", (reported_product_id,))
                prod_row = cur.fetchone()
                if prod_row:
                    product_name = prod_row.get('name') or prod_row.get('product_name')
                    raw_product_image = prod_row.get('image_path')
                    if raw_product_image:
                        try:
                            product_image_path = raw_product_image.replace('\\', '/').lstrip('./')
                        except Exception:
                            product_image_path = raw_product_image
                    if product_image_path:
                        try:
                            product_image_url = url_for('admin_uploaded_file', filename=product_image_path)
                        except Exception:
                            try:
                                product_image_url = url_for('uploaded_file', filename=product_image_path)
                            except Exception:
                                product_image_url = None
            except Exception:
                app.logger.debug('Failed to load product name for report %s', report_id, exc_info=True)

        if reported_seller_id:
            try:
                cur.execute("SELECT storename FROM sellers WHERE sellerID = %s LIMIT 1", (reported_seller_id,))
                seller_row = cur.fetchone()
                if seller_row:
                    seller_name = seller_row.get('storename') or seller_row.get('sellername')
            except Exception:
                app.logger.debug('Failed to load seller name for report %s', report_id, exc_info=True)

        image_url = None
        raw_image_path = row.get('image_path') or None
        image_path = None
        if raw_image_path:
            try:
                image_path = raw_image_path.replace('\\', '/').lstrip('./')
            except Exception:
                image_path = raw_image_path
        if image_path:
            try:
                image_url = url_for('admin_uploaded_file', filename=image_path)
            except Exception:
                try:
                    image_url = url_for('uploaded_file', filename=image_path)
                except Exception:
                    image_url = None

        created = row.get('created_at')
        if hasattr(created, 'isoformat'):
            created_val = created.isoformat(sep=' ', timespec='seconds')
        else:
            created_val = str(created) if created is not None else None

        report = {
            'id': row.get('id'),
            'reporter_id': row.get('reporter_id'),
            'reporter_name': row.get('reporter_name'),
            'reported_product_id': row.get('reported_product_id'),
            'reported_shop_id': row.get('reported_shop_id'),
            'role': row.get('role'),
            'description': row.get('description'),
            'message': row.get('message'),
            'status': row.get('status'),
            'offense_level': row.get('offense_level') or 0,
            'created_at': created_val,
            # complaint_type is not a DB column; keep key for template/JS compatibility
            'complaint_type': row.get('complaint_type'),
            'image_url': image_url,
            'image_path': image_path,
            'product_name': product_name,
            'product_image_url': product_image_url,
            'product_image_path': product_image_path,
            'seller_name': seller_name,
        }
        try:
            _ensure_restriction_tables(conn)
        except Exception:
            pass
        seller_id = row.get('reported_shop_id')
        responses = []
        restriction_type = None
        restriction_end = None
        if seller_id:
            try:
                cur.execute(
                    """
                    SELECT id, offense_level, response_type, subject, message, attachment_path, created_at, report_id
                    FROM seller_restriction_responses
                    WHERE sellerID = %s
                    ORDER BY created_at DESC
                    """,
                    (seller_id,)
                )
                resp_rows = cur.fetchall() or []
                for resp in resp_rows:
                    attachment_url = None
                    attachment_path = resp.get('attachment_path')
                    if attachment_path:
                        try:
                            attachment_url = url_for('admin_uploaded_file', filename=attachment_path)
                        except Exception:
                            try:
                                attachment_url = url_for('uploaded_file', filename=attachment_path)
                            except Exception:
                                attachment_url = None
                    responses.append({
                        'id': resp.get('id'),
                        'offense_level': resp.get('offense_level'),
                        'response_type': resp.get('response_type'),
                        'subject': resp.get('subject'),
                        'message': resp.get('message'),
                        'attachment_path': attachment_path,
                        'attachment_url': attachment_url,
                        'created_at': _dt_to_iso(resp.get('created_at')),
                        'report_id': resp.get('report_id'),
                    })
            except Exception:
                app.logger.debug('Failed to load seller restriction responses', exc_info=True)
            try:
                cur.execute(
                    "SELECT restriction_type, restriction_end FROM seller_restrictions WHERE sellerID = %s",
                    (seller_id,)
                )
                restriction_rows = cur.fetchall() or []
                if restriction_rows:
                    restriction_rows.sort(key=lambda r: 3 if (r.get('restriction_type') == 'account_frozen') else 2, reverse=True)
                    primary = restriction_rows[0]
                    restriction_type = primary.get('restriction_type')
                    restriction_end = _dt_to_iso(primary.get('restriction_end'))
            except Exception:
                app.logger.debug('Failed to load seller restriction info for report', exc_info=True)

        report['responses'] = responses
        report['restriction_type'] = restriction_type
        report['restriction_end'] = restriction_end
        return jsonify({'success': True, 'report': report}), 200
    except Exception:
        app.logger.exception('Failed to fetch report details')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/admin/reports/<int:report_id>/update-offense', methods=['POST'])
@admin_required
def admin_update_report_offense(report_id):
    data = request.get_json() or {}
    try:
        offense_level = int(data.get('offense_level', 0))
    except (TypeError, ValueError):
        offense_level = 0
    seller_id = data.get('seller_id')
    reason_text = (data.get('reason') or '').strip()
    auto_reset_days = data.get('auto_reset_days')
    if isinstance(auto_reset_days, str):
        auto_reset_days = auto_reset_days.strip()
        if not auto_reset_days:
            auto_reset_days = None

    if report_id < 0:
        return jsonify({'success': False, 'msg': 'invalid_report'}), 400

    try:
        seller_id = int(seller_id)
    except (TypeError, ValueError):
        seller_id = None

    if offense_level < 0 or offense_level > 3:
        return jsonify({'success': False, 'msg': 'Invalid offense level'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    try:
        _ensure_restriction_tables(conn)
        cur = conn.cursor(dictionary=True, buffered=True)

        status_value = 'resolved' if offense_level in (0, 1, 2, 3) else 'open'
        cur.execute(
            'UPDATE reports SET offense_level = %s, status = %s WHERE id = %s',
            (offense_level, status_value, report_id)
        )

        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({'success': False, 'msg': 'report_not_found'}), 404

        cur.execute(
            'SELECT reported_shop_id, reported_product_id FROM reports WHERE id = %s',
            (report_id,)
        )
        report = cur.fetchone()
        if not report:
            return jsonify({'success': False, 'msg': 'report_not_found'}), 404

        seller_id_from_report = report.get('reported_shop_id')
        product_id_from_report = report.get('reported_product_id')

        target_seller_id = seller_id if seller_id is not None else seller_id_from_report
        try:
            target_seller_id = int(target_seller_id) if target_seller_id is not None else None
        except (TypeError, ValueError):
            target_seller_id = None

        if target_seller_id is None and product_id_from_report:
            cur.execute('SELECT sellerID FROM products WHERE productID = %s LIMIT 1', (product_id_from_report,))
            product_owner = cur.fetchone()
            if product_owner:
                target_seller_id = product_owner.get('sellerID') or product_owner.get('seller_id')
                try:
                    target_seller_id = int(target_seller_id)
                except (TypeError, ValueError):
                    target_seller_id = None

        current_report_seller = None
        if seller_id_from_report is not None:
            try:
                current_report_seller = int(seller_id_from_report)
            except (TypeError, ValueError):
                current_report_seller = None

        if target_seller_id and (current_report_seller is None or current_report_seller != target_seller_id):
            try:
                cur.execute('UPDATE reports SET reported_shop_id = %s WHERE id = %s', (target_seller_id, report_id))
                conn.commit()
            except Exception:
                app.logger.debug('Failed to backfill reported_shop_id for report %s', report_id, exc_info=True)

        seller_status = None
        restriction_state = None

        if target_seller_id:
            try:
                restriction_state = _apply_seller_offense(
                    conn,
                    target_seller_id,
                    offense_level,
                    reason=reason_text,
                    report_id=report_id,
                    admin_id=_current_admin_id(),
                    auto_reset_days=auto_reset_days
                ) or {}
            except Exception:
                app.logger.exception('Failed to apply offense level %s for seller %s', offense_level, target_seller_id)
                return jsonify({'success': False, 'msg': 'offense_update_failed'}), 500

            try:
                cur.execute('SELECT status FROM sellers WHERE sellerID = %s LIMIT 1', (target_seller_id,))
                seller_row = cur.fetchone()
                seller_status = seller_row.get('status') if seller_row else None
            except Exception:
                seller_status = None
        else:
            conn.commit()

        payload = {
            'report_id': report_id,
            'offense_level': (restriction_state.get('offense_level') if restriction_state else offense_level),
            'seller_id': target_seller_id,
            'status': status_value,
            'seller_status': seller_status,
            'restriction_type': restriction_state.get('restriction_type') if restriction_state else None,
            'restriction_end': restriction_state.get('restriction_end') if restriction_state else None,
            'restriction_level': restriction_state.get('level') if restriction_state else None,
            'offense_reason': restriction_state.get('offense_reason') if restriction_state else (reason_text or None),
            'appeal_deadline': restriction_state.get('appeal_deadline') if restriction_state else None,
            'is_frozen': restriction_state.get('is_frozen') if restriction_state else None,
        }

        return jsonify({'success': True, 'msg': 'Offense level updated successfully', 'data': payload}), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('Failed to update offense level')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/admin/reports/<int:report_id>/unfreeze', methods=['POST'])
@admin_required
def admin_unfreeze_report(report_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    try:
        _ensure_restriction_tables(conn)
        _ensure_seller_offense_tables(conn)
        cur = conn.cursor(dictionary=True, buffered=True)
        cur.execute('SELECT * FROM reports WHERE id = %s LIMIT 1', (report_id,))
        report = cur.fetchone()
        if not report:
            return jsonify({'success': False, 'msg': 'not_found'}), 404

        seller_id = report.get('reported_shop_id')
        if not seller_id:
            return jsonify({'success': False, 'msg': 'missing_seller'}), 400

        cur.execute('SELECT selleremail FROM sellers WHERE sellerID = %s', (seller_id,))
        s_row = cur.fetchone()
        seller_email = s_row['selleremail'] if s_row else None

        cur.execute("UPDATE reports SET offense_level = 0, status = 'resolved' WHERE id = %s", (report_id,))

        restriction_state = _apply_seller_offense(
            conn,
            seller_id,
            0,
            reason='Restrictions cleared by administrator',
            report_id=report_id,
            admin_id=_current_admin_id()
        ) or {}
        conn.commit()

        try:
            cur.execute(
                "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)",
                (seller_id, 'Account unfrozen', 'Your account restrictions have been lifted by the administrator.')
            )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        emit_notification_event('seller', seller_id, 'Account unfrozen', 'Your account restrictions have been lifted by the administrator.')

        if seller_email:
            try:
                enqueue_email(
                    subject='Account Unfrozen - Happy Hands',
                    recipients=[seller_email],
                    body='Your account is now in an unfrozen state and you can now go back to business.',
                    html='<p>Your account is now in an unfrozen state and you can now go back to business.</p>'
                )
            except Exception:
                app.logger.exception('Failed to send unfreeze email')

        return jsonify({'success': True, 'state': restriction_state}), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('Failed to unfreeze seller account')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# PSGC API in-memory cache — avoids hammering the external API on every
# dropdown change.  Key = URL, value = (timestamp, simplified_list).
# TTL is 4 hours; data changes very rarely.
# ---------------------------------------------------------------------------
import time as _time
_PSGC_CACHE: dict = {}
_PSGC_CACHE_TTL = 4 * 3600  # seconds


def _psgc_fetch(url: str, timeout: int = 8) -> list:
    """Fetch a PSGC API URL and return the JSON list, using an in-memory cache."""
    now = _time.time()
    cached = _PSGC_CACHE.get(url)
    if cached and (now - cached[0]) < _PSGC_CACHE_TTL:
        return cached[1]
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    data = res.json()
    _PSGC_CACHE[url] = (now, data)
    return data


@app.route('/get_regions')
def get_regions():
    """Return list of PH regions from PSGC (code + name). Used by checkout page."""
    try:
        data = _psgc_fetch("https://psgc.gitlab.io/api/regions/")
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        app.logger.exception("Failed to fetch regions")
        return jsonify({'error': 'Failed to fetch regions', 'details': str(e)}), 500


@app.route('/get_provinces/<region>')
def get_provinces(region):
    """Return list of provinces for a region code from PSGC (code + name).
    For province-less regions (e.g. NCR), falls back to region-level cities
    and marks each item with city_direct=True so the frontend can skip the
    province→city cascade and go straight to barangay selection."""
    try:
        data = _psgc_fetch(f"https://psgc.gitlab.io/api/regions/{region}/provinces/")
        if data:
            simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        else:
            city_data = _psgc_fetch(f"https://psgc.gitlab.io/api/regions/{region}/cities-municipalities/")
            simplified = [{'code': item.get('code'), 'name': item.get('name'), 'city_direct': True}
                          for item in city_data]
        return jsonify(simplified)
    except Exception as e:
        app.logger.exception("Failed to fetch provinces")
        return jsonify({'error': 'Failed to fetch provinces', 'details': str(e)}), 500


@app.route('/get_cities/<province>')
def get_cities(province):
    """Return list of cities/municipalities for a province code from PSGC (code + name)."""
    try:
        data = _psgc_fetch(f"https://psgc.gitlab.io/api/provinces/{province}/cities-municipalities/")
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        app.logger.exception("Failed to fetch cities")
        return jsonify({'error': 'Failed to fetch cities', 'details': str(e)}), 500


@app.route('/get_barangays/<city>')
def get_barangays(city):
    try:
        data = _psgc_fetch(f"https://psgc.gitlab.io/api/cities-municipalities/{city}/barangays/")
        simplified = [{'code': item.get('code'), 'name': item.get('name')} for item in data]
        return jsonify(simplified)
    except Exception as e:
        app.logger.exception("Failed to fetch barangays")
        return jsonify({'error': 'Failed to fetch barangays', 'details': str(e)}), 500


@app.route('/seller_login', methods=['GET', 'POST'])
def seller_login():
    if request.method == 'GET':
        return render_template('seller_login.html')
    if request.method == 'POST':
        selleremail = (request.form.get('selleremail') or '').strip()
        password = request.form.get('sellerpassword') or ''
        remember = bool(request.form.get('remember'))

        if not selleremail or not password:
            flash('Please provide both email and password', 'error')
            return render_template('seller_login.html')

        conn = get_db_connection()
        if not conn:
            app.logger.error("DB connection failed during seller login")
            flash('Server error, please try later', 'error')
            return render_template('seller_login.html')

        cursor = None
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
                if cursor: cursor.close()
            except Exception:
                pass
            try:
                if conn.is_connected():
                    conn.close()
            except Exception:
                pass

        if not row:
            flash('Invalid credentials', 'error')
            return render_template('seller_login.html')

        hashed_pw = row.get('password') or row.get('sellerpassword') or ''
        status = (row.get('status') or 'pending')

        if not hashed_pw or not check_password_hash(hashed_pw, password):
            flash('Invalid credentials', 'error')
            return render_template('seller_login.html')

        # Block login for sellers who are not yet approved
        if status not in ('approved', 'active'):
            flash('Your seller account is not yet approved. Please wait for admin approval.', 'error')
            return render_template('seller_login.html')

        # prepare session and JWT token for seller role only
        try:
            for key in ('seller', 'seller_id', 'seller_token', 'seller_session'):
                session.pop(key, None)
        except Exception:
            pass
        seller_id = row.get('id') or row.get('sellerID')
        seller_name = row.get('sellername') or row.get('storename')
        identity_claim = {
            'sellerID': seller_id,
            'sellername': seller_name,
            'selleremail': selleremail,
            'role': 'seller'
        }
        # Keep both 'id' and 'sellerID' keys for compatibility with different code paths
        session['seller'] = {
            'id': seller_id,
            'sellerID': seller_id,
            'sellername': seller_name,
            'storename': row.get('storename'),
            'name': seller_name,
            'email': selleremail,
            'status': status
        }
        _set_active_role('seller')
        session.modified = True

        # create token with string subject and full seller info in additional_claims
        try:
            default_secs = int(app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
        except Exception:
            default_secs = 3600

        expires = timedelta(days=30) if remember else timedelta(seconds=default_secs)
        access_token = create_access_token(
            identity=str(seller_id),
            additional_claims={'seller': identity_claim, 'role': 'seller'},
            expires_delta=expires
        )

        session['seller_id'] = seller_id
        session['seller_token'] = access_token
        seller_session_token = secrets.token_urlsafe(32)
        session['seller_session'] = seller_session_token

        resp = make_response(redirect(url_for('seller_dashboard')))
        cookie_max_age = int(expires.total_seconds()) if expires else None
        # seller_session must be readable by front-end JS so Socket.IO can pass it in auth payloads
        _set_role_cookie(resp, 'seller', seller_session_token, max_age=cookie_max_age)
        
        # Set JWT cookie for API access
        set_access_cookies(resp, access_token)

        if remember:
            session.permanent = True

        flash('Signed in successfully', 'success')
        return resp

    return render_template('seller_login.html')


def sellers_has_status_column(conn):
    """Return True if sellers table contains a 'status' column."""
    try:
        cur = conn.cursor()
        cur.execute("SHOW COLUMNS FROM sellers")
        cols = [r[0].lower() for r in cur.fetchall()]
        try: cur.close()
        except Exception: pass
        return 'status' in cols
    except Exception:
        try: cur.close()
        except Exception: pass
        return False

@app.route('/api/seller/status')
def api_seller_status():
    seller = session.get('seller')
    if not seller:
        return jsonify({'error': 'not_authenticated'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'db_error'}), 500

    try:
        if sellers_has_status_column(conn):
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT status FROM sellers WHERE selleremail = %s LIMIT 1", (seller.get('email'),))
            row = cur.fetchone()
            status = row.get('status') if row else seller.get('status', 'pending')
            try: cur.close()
            except Exception: pass
        else:
            # fallback when DB has no status column
            status = seller.get('status') == 'pending'
            # optionally update session copy
            session.setdefault('seller', {})['status'] = status

        return jsonify({'status': status}), 200
    except Exception:
        app.logger.exception("Failed to get seller status")
        return jsonify({'error': 'server_error'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/seller_pending')
def seller_pending():
    # simple page to show pending message if needed
    seller = session.get('seller')
    if not seller:
        return redirect(url_for('seller_login'))
    return render_template('seller_pending.html', seller=seller)

@app.route('/baby-clothes')
def baby_clothes():
    return redirect(url_for('category_page', slug='baby-clothes'))

@app.route('/comfort-toys')
def comfort_toys():
    return redirect(url_for('category_page', slug='comfort-toys'))

@app.route('/toys')
def toys():
    # Nav shortcut for general toys link; reuse comfort-toys category view
    return redirect(url_for('category_page', slug='comfort-toys'))

@app.route('/educational-toys')
def educational_toys():
    return redirect(url_for('category_page', slug='educational-toys'))

@app.route('/nursery-furniture')
def nursery_furniture():
    return redirect(url_for('category_page', slug='nursery-furniture'))

@app.route('/furniture')
def furniture():
    # Nav shortcut for furniture link pointing at nursery furniture category
    return redirect(url_for('category_page', slug='nursery-furniture'))

@app.route('/safety-and-health')
def safety_and_health():
    return redirect(url_for('category_page', slug='safety-and-health'))

@app.route('/stroller-gear')
def stroller_gear():
    return redirect(url_for('category_page', slug='stroller-gear'))

@app.route('/clothes')
def clothes():
    # Nav shortcut for clothes link pointing at baby clothes category
    return redirect(url_for('category_page', slug='baby-clothes'))

@app.route('/search')
def search_page():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('home'))

    conn = get_db_connection()
    categories = []
    products = []
    
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            
            # 1. Fetch categories to check for direct match and for sidebar
            try:
                cur.execute("SELECT * FROM categories ORDER BY name ASC")
                categories = cur.fetchall() or []
            except Exception:
                # Fallback categories
                categories = [
                    {'id': 1, 'name': 'Baby Clothes & Accessories', 'slug': 'baby-clothes'},
                    {'id': 2, 'name': 'Comfort Toys', 'slug': 'comfort-toys'},
                    {'id': 3, 'name': 'Educational Toys', 'slug': 'educational-toys'},
                    {'id': 4, 'name': 'Nursery Furniture', 'slug': 'nursery-furniture'},
                    {'id': 5, 'name': 'Safety and Health', 'slug': 'safety-and-health'},
                    {'id': 6, 'name': 'Stroller Gear', 'slug': 'stroller-gear'},
                ]

            # 2. Check for category match (slug or name)
            for c in categories:
                if c.get('slug') == query.lower() or c.get('name', '').lower() == query.lower():
                    return redirect(url_for('category_page', slug=c.get('slug')))
            
            # 3. Search products
            # We'll search in name, description, and category fields
            search_term = f"%{query}%"
            
            # Check columns to build query safely
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM products")
            prod_cols = [r[0].lower() for r in meta.fetchall()]
            try: meta.close()
            except: pass
            
            where_clauses = []
            params = []
            
            if 'name' in prod_cols:
                where_clauses.append("name LIKE %s")
                params.append(search_term)
            elif 'title' in prod_cols:
                where_clauses.append("title LIKE %s")
                params.append(search_term)
                
            if 'description' in prod_cols:
                where_clauses.append("description LIKE %s")
                params.append(search_term)
                
            if 'category' in prod_cols:
                where_clauses.append("category LIKE %s")
                params.append(search_term)
                
            if where_clauses:
                sql = "SELECT * FROM products WHERE (" + " OR ".join(where_clauses) + ") ORDER BY productID DESC"
                cur.execute(sql, tuple(params))
                products = cur.fetchall() or []
            else:
                products = []

            # Normalize images (copied from category_page)
            try:
                normalized = []
                upload_folder = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)
                for r in products:
                    if not isinstance(r, dict):
                        normalized.append(r)
                        continue
                    img = r.get('image_path') or r.get('image') or r.get('main_image') or r.get('imageurl') or r.get('store_logo')
                    img_url = None
                    if img:
                        # Check if file exists
                        full_path = os.path.join(upload_folder, img)
                        if os.path.exists(full_path):
                            try:
                                img_url = url_for('uploaded_file', filename=img)
                            except Exception:
                                img_url = None
                        else:
                            img_url = None
                    
                    if not img_url:
                        img_url = url_for('static', filename='images/default.png')

                    rr = dict(r)
                    rr['image_url'] = img_url
                    if 'name' not in rr and rr.get('title'):
                        rr['name'] = rr.get('title')
                    normalized.append(rr)
                products = normalized
            except Exception:
                pass
                
            try:
                products = _filter_out_frozen_products(conn, products)
            except Exception:
                pass

        except Exception as e:
            app.logger.error(f"Search failed: {e}")
        finally:
            try: cur.close(); conn.close()
            except: pass
            
    # Render category_base with search results
    current_category = {'name': f'Search Results: "{query}"', 'slug': 'search'}
    pagination = {
        'page': 1,
        'per_page': len(products or []) or CATEGORY_PAGE_SIZE,
        'total_pages': 1,
        'total_products': len(products or []),
        'has_prev': False,
        'has_next': False,
    }
    return render_template('categories/category_base.html', products=products, categories=categories, current_category=current_category, pagination=pagination)


def _load_category_products(conn, slug, current_category, categories, page=1, per_page=None):
    """Fetch paginated products for a category, returning normalized records and pagination metadata."""
    per_page = per_page or CATEGORY_PAGE_SIZE
    per_page = max(1, min(_safe_int(per_page, CATEGORY_PAGE_SIZE), CATEGORY_PAGE_MAX))
    page = max(1, _safe_int(page, 1))

    result = {
        'products': [],
        'total_products': 0,
        'total_pages': 1,
        'page': page,
        'per_page': per_page,
    }

    if not conn:
        return result

    cur = conn.cursor(dictionary=True)
    products = []
    total_products = 0
    total_pages = 1

    try:
        prod_cols = []
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM products")
            prod_cols = [r[0].lower() for r in meta.fetchall()]
        except Exception:
            prod_cols = []
        finally:
            try:
                meta.close()
            except Exception:
                pass

        where_parts = []
        params = []
        cat_name = (current_category.get('name') or '').strip() if current_category else ''
        normalized_slug = (slug or '').strip().lower()

        category_id = None
        try:
            # Prefer the categoryID already resolved on current_category.
            if current_category:
                raw_cid = current_category.get('categoryID') or current_category.get('category_id') or current_category.get('id')
                try:
                    category_id = int(raw_cid) if raw_cid is not None else None
                except (TypeError, ValueError):
                    category_id = None
            if category_id is None and categories:
                for c in categories:
                    cid = c.get('categoryID') or c.get('id')
                    c_slug = (c.get('slug') or '').strip().lower()
                    c_name = (c.get('name') or '').strip().lower()
                    if (c_slug and c_slug == normalized_slug) or (cat_name and c_name == cat_name.lower()):
                        try:
                            category_id = int(cid) if cid is not None else None
                        except (TypeError, ValueError):
                            category_id = None
                        break
        except Exception:
            category_id = None

        if 'category_slug' in prod_cols:
            where_parts.append("LOWER(category_slug) = %s")
            params.append(normalized_slug)
        if 'category' in prod_cols:
            where_parts.append("LOWER(category) = %s")
            params.append(normalized_slug)
            if cat_name:
                where_parts.append("LOWER(category) = %s")
                params.append(cat_name.lower())
        if ('categoryid' in prod_cols or 'category_id' in prod_cols) and category_id is not None:
            id_col = 'categoryID' if 'categoryid' in prod_cols else 'category_id'
            where_parts.append(f"{id_col} = %s")
            params.append(category_id)

        # Safety: if the caller passed a slug but we could not build a filter
        # (no slug/category text column AND no resolved category_id), refuse
        # to return all products — that would silently show the wrong list.
        if slug and not where_parts:
            try:
                app.logger.info(
                    "Category filter could not resolve slug '%s' to any column or categoryID; returning empty.",
                    slug,
                )
            except Exception:
                pass
            return result

        where_clause = ''
        query_params = tuple(params) if where_parts else tuple()
        if where_parts:
            where_clause = " WHERE (" + " OR ".join(where_parts) + ")"

        # Count
        count_sql = "SELECT COUNT(*) AS total FROM products" + where_clause
        cur.execute(count_sql, query_params)
        row = cur.fetchone() or {}
        total_products = int(row.get('total') or row.get('COUNT(*)') or 0)
        if total_products:
            total_pages = max(1, math.ceil(total_products / per_page))
            page = min(max(1, page), total_pages)
        else:
            total_pages = 1
            page = 1
        offset = (page - 1) * per_page

        data_sql = "SELECT * FROM products" + where_clause + " ORDER BY productID DESC LIMIT %s OFFSET %s"
        data_params = list(query_params)
        data_params.extend([per_page, offset])
        cur.execute(data_sql, tuple(data_params))
        products = cur.fetchall() or []

    except Exception:
        app.logger.exception("Category filter query failed; falling back to paginated results for slug '%s'", slug)
        try:
            cur.execute("SELECT COUNT(*) AS total FROM products")
            row = cur.fetchone() or {}
            total_products = int(row.get('total') or 0)
            if total_products:
                total_pages = max(1, math.ceil(total_products / per_page))
                page = min(max(1, page), total_pages)
            else:
                total_pages = 1
                page = 1
            offset = (page - 1) * per_page
            cur.execute("SELECT * FROM products ORDER BY productID DESC LIMIT %s OFFSET %s", (per_page, offset))
            products = cur.fetchall() or []
        except Exception:
            products = []
            total_products = 0
            total_pages = 1
            page = 1
    finally:
        try:
            cur.close()
        except Exception:
            pass

    # Normalize image URLs and include gallery images
    try:
        normalized = []
        upload_folder = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)
        for r in products:
            if not isinstance(r, dict):
                normalized.append(r)
                continue
            img = r.get('image_path') or r.get('image') or r.get('main_image') or r.get('imageurl') or r.get('store_logo')

            images_list = []
            if img and isinstance(img, str):
                for p in img.split(','):
                    if p.strip():
                        try:
                            images_list.append(url_for('uploaded_file', filename=p.strip()))
                        except Exception:
                            pass

            if img and isinstance(img, str) and ',' in img:
                img = img.split(',')[0]

            img_url = None
            if img:
                full_path = os.path.join(upload_folder, img)
                if os.path.exists(full_path):
                    try:
                        img_url = url_for('uploaded_file', filename=img)
                    except Exception:
                        img_url = None
            if not img_url:
                img_url = url_for('static', filename='images/default.png')

            rr = dict(r)
            rr['image_url'] = img_url
            rr['images'] = images_list
            if 'name' not in rr and rr.get('title'):
                rr['name'] = rr.get('title')
            normalized.append(rr)
        products = normalized
    except Exception:
        pass

    try:
        products = _filter_out_frozen_products(conn, products)
    except Exception:
        pass

    result.update({
        'products': products,
        'total_products': total_products,
        'total_pages': total_pages,
        'page': page,
        'per_page': per_page,
    })
    return result

@app.route('/category/<slug>')
def category_page(slug):
    """Render a category page for the given slug and list products whose category matches the slug.
    Falls back to a base template when a specific file does not exist.
    """
    # Load categories from database
    categories = []
    current_category = None
    products = []
    requested_page = _safe_int(request.args.get('page'), 1)
    per_page = _safe_int(request.args.get('per_page'), CATEGORY_PAGE_SIZE)
    per_page = max(1, min(per_page, CATEGORY_PAGE_MAX))
    pagination = {
        'page': max(1, requested_page),
        'per_page': per_page,
        'total_pages': 1,
        'total_products': 0,
        'has_prev': False,
        'has_next': False,
        'prev_page': None,
        'next_page': None,
    }
    
    conn = get_db_connection()
    if conn:
        try:
            categories = _fetch_all_categories(conn) or []

            # Find current category by slug (case-insensitive)
            slug_lc = (slug or '').strip().lower()
            current_category = next((c for c in categories if (c.get('slug') or '').strip().lower() == slug_lc), None)
            if not current_category:
                # If not found by slug, try to find by name (convert slug to name)
                category_name = slug.replace('-', ' ').title()
                current_category = next((c for c in categories if c.get('name', '').lower() == category_name.lower()), None)

            # If still not found, create a fallback category
            if not current_category:
                current_category = {'name': slug.replace('-', ' ').title(), 'slug': slug}

            try:
                cur.close()
            except Exception:
                pass
            cur = None

            data = _load_category_products(conn, slug, current_category, categories, page=requested_page, per_page=per_page)
            products = data.get('products', [])
            pagination['page'] = data.get('page', pagination['page'])
            pagination['per_page'] = data.get('per_page', pagination['per_page'])
            pagination['total_pages'] = max(1, data.get('total_pages', 1) or 1)
            pagination['total_products'] = data.get('total_products', len(products))
            pagination['has_prev'] = pagination['page'] > 1
            pagination['has_next'] = pagination['page'] < pagination['total_pages']
            pagination['prev_page'] = pagination['page'] - 1 if pagination['has_prev'] else None
            pagination['next_page'] = pagination['page'] + 1 if pagination['has_next'] else None
                    
        except Exception:
            app.logger.exception("Failed to load data for category '%s'", slug)
            products = []
        finally:
            try:
                if cur:
                    cur.close()
                conn.close()
            except Exception:
                pass

    # Prefer specific template if it exists, else use base
    from os import path as _path
    template_specific = f"categories/{slug}.html"
    template_base = "categories/category_base.html"
    template_path = _path.join(parent_dir, 'templates', 'categories', f'{slug}.html')
    template_to_render = template_specific if _path.exists(template_path) else template_base

    return render_template(template_to_render, products=products, categories=categories, current_category=current_category, pagination=pagination)

@app.route('/api/categories/<slug>')
def api_category(slug):
    """Return JSON payload for a category, mirroring the data used by category_page.
    
    This endpoint is used by frontend scripts (e.g., category_page.js) for AJAX
    category switching. It intentionally reuses the same category and product
    selection logic as category_page, but returns JSON instead of rendering
    a template.
    """
    categories = []
    current_category = None
    products = []
    popular = None
    page = _safe_int(request.args.get('page'), 1)
    per_page = _safe_int(request.args.get('per_page'), CATEGORY_PAGE_SIZE)
    per_page = max(1, min(per_page, CATEGORY_PAGE_MAX))
    pagination = {
        'page': max(1, page),
        'per_page': per_page,
        'total_pages': 1,
        'total_products': 0,
        'has_prev': False,
        'has_next': False,
        'prev_page': None,
        'next_page': None,
    }

    conn = get_db_connection()
    if conn:
        cur = None
        try:
            categories = _fetch_all_categories(conn) or []

            # Find current category by slug (case-insensitive)
            slug_lc = (slug or '').strip().lower()
            current_category = next((c for c in categories if (c.get('slug') or '').strip().lower() == slug_lc), None)
            if not current_category:
                category_name = slug.replace('-', ' ').title()
                current_category = next((c for c in categories if c.get('name', '').lower() == category_name.lower()), None)

            if not current_category:
                app.logger.warning(
                    "api_category: slug '%s' not found in categories: %s",
                    slug,
                    [(c.get('slug'), c.get('name')) for c in categories],
                )
                current_category = {'name': slug.replace('-', ' ').title(), 'slug': slug}
            try:
                cur.close()
            except Exception:
                pass
            cur = None

            data = _load_category_products(conn, slug, current_category, categories, page=page, per_page=per_page)
            products = data.get('products', [])
            pagination['page'] = data.get('page', pagination['page'])
            pagination['per_page'] = data.get('per_page', pagination['per_page'])
            pagination['total_pages'] = max(1, data.get('total_pages', 1) or 1)
            pagination['total_products'] = data.get('total_products', len(products))
            pagination['has_prev'] = pagination['page'] > 1
            pagination['has_next'] = pagination['page'] < pagination['total_pages']
            pagination['prev_page'] = pagination['page'] - 1 if pagination['has_prev'] else None
            pagination['next_page'] = pagination['page'] + 1 if pagination['has_next'] else None

        except Exception:
            app.logger.exception("Failed to load data for category '%s' (API)", slug)
            products = []
        finally:
            try:
                if cur:
                    cur.close()
                conn.close()
            except Exception:
                pass

    if not current_category:
        current_category = {'name': slug.replace('-', ' ').title(), 'slug': slug}

    return jsonify({
        'category': current_category,
        'products': products,
        'pagination': pagination,
        'popular': popular,
    })

@app.route('/admin/profile')
def admin_profile():
    if not admin_required():
        return redirect(url_for('login'))
    admin_obj = session.get('admin') or session.get('user') or {}
    return render_template('admin_profile.html', admin=admin_obj)

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
            SELECT sellerID AS id, sellername, selleremail, contactnumber, storename, storedesc,
                   region, province, city, barangay, status, IFNULL(seller_category, '') AS seller_category,
                   storelogo_path, businesspermit_path, created_at
            FROM sellers
            ORDER BY sellerID DESC
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
              'seller_category': row.get('seller_category'),
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

def _ensure_financial_columns(conn):
    """Ensure financial_transactions has seller_net and vat_amount columns."""
    if not conn:
        return
    try:
        cur = conn.cursor()
        # Check/Add seller_net
        try:
            cur.execute("SHOW COLUMNS FROM financial_transactions LIKE 'seller_net'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE financial_transactions ADD COLUMN seller_net DECIMAL(12,2) NOT NULL DEFAULT 0.00")
        except Exception:
            pass
            
        # Check/Add vat_amount
        try:
            cur.execute("SHOW COLUMNS FROM financial_transactions LIKE 'vat_amount'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE financial_transactions ADD COLUMN vat_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00")
        except Exception:
            pass
        
        conn.commit()
        cur.close()
    except Exception:
        pass

@app.route('/seller-dashboard')
@app.route('/seller/dashboard')
def seller_dashboard():
    seller = session.get('seller')
    if not seller:
        return redirect(url_for('seller_login'))
    seller_id = seller.get('id') or seller.get('sellerID')
    seller_products = []
    categories = []
    orders = []
    order_reports = []
    order_reports_json = []
    stats = {
        'total_products': 0,
        'total_earnings': 0.0,
        'total_orders': 0,
        'total_ratings': 0
    }
    
    conn = get_db_connection()
    if conn:
        try:
            _ensure_financial_columns(conn)
            cur = conn.cursor(dictionary=True)
            
            # Refresh seller info to ensure storename is up to date
            if seller_id:
                cur.execute("SELECT storename, sellername, status, storelogo_path FROM sellers WHERE sellerID = %s", (seller_id,))
                s_row = cur.fetchone()
                if s_row:
                    seller['storename'] = s_row.get('storename')
                    seller['sellername'] = s_row.get('sellername')
                    seller['status'] = s_row.get('status')
                    if s_row.get('storelogo_path'):
                        seller['storelogo_path'] = s_row.get('storelogo_path')
                    # Update session
                    session['seller'] = seller

            # Fetch seller products
            if seller_id:
                cur.execute(
                    "SELECT * FROM products WHERE sellerID = %s ORDER BY productID DESC",
                    (seller_id,)
                )
                seller_products = cur.fetchall() or []
            
            # Fetch seller orders for dashboard
            if seller_id:
                cur.execute("""
                    SELECT 
                        so.*,
                        u.username as customer_name,
                        r.ridername AS rider_name,
                        GROUP_CONCAT(
                            CONCAT(
                                '{"order_item_id":', soi.itemID,
                                ',"productID":', soi.productID,
                                ',"name":"', COALESCE(p.name, 'Unknown'), '"',
                                ',"quantity":', soi.quantity,
                                ',"price":', soi.price,
                                ',"image_path":"', COALESCE(p.image_path, ''), '"}'
                            ) SEPARATOR ','
                        ) AS items_json
                    FROM seller_orders so
                    LEFT JOIN seller_order_items soi ON so.sellerOrderID = soi.sellerOrderID 
                    LEFT JOIN products p ON soi.productID = p.productID
                    LEFT JOIN users u ON so.userID = u.userID
                    LEFT JOIN riders r ON so.riderID = r.riderID
                    WHERE so.sellerID = %s
                    GROUP BY so.sellerOrderID
                    ORDER BY so.created_at DESC
                    LIMIT 5
                """, (seller_id,))
                db_orders = cur.fetchall()

                # Process the orders and parse the JSON items
                for order in db_orders:
                    try:
                        items_json = order.get('items_json')
                        items = []
                        if items_json:
                            try:
                                # Parse GROUP_CONCAT JSON format: {"item1"},{"item2"}
                                items_json = '[' + items_json + ']'
                                items = json.loads(items_json)
                            except Exception:
                                # Fallback: try to parse individual items
                                items = []
                                for part in (items_json or '').split(','):
                                    try:
                                        items.append(json.loads(part))
                                    except Exception:
                                        continue

                        # Normalize item types and provide safe defaults
                        processed_items = []
                        for it in items:
                            try:
                                processed_items.append({
                                    'order_item_id': it.get('order_item_id'),
                                    'productID': it.get('productID'),
                                    'name': it.get('name'),
                                    'quantity': int(it.get('quantity') or 0),
                                    'price': float(it.get('price') or 0.0),
                                    'image_path': it.get('image_path')
                                })
                            except Exception:
                                continue

                        orders.append({
                            'order_number': order.get('order_number'),
                            'sellerOrderID': order.get('sellerOrderID'),
                            'total_amount': float(order.get('total_amount') or 0.0),
                            'status': order.get('status') or 'pending',
                            'created_at': order.get('created_at'),
                            'updated_at': order.get('updated_at'),
                            'customer_name': order.get('customer_name'),
                            'rider_name': order.get('rider_name'),
                            'shipping_address': order.get('shipping_address'),
                            'contact_number': order.get('contact_number'),
                            'payment_method': order.get('payment_method') or 'cash_on_delivery',
                            'items': processed_items
                        })
                    except Exception as e:
                        app.logger.exception(f"Error processing order {order.get('sellerOrderID')}: {e}")
                        continue
            
            # Fetch order-related reports submitted by users
            if seller_id:
                try:
                    cur.execute(
                        """
                        SELECT r.*, u.username AS reporter_username, so.order_number, so.status AS order_status,
                               so.total_amount, so.userID, so.riderID, riders.ridername
                        FROM reports r
                        LEFT JOIN seller_orders so ON r.reported_order_id = so.sellerOrderID
                        LEFT JOIN users u ON r.reporter_id = u.userID
                        LEFT JOIN riders ON so.riderID = riders.riderID
                        WHERE r.reported_shop_id = %s AND r.reported_order_id IS NOT NULL
                        ORDER BY r.created_at DESC
                        LIMIT 50
                        """,
                        (seller_id,)
                    )
                    report_rows = cur.fetchall() or []
                    for rep in report_rows:
                        created_at = rep.get('created_at')
                        escalated_at = rep.get('escalated_at')
                        order_reports.append({
                            'id': rep.get('id'),
                            'order_id': rep.get('reported_order_id'),
                            'order_number': rep.get('order_number'),
                            'status': rep.get('status'),
                            'issue_type': rep.get('issue_type') or rep.get('complaint_type'),
                            'description': rep.get('description'),
                            'message': rep.get('message'),
                            'created_at': created_at,
                            'reporter_name': rep.get('reporter_name') or rep.get('reporter_username'),
                            'reporter_username': rep.get('reporter_username'),
                            'total_amount': float(rep.get('total_amount') or 0.0) if rep.get('total_amount') is not None else None,
                            'rider_id': rep.get('reported_rider_id') or rep.get('riderID'),
                            'rider_name': rep.get('ridername'),
                            'escalated_to_admin': bool(rep.get('escalated_to_admin')),
                            'escalated_at': escalated_at,
                            'escalation_note': rep.get('escalation_note')
                        })
                except Exception:
                    app.logger.debug('Failed to load order reports for seller %s', seller_id, exc_info=True)

            # Prepare JSON serializable reports
            order_reports_json = []
            for r in order_reports:
                item = r.copy()
                if isinstance(item.get('created_at'), datetime):
                    item['created_at'] = item['created_at'].isoformat()
                else:
                    item['created_at'] = str(item['created_at']) if item.get('created_at') else None
                
                if isinstance(item.get('escalated_at'), datetime):
                    item['escalated_at'] = item['escalated_at'].isoformat()
                else:
                    item['escalated_at'] = str(item['escalated_at']) if item.get('escalated_at') else None
                order_reports_json.append(item)

            # Calculate stats
            stats['total_products'] = len(seller_products)
            
            # Calculate total orders (all time)
            try:
                cur.execute("SELECT COUNT(*) as cnt FROM seller_orders WHERE sellerID = %s", (seller_id,))
                row = cur.fetchone()
                stats['total_orders'] = row['cnt'] if row else 0
            except Exception:
                stats['total_orders'] = 0

            # Calculate total earnings (only released revenue)
            try:
                # Hybrid calculation: use recorded net if available and valid, else estimate with 7% deduction (5% comm + 2% platform fee)
                cur.execute("""
                    SELECT 
                        SUM(
                            CASE 
                                WHEN ft.seller_net IS NOT NULL AND ft.seller_net > 0 THEN ft.seller_net 
                                ELSE (so.total_amount * 0.93) 
                            END
                        ) as earnings
                    FROM seller_orders so
                    LEFT JOIN financial_transactions ft ON so.sellerOrderID = ft.order_id
                    WHERE so.sellerID = %s AND so.revenue_released = 1
                """, (seller_id,))
                row = cur.fetchone()
                stats['total_earnings'] = float(row['earnings']) if row and row['earnings'] else 0.0
            except Exception:
                stats['total_earnings'] = 0.0

            # Calculate pending orders
            try:
                cur.execute("SELECT COUNT(*) as cnt FROM seller_orders WHERE sellerID = %s AND status NOT IN ('delivered', 'cancelled', 'returned')", (seller_id,))
                row = cur.fetchone()
                stats['pending_orders'] = row['cnt'] if row else 0
            except Exception:
                stats['pending_orders'] = 0
            
            categories, _ = _fetch_seller_allowed_categories(conn, seller_id, fallback_to_all=False)
                
        except Exception:
            app.logger.exception("Failed to load seller data")
            seller_products = []
            categories = []
            orders = []
        finally:
            try: cur.close()
            except: pass
            try: conn.close()
            except: pass
    
    restriction_state = getattr(g, 'seller_restriction_state', None)
    if restriction_state is None and seller_id:
        restriction_state = _load_seller_restriction_state(seller_id)
        g.seller_restriction_state = restriction_state

    return render_template('seller_dashboard.html', 
                         seller_products=seller_products, 
                         seller=seller, 
                         categories=categories,
                         orders=orders,
                         stats=stats,
                         order_reports=order_reports,
                         order_reports_json=order_reports_json,
                         restriction_state=restriction_state)

# Seller Profile page (view + edit)
@app.route('/seller/profile', methods=['GET', 'POST'])
def seller_profile():
    seller = session.get('seller') or {}
    seller_id = seller.get('id') or seller.get('sellerID')
    if not seller_id:
        return redirect(url_for('seller_login'))
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if request.method == 'POST':
            seller_name = (request.form.get('seller_name') or '').strip()
            store_name = (request.form.get('store_name') or '').strip()
            email = (request.form.get('selleremail') or '').strip()
            phone = (request.form.get('contactnumber') or '').strip()
            address = (request.form.get('address') or '').strip()
            region = (request.form.get('region') or '').strip() or None
            province = (request.form.get('province') or '').strip() or None
            city = (request.form.get('city') or '').strip() or None
            barangay = (request.form.get('barangay') or '').strip() or None
            try:
                cur.execute(
                    """
                    UPDATE sellers
                    SET sellername = %s, storename = %s, selleremail = %s, contactnumber = %s,
                        exact_address = %s, region = %s, province = %s, city = %s, barangay = %s
                    WHERE sellerID = %s
                    """,
                    (seller_name or seller.get('sellername'), store_name or seller.get('storename'),
                     email or seller.get('selleremail'), phone or seller.get('contactnumber'),
                     address or seller.get('address'), region, province, city, barangay, seller_id)
                )
                conn.commit()
                seller['sellername'] = seller_name or seller.get('sellername')
                seller['storename'] = store_name or seller.get('storename')
                seller['selleremail'] = email or seller.get('selleremail')
                seller['contactnumber'] = phone or seller.get('contactnumber')
                seller['address'] = address or seller.get('address')
                session['seller'] = seller
                flash('Profile updated', 'success')
            except Exception:
                try: conn.rollback()
                except Exception: pass
                flash('Failed to update profile', 'danger')
        # Load latest row for render
        cur.execute("""
            SELECT sellerID, sellername, storename, selleremail, contactnumber,
                   exact_address AS address, storelogo_path, storedesc,
                   region, province, city, barangay
            FROM sellers
            WHERE sellerID = %s
            LIMIT 1
        """, (seller_id,))
        row = cur.fetchone() or {}
        seller_payload = {
            'id': row.get('sellerID') or seller_id,
            'sellerID': row.get('sellerID') or seller_id,
            'name': row.get('sellername') or seller.get('sellername') or 'Seller',
            'sellername': row.get('sellername') or seller.get('sellername') or '',
            'store_name': row.get('storename') or seller.get('storename') or '',
            'storename': row.get('storename') or seller.get('storename') or '',
            'selleremail': row.get('selleremail') or seller.get('selleremail') or '',
            'contactnumber': row.get('contactnumber') or seller.get('contactnumber') or '',
            'address': row.get('address') or seller.get('address') or '',
            'storelogo_path': row.get('storelogo_path') or seller.get('storelogo_path') or '',
            'storedesc': row.get('storedesc') or seller.get('storedesc') or '',
            'region': row.get('region') or '',
            'province': row.get('province') or '',
            'city': row.get('city') or '',
            'barangay': row.get('barangay') or '',
        }
        return render_template('seller_profile.html', seller=seller_payload)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if conn: conn.close()
        except Exception:
            pass

@app.route('/seller/settings/password', methods=['POST'])
def seller_settings_password():
    seller = session.get('seller') or {}
    seller_id = seller.get('id') or seller.get('sellerID')
    if not seller_id:
        return redirect(url_for('seller_login'))
    current_password = request.form.get('current_password') or ''
    new_password = request.form.get('new_password') or ''
    confirm_password = request.form.get('confirm_password') or ''
    if not new_password or new_password != confirm_password:
        flash('Passwords do not match', 'danger')
        return redirect(url_for('seller_profile'))
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT sellerpass FROM sellers WHERE sellerID = %s", (seller_id,))
        row = cur.fetchone() or {}
        hashed = row.get('sellerpass') or ''
        if not hashed or not check_password_hash(hashed, current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('seller_profile'))
        new_hash = generate_password_hash(new_password)
        cur.execute("UPDATE sellers SET sellerpass = %s WHERE sellerID = %s", (new_hash, seller_id))
        conn.commit()
        flash('Password updated', 'success')
        return redirect(url_for('seller_profile'))
    except Exception:
        try: conn.rollback()
        except Exception: pass
        flash('Failed to update password', 'danger')
        return redirect(url_for('seller_profile'))
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if conn: conn.close()
        except Exception:
            pass


@app.route('/seller/restrictions/explanation', methods=['POST'])
def seller_submit_explanation():
    seller = session.get('seller') or {}
    seller_id = seller.get('sellerID') or seller.get('id')
    if not seller_id:
        return jsonify({'success': False, 'msg': 'unauthorized'}), 401

    state = getattr(g, 'seller_restriction_state', None)
    if state is None:
        state = _load_seller_restriction_state(seller_id)
        g.seller_restriction_state = state

    if not state or (state.get('level') or 0) < 2:
        return jsonify({'success': False, 'msg': 'no_active_restriction'}), 400

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        subject = (payload.get('subject') or '').strip()
        message = (payload.get('message') or '').strip()
    else:
        subject = (request.form.get('subject') or '').strip()
        message = (request.form.get('message') or '').strip()
    if not subject or not message:
        return jsonify({'success': False, 'msg': 'missing_fields'}), 400

    attachment_file = None
    if request.files:
        attachment_file = request.files.get('attachment') or request.files.get('file')

    attachment_path = None
    saved_path = None
    if attachment_file and attachment_file.filename:
        filename = secure_filename(attachment_file.filename)
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext != '.pdf':
                return jsonify({'success': False, 'msg': 'invalid_file_type'}), 400
            target_dir = os.path.join(UPLOAD_DIR, 'restrictions')
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception:
                pass
            unique_name = f"explanation_{seller_id}_{uuid.uuid4().hex}{ext}"
            saved_path = os.path.join(target_dir, unique_name)
            attachment_file.save(saved_path)
            attachment_path = os.path.join('restrictions', unique_name)

    conn = get_db_connection()
    if not conn:
        if saved_path:
            try:
                os.remove(saved_path)
            except Exception:
                pass
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    try:
        _ensure_restriction_tables(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO seller_restriction_responses (sellerID, report_id, offense_level, response_type, subject, message, attachment_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                seller_id,
                state.get('report_id'),
                state.get('level') or 2,
                'explanation',
                subject,
                message,
                attachment_path,
            )
        )
        conn.commit()
        g.seller_restriction_state = _load_seller_restriction_state(seller_id)

        email_subject = f'Seller #{seller_id} submitted an explanation'
        email_body = (
            f'Seller #{seller_id} submitted an explanation for restriction level {state.get("level") or 2}.\n\n'
            f'Subject: {subject}\n\n{message}\n'
        )
        try:
            _send_email_direct(email_subject, [ADMIN_COMPLIANCE_EMAIL], email_body)
        except Exception:
            pass
        emit_notification_event('admin', 0, 'Seller explanation received', f'Seller #{seller_id}: {subject}')

        return jsonify({'success': True}), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        if saved_path:
            try:
                os.remove(saved_path)
            except Exception:
                pass
        app.logger.exception('Failed to store seller explanation')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/seller/restrictions/appeal', methods=['POST'])
def seller_submit_appeal():
    seller = session.get('seller') or {}
    seller_id = seller.get('sellerID') or seller.get('id')
    if not seller_id:
        return jsonify({'success': False, 'msg': 'unauthorized'}), 401

    state = getattr(g, 'seller_restriction_state', None)
    if state is None:
        state = _load_seller_restriction_state(seller_id)
        g.seller_restriction_state = state

    if not state or (state.get('level') or 0) < 3:
        return jsonify({'success': False, 'msg': 'no_active_freeze'}), 400

    payload = request.get_json(silent=True) or {}
    subject = (payload.get('subject') or '').strip() or 'Account unfreeze appeal'
    reason = (payload.get('message') or '').strip()
    if not reason:
        return jsonify({'success': False, 'msg': 'missing_fields'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    try:
        _ensure_restriction_tables(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO seller_restriction_responses (sellerID, report_id, offense_level, response_type, subject, message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                seller_id,
                state.get('report_id'),
                state.get('level') or 3,
                'appeal',
                subject,
                reason,
            )
        )
        conn.commit()
        g.seller_restriction_state = _load_seller_restriction_state(seller_id)

        email_subject = f'Seller #{seller_id} requested account unfreeze'
        if state.get('report_id'):
            email_subject += f' (Report #{state.get("report_id")})'
            
        email_body = (
            f'Seller #{seller_id} submitted an appeal for account unfreeze.\n'
            f'Report ID: {state.get("report_id") or "N/A"}\n\n'
            f'Subject: {subject}\n\n{reason}\n'
        )
        try:
            _send_email_direct(email_subject, [ADMIN_COMPLIANCE_EMAIL], email_body)
        except Exception:
            pass
        
        notif_extra = {'report_id': state.get('report_id')} if state.get('report_id') else None
        emit_notification_event('admin', 0, 'Seller unfreeze appeal', f'Seller #{seller_id} submitted an appeal.', extra=notif_extra)

        return jsonify({'success': True}), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('Failed to store seller appeal')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def _ensure_dict_cursor(conn):
    try:
        return conn.cursor(dictionary=True)
    except Exception:
        return None

def _format_stats_date(value):
    if not value:
        return None
    try:
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return str(value)[:10]
    except Exception:
        return str(value)

@app.route('/api/seller/stats/summary')
def api_seller_stats_summary():
    """Aggregate KPIs for the seller dashboard mobile view: product count,
    earnings (delivered orders), pending order count, and total order count.
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'msg': 'not_authenticated'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = _ensure_dict_cursor(conn)
    if not cur:
        try: conn.close()
        except Exception: pass
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    try:
        cur.execute(
            "SELECT COUNT(*) AS c FROM products WHERE sellerID = %s",
            (seller_id,),
        )
        total_products = int((cur.fetchone() or {}).get('c') or 0)

        cur.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN status = 'delivered' THEN total_amount ELSE 0 END), 0) AS earnings,
              COUNT(*) AS total_orders,
              SUM(CASE WHEN status IN ('pending', 'processing', 'preparing', 'awaiting_pickup') THEN 1 ELSE 0 END) AS pending_orders,
              SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders
            FROM seller_orders
            WHERE sellerID = %s
            """,
            (seller_id,),
        )
        agg = cur.fetchone() or {}

        return jsonify({
            'success': True,
            'data': {
                'total_products':   total_products,
                'total_earnings':   float(agg.get('earnings') or 0.0),
                'total_orders':     int(agg.get('total_orders') or 0),
                'pending_orders':   int(agg.get('pending_orders') or 0),
                'delivered_orders': int(agg.get('delivered_orders') or 0),
            },
        }), 200
    except Exception:
        app.logger.exception('Failed to compute seller summary stats')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@app.route('/api/seller/stats/sales')
def api_seller_stats_sales():
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'msg': 'not_authenticated'}), 401

    range_param = (request.args.get('range') or 'daily').lower()
    if range_param != 'daily':
        return jsonify({'success': False, 'msg': 'unsupported_range'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = _ensure_dict_cursor(conn)
    if not cur:
        try: conn.close()
        except Exception: pass
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    try:
        cur.execute("""
            SELECT DATE(created_at) AS day, COALESCE(SUM(total_amount), 0) AS total_sales
            FROM seller_orders
            WHERE sellerID = %s
              AND (status IS NULL OR status = 'delivered')
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            LIMIT 30
        """, (seller_id,))
        rows = cur.fetchall() or []
        data = [{
            'date': _format_stats_date(row.get('day')),
            'total_sales': float(row.get('total_sales') or 0.0)
        } for row in rows]
        return jsonify({'success': True, 'range': 'daily', 'data': data}), 200
    except Exception:
        app.logger.exception('Failed to compute seller sales stats')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

@app.route('/api/seller/stats/orders')
def api_seller_stats_orders():
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'msg': 'not_authenticated'}), 401

    range_param = (request.args.get('range') or 'daily').lower()
    if range_param != 'daily':
        return jsonify({'success': False, 'msg': 'unsupported_range'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = _ensure_dict_cursor(conn)
    if not cur:
        try: conn.close()
        except Exception: pass
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    try:
        cur.execute("""
            SELECT DATE(created_at) AS day, COUNT(*) AS order_count
            FROM seller_orders
            WHERE sellerID = %s
              AND (status IS NULL OR status <> 'cancelled')
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            LIMIT 30
        """, (seller_id,))
        rows = cur.fetchall() or []
        data = [{
            'date': _format_stats_date(row.get('day')),
            'order_count': int(row.get('order_count') or 0)
        } for row in rows]
        return jsonify({'success': True, 'range': 'daily', 'data': data}), 200
    except Exception:
        app.logger.exception('Failed to compute seller order stats')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

@app.route('/api/seller/stats/recent-orders')
def api_seller_recent_orders():
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'msg': 'not_authenticated'}), 401

    limit = request.args.get('limit', default=10, type=int)
    try:
        limit = max(1, min(limit, 50))
    except Exception:
        limit = 10

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = _ensure_dict_cursor(conn)
    if not cur:
        try: conn.close()
        except Exception: pass
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    try:
        cur.execute("""
            SELECT so.*, u.username AS customer_name
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.sellerID = %s
            ORDER BY so.created_at DESC
            LIMIT %s
        """, (seller_id, limit))
        orders = cur.fetchall() or []
        if not orders:
            return jsonify({'success': True, 'data': []}), 200

        order_ids = [row.get('sellerOrderID') for row in orders if row.get('sellerOrderID') is not None]
        items_map = {oid: [] for oid in order_ids}

        if order_ids:
            placeholders = ','.join(['%s'] * len(order_ids))
            cur.execute(f"""
                SELECT soi.*, p.name AS product_name
                FROM seller_order_items soi
                LEFT JOIN products p ON soi.productID = p.productID
                WHERE soi.sellerOrderID IN ({placeholders})
            """, tuple(order_ids))
            for item in cur.fetchall() or []:
                oid = item.get('sellerOrderID')
                items_map.setdefault(oid, []).append(item)

        data = []
        for order in orders:
            oid = order.get('sellerOrderID')
            items = items_map.get(oid, []) if oid else []
            total_qty = sum(int(it.get('quantity') or 0) for it in items)
            primary_item = items[0] if items else None
            if primary_item:
                base_name = primary_item.get('product_name') or f"Product #{primary_item.get('productID')}"
                extra = len(items) - 1
                product_label = base_name + (f" (+{extra} more)" if extra > 0 else '')
                unit_price = float(primary_item.get('price') or 0)
            else:
                product_label = '—'
                unit_price = 0.0

            order_date = order.get('created_at')
            if hasattr(order_date, 'strftime'):
                order_date_str = order_date.strftime('%Y-%m-%d %H:%M')
            else:
                order_date_str = str(order_date) if order_date else None

            payment_status = order.get('payment_status')
            if not payment_status:
                payment_status = 'Paid' if (order.get('status') == 'delivered') else 'Pending'

            shipping_status = order.get('shipping_status') or order.get('status') or 'pending'

            data.append({
                'order_id': oid,
                'order_number': order.get('order_number'),
                'customer_name': order.get('customer_name') or '—',
                'product': product_label,
                'quantity': total_qty or (primary_item.get('quantity') if primary_item else 0),
                'unit_price': unit_price,
                'total': float(order.get('total_amount') or 0.0),
                'order_status': order.get('status') or 'pending',
                'payment_status': payment_status,
                'shipping_status': shipping_status,
                'order_date': order_date_str,
            })

        return jsonify({'success': True, 'data': data}), 200
    except Exception:
        app.logger.exception('Failed to load seller recent orders')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@app.route('/api/seller/reports/<report_id>/escalate', methods=['POST'])
def api_seller_escalate_report(report_id):
    try:
        report_id = int(report_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'msg': 'Invalid report ID'}), 400

    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'msg': 'not_authenticated'}), 401

    data = request.get_json(silent=True) or {}
    note = (data.get('note') or '').strip()
    if not note:
        return jsonify({'success': False, 'msg': 'Please include escalation details'}), 400

    app.logger.info(f"Seller {seller_id} escalating report {report_id}")

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, reported_shop_id, reported_order_id, reported_rider_id, reporter_name
            FROM reports
            WHERE id = %s
            LIMIT 1
            """,
            (report_id,)
        )
        report_row = cur.fetchone()
        if not report_row:
            app.logger.warning(f"Report {report_id} not found in DB")
            return jsonify({'success': False, 'msg': 'Report not found'}), 404
        
        if int(report_row.get('reported_shop_id') or 0) != int(seller_id):
            app.logger.warning(f"Report {report_id} belongs to shop {report_row.get('reported_shop_id')}, not {seller_id}")
            return jsonify({'success': False, 'msg': 'Report not found'}), 404

        cur.execute(
            """
            UPDATE reports
            SET status = 'escalated', escalated_to_admin = 1, escalated_by = %s,
                escalated_at = NOW(), escalation_note = %s
            WHERE id = %s
            """,
            (seller_id, note, report_id)
        )

        escalated_at_value = None
        try:
            cur.execute(
                "SELECT escalated_at FROM reports WHERE id = %s",
                (report_id,)
            )
            ts_row = cur.fetchone() or {}
            escalated_at_value = ts_row.get('escalated_at')
        except Exception:
            escalated_at_value = None

        try:
            admin_body = f"Seller #{seller_id} escalated report #{report_id} for order #{report_row.get('reported_order_id') or 'N/A'}."
            if report_row.get('reported_rider_id'):
                admin_body += f" Rider #{report_row.get('reported_rider_id')} flagged."
            admin_body += f" Details: {note}"
            cur.execute(
                "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('admin', %s, %s, %s)",
                (0, 'Escalated order report', admin_body)
            )
            emit_notification_event('admin', 0, 'Escalated order report', admin_body)
        except Exception:
            pass

        conn.commit()
        if escalated_at_value and isinstance(escalated_at_value, datetime):
            escalated_at_payload = escalated_at_value.isoformat()
        elif escalated_at_value:
            escalated_at_payload = str(escalated_at_value)
        else:
            escalated_at_payload = None

        return jsonify({
            'success': True,
            'msg': 'Report escalated to admin',
            'escalated_at': escalated_at_payload
        }), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('Seller escalation failed')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/seller/add-product')
def seller_add_product_page():
    seller = session.get('seller')
    if not seller:
        return redirect(url_for('seller_login'))

    categories = []
    conn = get_db_connection()
    seller_category = None
    if conn:
        try:
            categories, _ = _fetch_seller_allowed_categories(conn, seller.get('sellerID'), fallback_to_all=False)
            if not categories:
                try:
                    cur = conn.cursor(dictionary=True)
                    cur.execute("SELECT seller_category FROM sellers WHERE sellerID = %s", (seller.get('sellerID'),))
                    row = cur.fetchone()
                    if row:
                        seller_category = row.get('seller_category')
                except Exception:
                    seller_category = None
                finally:
                    try:
                        if 'cur' in locals() and cur:
                            cur.close()
                    except Exception:
                        pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return render_template('seller_add_product.html', categories=categories, seller=seller, seller_category=seller_category)


@app.route('/seller/manage-product')
def seller_manage_product_page():
    seller = session.get('seller')
    if not seller:
        return redirect(url_for('seller_login'))

    seller_id = seller.get('id') or seller.get('sellerID')
    seller_products = []

    conn = get_db_connection()
    if conn and seller_id:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM products WHERE sellerID = %s ORDER BY productID DESC", (seller_id,))
            seller_products = cur.fetchall() or []
        except Exception:
            seller_products = []
        finally:
            try: cur.close(); conn.close()
            except Exception: pass

    return render_template('seller_manage_product.html', seller_products=seller_products, seller=seller)

def send_welcome_email(email, username):
    try:
        if not _validate_email_address(email):
            app.logger.warning(f"Skip welcome email: invalid address {email}")
            return
        subject = 'Welcome to Happy Hands!'
        body = f'Hi {username},\n\nWelcome to Happy Hands! We are excited to have you on board.\n\nBest regards,\nHappyHandsPH'
        enqueue_email(subject, [email], body)
    except Exception as e:
        app.logger.exception(f"Failed to enqueue welcome email to {email}: {e}")

def send_seller_welcome_email(selleremail, sellername):
    try:
        if not _validate_email_address(selleremail):
            app.logger.warning(f"Skip seller welcome email: invalid address {selleremail}")
            return
        subject = 'Welcome to Happy Hands!'
        body = f'Hi {sellername},\n\nWelcome to Happy Hands! Please wait for your account to be approved.\n\nBest regards,\nHappyHandsPH'
        enqueue_email(subject, [selleremail], body)
    except Exception as e:
        app.logger.exception(f"Failed to enqueue seller welcome email to {selleremail}: {e}")

def send_approve_email(selleremail, sellername):
    try:
        if not _validate_email_address(selleremail):
            app.logger.warning(f"Skip approve email: invalid address {selleremail}")
            return
        subject = 'Your account has been approved!'
        body = f'Hi {sellername},\n\nYour account has been approved! You can now login to your account.\n\nBest regards,\nHappyHandsPH'
        enqueue_email(subject, [selleremail], body)
    except Exception as e:
        app.logger.exception(f"Failed to enqueue approval email to {selleremail}: {e}")

def send_reject_email(selleremail, sellername):
    try:
        if not _validate_email_address(selleremail):
            app.logger.warning(f"Skip reject email: invalid address {selleremail}")
            return
        subject = 'Your account has been rejected!'
        body = f'Hi {sellername},\n\nYour account has been rejected! Please contact the administrator for more information.\n\nBest regards,\nHappyHandsPH'
        enqueue_email(subject, [selleremail], body)
    except Exception as e:
        app.logger.exception(f"Failed to enqueue rejection email to {selleremail}: {e}")


def send_rider_approve_email(rideremail, ridername):
    try:
        if not _validate_email_address(rideremail):
            app.logger.warning(f"Skip rider approve email: invalid address {rideremail}")
            return
        subject = 'Your rider account has been approved'
        body = f'Hi {ridername},\n\nYour rider account has been approved. You can now log in and accept deliveries.\n\nBest regards,\nHappyHandsPH'
        enqueue_email(subject, [rideremail], body)
    except Exception as e:
        app.logger.exception(f"Failed to enqueue rider approval email to {rideremail}: {e}")


def send_rider_reject_email(rideremail, ridername):
    try:
        if not _validate_email_address(rideremail):
            app.logger.warning(f"Skip rider reject email: invalid address {rideremail}")
            return
        subject = 'Your rider account application'
        body = f'Hi {ridername},\n\nUnfortunately your rider application was not approved. Please contact the administrator for more information.\n\nBest regards,\nHappyHandsPH'
        enqueue_email(subject, [rideremail], body)
    except Exception as e:
        app.logger.exception(f"Failed to enqueue rider rejection email to {rideremail}: {e}")


def send_rider_pending_review_email(rideremail, ridername):
    """Notify a rider that their signup is under admin review."""
    try:
        if not _validate_email_address(rideremail):
            app.logger.warning(f"Skip rider pending email: invalid address {rideremail}")
            return
        subject = 'Your rider account is under review'
        body = (
            f"Hi {ridername},\n\n"
            "Thanks for signing up as a rider. Your account is now under review by our admin team. "
            "You will receive another email once your account is approved.\n\n"
            "Best regards,\nHappyHandsPH"
        )
        enqueue_email(subject, [rideremail], body)
    except Exception as e:
        app.logger.exception(f"Failed to enqueue rider pending email to {rideremail}: {e}")


def send_seller_order_notification(seller_id, order_number, total_amount, shipping_address=None):
    """Notify a seller via email about a new order that was just created for them.
    Best-effort: log and return on any failure, do not raise.
    """
    conn = get_db_connection()
    if not conn:
        app.logger.warning("Email notify skipped: DB connection unavailable while fetching seller info")
        return
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        # Tolerant lookup for seller by id (support sellerID/seller_id/id)
        cur.execute(
            """
            SELECT * FROM sellers
            WHERE sellerID = %s OR seller_id = %s OR id = %s
            LIMIT 1
            """,
            (seller_id, seller_id, seller_id),
        )
        row = cur.fetchone() or {}
        seller_email = row.get('selleremail') or row.get('email')
        seller_name = (
            row.get('storename') or row.get('store_name') or row.get('sellername') or row.get('seller_name') or 'Seller'
        )

        if not seller_email:
            app.logger.warning(f"Email notify skipped: missing email for seller {seller_id}")
            return

        try:
            subject = f"New order received: {order_number}"
            lines = [
                f"Hi {seller_name},",
                "",
                "You have a new order in Happy Hands.",
                f"Order Number: {order_number}",
                f"Total Amount: {total_amount}",
            ]
            if shipping_address:
                lines.append(f"Ship To: {shipping_address}")
            lines.extend([
                "",
                "Please open your Seller Dashboard > Orders to review and start processing.",
                "",
                "Best regards,",
                "HappyHandsPH",
            ])

            msg = Message(subject, recipients=[seller_email])
            msg.body = "\n".join(lines)
            mail.send(msg)
            app.logger.info(f"Seller order notification sent to {seller_email} for order {order_number}")
        except Exception as mail_err:
            app.logger.exception(f"Failed to send seller order notification to {seller_email}: {mail_err}")
    except Exception:
        app.logger.exception("Error looking up seller for email notification")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


# Product management routes
@app.route('/seller/manage/product', methods=['POST'])
def seller_manage_product():
    """Create or update a product. Uses JWT identity (preferred) or session seller as fallback.
    Saves uploaded images (image0..image3) to UPLOAD_FOLDER and stores first image path if product table has image column.
    Also updates session['seller_products'] with the seller's current product list so Manage Products UI can read from session.
    """
    # determine seller id from JWT cookie or session safely (avoid 422 from flask-jwt-extended loaders)
    seller_id = None
    try:
        token = request.cookies.get(app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token'))
        if token:
            decoded = decode_token(token)
            identity = extract_identity_from_decoded(decoded)
            if identity and isinstance(identity, dict) and identity.get('role') == 'seller':
                seller_id = identity.get('sellerID') or identity.get('sellerId') or identity.get('id')
    except Exception:
        seller_id = None

    if not seller_id:
        seller = session.get('seller')
        if seller:
            seller_id = seller.get('id')

    if not seller_id:
        return jsonify({'success': False, 'msg': 'Seller not authenticated'}), 401

    # allow multipart/form-data (files) or normal form submission
    data = request.form or {}
    productID = data.get('productID') or None
    name = (data.get('name') or '').strip()
    price = data.get('price') or None
    description = (data.get('description') or '').strip()
    stock = data.get('stock') or None
    category = (data.get('category') or '').strip()

    # handle image uploads (pick first uploaded image for DB)
    saved_images = []
    try:
        os.makedirs(app.config.get('UPLOAD_FOLDER', UPLOAD_DIR), exist_ok=True)
    except Exception:
        pass

    for i in range(4):
        f = request.files.get(f'image{i}')
        if f and f.filename:
            if not allowed_file(f.filename, ALLOWED_IMAGE_EXT):
                return jsonify({'success': False, 'msg': 'Invalid image file type'}), 400
            fname = secure_filename(f.filename)
            unique = f"prod_{seller_id}_{uuid.uuid4().hex}_{fname}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
            try:
                f.save(path)
                saved_images.append(unique)
            except Exception:
                app.logger.exception("Failed saving uploaded image")
                return jsonify({'success': False, 'msg': 'Failed saving image'}), 500
    
    saved_image = ",".join(saved_images) if saved_images else None

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    # use two cursors: lightweight cursor for schema introspection, dict cursor for row operations
    dict_cursor = conn.cursor(dictionary=True)
    meta_cursor = conn.cursor()  # regular cursor returns tuples (r[0] works)
    allowed_categories, _ = _fetch_seller_allowed_categories(conn, seller_id, fallback_to_all=False)
    if not allowed_categories:
        return jsonify({'success': False, 'msg': 'No categories are assigned to your store yet. Please contact support.'}), 400
    allowed_lookup = {
        int(cat.get('id')): cat
        for cat in allowed_categories
        if cat.get('id') is not None
    }
    allowed_slug_map = {
        (cat.get('slug') or '').lower(): int(cat.get('id'))
        for cat in allowed_categories
        if cat.get('slug') and cat.get('id') is not None
    }
    allowed_name_map = {
        (cat.get('name') or '').strip().lower(): int(cat.get('id'))
        for cat in allowed_categories
        if cat.get('name') and cat.get('id') is not None
    }
    try:
        # inspect products table to determine column names
        meta_cursor.execute("SHOW COLUMNS FROM products")
        cols = [r[0].lower() for r in meta_cursor.fetchall()]

        # determine seller column name in products table
        if 'sellerid' in cols:
            seller_col = 'sellerID'
        elif 'seller_id' in cols:
            seller_col = 'seller_id'
        elif 'seller' in cols:
            seller_col = 'seller'
        else:
            return jsonify({'success': False, 'msg': 'products table missing seller column'}), 500

        # determine image column name
        image_col = None
        for candidate in ('image_path', 'image', 'main_image', 'imageurl'):
            if candidate in cols:
                image_col = candidate
                break

        # resolve category selection into either slug/text or numerical id within the seller's permissions
        resolved_category_id = None
        resolved_category_slug = None
        resolved_category_name = None
        if category:
            category_value = str(category).strip()
            maybe_id = None
            try:
                maybe_id = int(category_value)
            except (TypeError, ValueError):
                maybe_id = None

            if maybe_id and maybe_id in allowed_lookup:
                resolved_category_id = maybe_id
            else:
                normalized = category_value.lower()
                resolved_category_id = allowed_slug_map.get(normalized) or allowed_name_map.get(normalized)

            if not resolved_category_id:
                return jsonify({'success': False, 'msg': 'Selected category is not available for your store.'}), 400

            resolved_category = allowed_lookup.get(resolved_category_id)
            resolved_category_name = (resolved_category or {}).get('name')
            resolved_category_slug = (resolved_category or {}).get('slug')
            if not resolved_category_slug:
                resolved_category_slug = _slugify_category_name(resolved_category_name or category_value)

        if not productID and not resolved_category_id:
            return jsonify({'success': False, 'msg': 'Please choose a valid category for this product.'}), 400

        # create new product when no productID provided
        if not productID:
            if not name or not price:
                return jsonify({'success': False, 'msg': 'Missing required fields (name, price)'}), 400

            insert_cols = []
            insert_vals = []

            if 'name' in cols:
                insert_cols.append('name'); insert_vals.append(name)
            elif 'title' in cols:
                insert_cols.append('title'); insert_vals.append(name)

            if 'price' in cols:
                insert_cols.append('price'); insert_vals.append(price)
            if 'description' in cols:
                insert_cols.append('description'); insert_vals.append(description)
            if 'stock' in cols:
                insert_cols.append('stock'); insert_vals.append(stock or 0)
            # Persist category selection: prefer numeric categoryID if column exists; else slug; else name/text.
            if resolved_category_id is not None and ('categoryid' in cols or 'category_id' in cols):
                id_col = 'categoryID' if 'categoryid' in cols else 'category_id'
                insert_cols.append(id_col); insert_vals.append(resolved_category_id)
            if resolved_category_slug and 'category_slug' in cols:
                insert_cols.append('category_slug'); insert_vals.append(resolved_category_slug.lower())
            elif 'category' in cols and resolved_category_name:
                insert_cols.append('category'); insert_vals.append(resolved_category_name)

            if image_col and saved_image:
                insert_cols.append(image_col); insert_vals.append(saved_image)

            insert_cols.append(seller_col); insert_vals.append(seller_id)

            placeholders = ','.join(['%s'] * len(insert_vals))
            sql = f"INSERT INTO products ({','.join(insert_cols)}) VALUES ({placeholders})"
            dict_cursor.execute(sql, tuple(insert_vals))
            conn.commit()

            # reliably obtain the inserted id
            new_id = None
            try:
                new_id = getattr(dict_cursor, 'lastrowid', None)
            except Exception:
                new_id = None
            if not new_id:
                try:
                    meta_cursor.execute("SELECT LAST_INSERT_ID()")
                    row = meta_cursor.fetchone()
                    if row:
                        new_id = row[0]
                except Exception:
                    new_id = None

            # Featured request handling (optional checkbox)
            try:
                req = (data.get('request_featured') or data.get('featured') or '').lower()
                requested = req in ('1', 'true', 'on', 'yes')
            except Exception:
                requested = False
            if requested and new_id:
                try:
                    # upsert as requested
                    _cur = conn.cursor()
                    try:
                        _cur.execute("INSERT INTO featured_products (productID, status) VALUES (%s, 'requested') ON DUPLICATE KEY UPDATE status = VALUES(status)", (new_id,))
                        conn.commit()
                    finally:
                        try: _cur.close()
                        except Exception: pass
                except Exception:
                    app.logger.exception("Failed to save featured request")

            # update session seller_products list after successful insert
            try:
                dict_cursor.execute(f"SELECT * FROM products WHERE `{seller_col}` = %s ORDER BY productID DESC", (seller_id,))
                rows = dict_cursor.fetchall() or []
                sess_products = []
                for r in rows:
                    simple = {}
                    for k, v in r.items():
                        try:
                            # convert datetimes to isoformat for safe session serialization
                            if hasattr(v, 'isoformat'):
                                simple[k] = v.isoformat()
                            else:
                                simple[k] = v
                        except Exception:
                            simple[k] = str(v)
                    sess_products.append(simple)
                session['seller_products'] = sess_products
            except Exception:
                app.logger.exception("Failed to refresh seller_products in session")

            return jsonify({'success': True, 'msg': 'Product created', 'productID': new_id}), 201

        # update existing product - verify ownership using dict_cursor
        dict_cursor.execute("SELECT * FROM products WHERE productID = %s LIMIT 1", (productID,))
        owner_row = dict_cursor.fetchone()
        if not owner_row:
            return jsonify({'success': False, 'msg': 'Product not found'}), 404

        owner = None
        for k in ('sellerID', 'seller_id', 'sellerid', 'seller'):
            if k in owner_row and owner_row.get(k) is not None:
                owner = owner_row.get(k)
                break

        if owner is None:
            return jsonify({'success': False, 'msg': 'Cannot determine product owner'}), 500

        if str(owner) != str(seller_id):
            return jsonify({'success': False, 'msg': 'Not authorized to modify this product'}), 403

        updates = []
        params = []
        if name:
            if 'name' in cols:
                updates.append('name=%s'); params.append(name)
            elif 'title' in cols:
                updates.append('title=%s'); params.append(name)
        if price is not None and 'price' in cols:
            updates.append('price=%s'); params.append(price)
        if description and 'description' in cols:
            updates.append('description=%s'); params.append(description)
        if stock is not None and 'stock' in cols:
            updates.append('stock=%s'); params.append(stock)
        # Update category if provided
        if category:
            if resolved_category_id is None:
                return jsonify({'success': False, 'msg': 'Selected category is not available for your store.'}), 400
            if 'categoryid' in cols or 'category_id' in cols:
                id_col = 'categoryID' if 'categoryid' in cols else 'category_id'
                updates.append(f'{id_col}=%s'); params.append(resolved_category_id)
            if 'category_slug' in cols and resolved_category_slug:
                updates.append('category_slug=%s'); params.append(resolved_category_slug.lower())
            elif 'category' in cols and resolved_category_name:
                updates.append('category=%s'); params.append(resolved_category_name)
        if image_col and saved_image:
            updates.append(f"{image_col}=%s"); params.append(saved_image)

        if not updates:
            return jsonify({'success': False, 'msg': 'No fields to update'}), 400

        sql = f"UPDATE products SET {', '.join(updates)} WHERE productID = %s"
        params.append(productID)
        dict_cursor.execute(sql, tuple(params))
        conn.commit()

        # If stock was replenished (from 0/None to >0), notify affected users
        try:
            prev_stock = 0
            try:
                prev_stock = int(owner_row.get('stock') or 0)
            except Exception:
                prev_stock = 0
            new_stock = 0
            try:
                new_stock = int(stock or 0)
            except Exception:
                new_stock = 0
            if prev_stock <= 0 and new_stock > 0:
                try:
                    dict_cursor.execute("SELECT name FROM products WHERE productID = %s", (productID,))
                    prow = dict_cursor.fetchone() or {}
                    prod_name = prow.get('name') or 'Product'
                except Exception:
                    prod_name = 'Product'
                try:
                    # Find cancellations awaiting restock
                    dict_cursor.execute("SELECT DISTINCT userID, pendingID FROM order_cancellation_log WHERE productID = %s AND status = 'cancelled'", (productID,))
                    rows = dict_cursor.fetchall() or []
                except Exception:
                    rows = []
                for r in rows:
                    try:
                        uid = r.get('userID'); pid = r.get('pendingID')
                        # Notify user
                        try:
                            dict_cursor.execute("INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('user', %s, %s, %s)", (uid, 'Item back in stock', f"{prod_name} is available again. You can review cancelled order #{pid}.") )
                            emit_notification_event('user', uid, 'Item back in stock', f"{prod_name} is available again. You can review cancelled order #{pid}.")
                        except Exception:
                            pass
                        # Email user (best-effort)
                        try:
                            dict_cursor.execute("SELECT email FROM users WHERE userID = %s", (uid,))
                            row_u = dict_cursor.fetchone() or {}
                            uemail = row_u.get('email')
                            if uemail:
                                try:
                                    msg = Message('Item back in stock', recipients=[uemail])
                                    msg.body = f"Good news! {prod_name} is back in stock. You can review and reinstate your cancelled order #{pid} in Your Orders."
                                    mail.send(msg)
                                except Exception:
                                    app.logger.debug('Email send failed for back-in-stock')
                        except Exception:
                            pass
                        # Update log status
                        try:
                            dict_cursor.execute("UPDATE order_cancellation_log SET status = 'restocked_notified' WHERE pendingID = %s AND userID = %s AND productID = %s", (pid, uid, productID))
                        except Exception:
                            pass
                        # Audit trail
                        try:
                            dict_cursor.execute("INSERT INTO order_cancellation_audit (pendingID, userID, action, note, created_at) VALUES (%s, %s, 'notified_restock', %s, NOW())", (pid, uid, prod_name))
                        except Exception:
                            pass
                    except Exception:
                        pass
                try: conn.commit()
                except Exception: pass
        except Exception:
            app.logger.debug('restock notification flow failed')

        # refresh session seller_products after update
        try:
            dict_cursor.execute(f"SELECT * FROM products WHERE `{seller_col}` = %s ORDER BY productID DESC", (seller_id,))
            rows = dict_cursor.fetchall() or []
            sess_products = []
            for r in rows:
                simple = {}
                for k, v in r.items():
                    try:
                        if hasattr(v, 'isoformat'):
                            simple[k] = v.isoformat()
                        else:
                            simple[k] = v
                    except Exception:
                        simple[k] = str(v)
                sess_products.append(simple)
            session['seller_products'] = sess_products
        except Exception:
            app.logger.exception("Failed to refresh seller_products in session (update)")

        return jsonify({'success': True, 'msg': 'Product updated', 'image': saved_image}), 200

    except Exception as e:
        conn.rollback()
        app.logger.exception("Error in seller_manage_product")
        return jsonify({'success': False, 'msg': f'Error: {str(e)}'}), 500
    finally:
        try: dict_cursor.close()
        except Exception: pass
        try: meta_cursor.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Delegate to the existing featured-requests dashboard view so logic is shared
    return admin_featured_requests()


@app.route('/admin/featured/requests')
def admin_featured_requests():
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db_connection()
    reqs = []
    metrics = {
        'total_products': 0,
        'total_revenue': 0.0,
        'total_orders': 0,
        'total_sellers': 0,
    }
    approved_sellers = []
    pending_sellers = []
    all_sellers = []
    approved_riders = []
    pending_riders = []
    all_riders = []
    featured_approved = []
    categories = []
    user_reports = []
    seller_reports = []
    rider_reports = []
    if not conn:
        return render_template(
            'admin_dashboard.html',
            featured_requests=reqs,
            metrics=metrics,
            approved_sellers=approved_sellers,
            pending_sellers=pending_sellers,
            approved_riders=approved_riders,
            pending_riders=pending_riders,
            featured_approved=featured_approved,
            categories=categories,
            user_reports=user_reports,
            seller_reports=seller_reports,
            rider_reports=rider_reports,
            all_sellers=all_sellers,
            all_riders=all_riders,
        )
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT f.productID, f.status, p.name, p.price
            FROM featured_products f
            JOIN products p ON p.productID = f.productID
            WHERE f.status = 'requested'
            ORDER BY f.created_at DESC
            """
        )
        reqs = cur.fetchall() or []

        # Compute simple aggregate metrics for the dashboard (best-effort, ignore failures)
        try:
            # total products
            cur.execute("SELECT COUNT(*) AS c FROM products")
            row = cur.fetchone() or {}
            metrics['total_products'] = int(row.get('c') or 0)
        except Exception:
            metrics['total_products'] = 0

        try:
            # total revenue (sum of admin_share from financial_transactions)
            cur.execute("SELECT COALESCE(SUM(admin_share),0) AS total FROM financial_transactions")
            row = cur.fetchone() or {}
            metrics['total_revenue'] = float(row.get('total') or 0.0)
        except Exception:
            metrics['total_revenue'] = 0.0

        try:
            # total delivered orders
            cur.execute("SELECT COUNT(*) AS c FROM seller_orders WHERE LOWER(IFNULL(status,'')) = 'delivered'")
            row = cur.fetchone() or {}
            metrics['total_orders'] = int(row.get('c') or 0)
        except Exception:
            metrics['total_orders'] = 0

        try:
            # total riders
            cur.execute("SELECT COUNT(*) AS c FROM riders")
            row = cur.fetchone() or {}
            metrics['total_riders'] = int(row.get('c') or 0)
        except Exception:
            metrics['total_riders'] = 0

        try:
            # total sellers
            cur.execute("SELECT COUNT(*) AS c FROM sellers")
            row = cur.fetchone() or {}
            metrics['total_sellers'] = int(row.get('c') or 0)
        except Exception:
            metrics['total_sellers'] = 0

        # Approved and pending sellers (for sidebar Stores/Approve Store)
        try:
            # Ensure seller_category column exists to avoid query errors if migration hasn't run
            cur.execute("SHOW COLUMNS FROM sellers LIKE 'seller_category'")
            has_seller_category = bool(cur.fetchone())
            if not has_seller_category:
                try:
                    cur.execute("ALTER TABLE sellers ADD COLUMN seller_category VARCHAR(255) NULL")
                    conn.commit()
                    has_seller_category = True
                except Exception:
                    pass

            # Build query dynamically — if seller_category doesn't exist, use NULL placeholder
            extra_col = "seller_category" if has_seller_category else "NULL AS seller_category"
            cur.execute(
                f"""
                SELECT sellerID, sellername, selleremail, storename, status, businesspermit_path, {extra_col},
                       contactnumber, storedesc, region, province, city, barangay, created_at
                FROM sellers
                ORDER BY sellerID DESC
                """
            )
            rows = cur.fetchall() or []
            for row in rows:
                st = (row.get('status') or '').lower()
                rec = {
                    'sellerID': row.get('sellerID'),
                    'storename': row.get('storename'),
                    'sellername': row.get('sellername'),
                    'selleremail': row.get('selleremail'),
                    'status': row.get('status'),
                    'businesspermit_path': row.get('businesspermit_path'),
                    'seller_category': row.get('seller_category'),
                    'contactnumber': row.get('contactnumber'),
                    'storedesc': row.get('storedesc'),
                    'region': row.get('region'),
                    'province': row.get('province'),
                    'city': row.get('city'),
                    'barangay': row.get('barangay'),
                    'created_at': row.get('created_at'),
                }
                all_sellers.append(rec)
                if st == 'approved':
                    approved_sellers.append(rec)
                elif st == 'pending':
                    pending_sellers.append(rec)
        except Exception as e:
            app.logger.error(f"[admin_dashboard] Failed to query sellers: {e}")
            approved_sellers = []
            pending_sellers = []
            all_sellers = []

        # Approved and pending riders (for Riders / Approve Riders tabs)
        try:
            # Ensure vehicle_type column exists to avoid query errors if migration hasn't run
            cur.execute("SHOW COLUMNS FROM riders LIKE 'vehicle_type'")
            if not cur.fetchone():
                try:
                    cur.execute("ALTER TABLE riders ADD COLUMN vehicle_type VARCHAR(100) NULL")
                    conn.commit()
                except Exception:
                    pass

            cur.execute(
                """
                SELECT riderID, ridername, rideremail, phone, status, is_available, image_path, vehicle_type
                FROM riders
                ORDER BY riderID DESC
                """
            )
            rows = cur.fetchall() or []
            for row in rows:
                st = (row.get('status') or '').lower()
                rec = {
                    'riderID': row.get('riderID'),
                    'ridername': row.get('ridername'),
                    'rideremail': row.get('rideremail'),
                    'phone': row.get('phone'),
                    'status': row.get('status'),
                    'is_available': row.get('is_available'),
                    'image_path': row.get('image_path'),
                    'driverlicense_path': row.get('image_path'),
                    'vehicle_type': row.get('vehicle_type'),
                }
                all_riders.append(rec)
                if st in ('active', 'approved'):
                    approved_riders.append(rec)
                elif st == 'pending':
                    pending_riders.append(rec)
        except Exception:
            approved_riders = []
            pending_riders = []

        # Currently approved featured products (for "Currently Featured" table)
        try:
            cur.execute(
                """
                SELECT f.productID, p.name, p.price
                FROM featured_products f
                JOIN products p ON p.productID = f.productID
                WHERE f.status = 'approved'
                ORDER BY f.created_at DESC
                """
            )
            featured_approved = cur.fetchall() or []
        except Exception:
            featured_approved = []

        # Categories list for Manage Categories tab
        try:
            cur.execute("SELECT * FROM categories ORDER BY name ASC")
            categories = cur.fetchall() or []
        except Exception:
            categories = []

        # Reports grouped by role (user/seller/rider) for unified Reports tab
        try:
            cur.execute(
                """
                SELECT r.*, p.name AS product_name, p.image_path AS product_image_path,
                       s.storename AS seller_name, s.status AS seller_status
                FROM reports r
                LEFT JOIN products p ON r.reported_product_id = p.productID
                LEFT JOIN sellers s ON r.reported_shop_id = s.sellerID
                ORDER BY r.created_at DESC
                """
            )
            rrows = cur.fetchall() or []
            for r in rrows:
                role = (r.get('role') or '').lower()
                if role == 'user':
                    user_reports.append(r)
                elif role == 'seller':
                    seller_reports.append(r)
                elif role == 'rider':
                    rider_reports.append(r)
                else:
                    user_reports.append(r)
        except Exception:
            user_reports = []
            seller_reports = []
            rider_reports = []
    except Exception:
        reqs = []
    finally:
        try: cur.close(); conn.close()
        except Exception: pass
    return render_template(
        'admin_dashboard.html',
        featured_requests=reqs,
        metrics=metrics,
        approved_sellers=approved_sellers,
        pending_sellers=pending_sellers,
        approved_riders=approved_riders,
        pending_riders=pending_riders,
        featured_approved=featured_approved,
        categories=categories,
        user_reports=user_reports,
        seller_reports=seller_reports,
        rider_reports=rider_reports,
        all_sellers=all_sellers,
        all_riders=all_riders,
    )


@app.route('/api/admin/stats_chart')
def api_admin_stats_chart():
    """Return JSON time series for orders (daily) and admin commissions for Chart.js.

    Returns last 30 days aggregated sums.
    """
    if not admin_required():
        return jsonify({'error': 'unauthorized'}), 403

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    try:
        cur = conn.cursor()
        # Build last 30 days date series using MySQL DATE functions
        cur.execute("""
            SELECT
                DATE(created_at) AS day,
                COALESCE(SUM(total_amount),0) AS sales_total
            FROM seller_orders
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
        """)
        sales_rows = cur.fetchall() or []

        cur.execute("""
            SELECT
                DATE(created_at) AS day,
                COALESCE(SUM(admin_share),0) AS admin_commissions
            FROM financial_transactions
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
        """)
        comm_rows = cur.fetchall() or []

        cur.execute("""
            SELECT
                DATE(created_at) AS day,
                COUNT(*) AS order_count
            FROM seller_orders
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
        """)
        orders_rows = cur.fetchall() or []

        delivered_rows = []
        try:
            cur.execute("""
                SELECT
                    DATE(h.timestamp) AS day,
                    COUNT(*) AS delivered_count
                FROM order_status_history h
                WHERE h.status = 'delivered'
                  AND h.timestamp >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY DATE(h.timestamp)
                ORDER BY DATE(h.timestamp)
            """)
            delivered_rows = cur.fetchall() or []
        except mysql.connector.Error as err:
            if err.errno == getattr(errorcode, 'ER_NO_SUCH_TABLE', 1146):
                cur.execute("""
                    SELECT
                        DATE(updated_at) AS day,
                        COUNT(*) AS delivered_count
                    FROM seller_orders
                    WHERE status = 'delivered' AND updated_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    GROUP BY DATE(updated_at)
                    ORDER BY DATE(updated_at)
                """)
                delivered_rows = cur.fetchall() or []
            else:
                raise

        # Normalize into dicts by day
        sales_map = { str(r[0]): float(r[1] or 0.0) for r in sales_rows }
        comm_map = { str(r[0]): float(r[1] or 0.0) for r in comm_rows }
        orders_map = { str(r[0]): int(r[1] or 0) for r in orders_rows }
        delivered_map = { str(r[0]): int(r[1] or 0) for r in delivered_rows }

        # Build list of last 30 days
        cur.execute("SELECT CURDATE()")
        today = cur.fetchone()[0]
        labels = []
        sales = []
        comms = []
        orders = []
        delivered = []
        for i in range(29, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            labels.append(d)
            sales.append(sales_map.get(d, 0.0))
            comms.append(comm_map.get(d, 0.0))
            orders.append(orders_map.get(d, 0))
            delivered.append(delivered_map.get(d, 0))

        return jsonify({
            'labels': labels, 
            'sales': sales, 
            'commissions': comms,
            'orders': orders,
            'delivered': delivered
        }), 200
    except Exception as e:
        app.logger.exception('Failed to build admin stats chart')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass


@app.route('/api/admin/notifications')
def api_admin_notifications():
    if not admin_required():
        return jsonify({'success': False, 'msg': 'unauthorized'}), 403

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    meta_cur = None
    report_cur = None
    count_cur = None
    try:
        cur = conn.cursor(dictionary=True)
        meta_cur = conn.cursor()
        meta_cur.execute('SHOW COLUMNS FROM notifications')
        column_rows = meta_cur.fetchall() or []
        columns = [row[0] for row in column_rows]
        id_col = 'notificationID' if 'notificationID' in columns else 'id'
        has_is_read = 'is_read' in columns
        select_cols = f"{id_col} AS id, title, body, created_at"
        if has_is_read:
            select_cols += ', is_read'
        else:
            select_cols += ', 0 AS is_read'

        cur.execute(
            f"""
            SELECT {select_cols}
            FROM notifications
            WHERE recipient_type = 'admin'
            ORDER BY created_at DESC
            LIMIT 50
            """
        )
        rows = cur.fetchall() or []
        notifications = []
        unread_ids = []
        for row in rows:
            created_at = row.get('created_at')
            if hasattr(created_at, 'isoformat'):
                created_str = created_at.isoformat()
            elif created_at is not None:
                created_str = str(created_at)
            else:
                created_str = None
            title = row.get('title') or ''
            note_type = 'vat' if 'vat' in title.lower() or 'platform fee' in title.lower() else 'general'
            is_read = row.get('is_read')
            is_read_flag = 1 if str(is_read).lower() in ('1', 'true', 'yes') or is_read == 1 else 0
            notif_id = row.get('id')
            notifications.append({
                'id': notif_id,
                'title': title,
                'body': row.get('body'),
                'created_at': created_str,
                'is_read': is_read_flag,
                'type': note_type,
            })
            if not is_read_flag and notif_id is not None:
                unread_ids.append(str(notif_id))
        unread_count = len(unread_ids)

        report_cur = conn.cursor(dictionary=True)
        report_cur.execute(
            """
            SELECT id, reporter_name, complaint_type, status, created_at,
                   reported_shop_id, reported_product_id, offense_level
            FROM reports
            WHERE status IS NULL OR LOWER(status) <> 'resolved'
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
        report_rows = report_cur.fetchall() or []
        report_alerts = []
        for row in report_rows:
            created_at = row.get('created_at')
            if hasattr(created_at, 'isoformat'):
                created_str = created_at.isoformat()
            elif created_at is not None:
                created_str = str(created_at)
            else:
                created_str = None
            report_alerts.append({
                'id': row.get('id'),
                'reporter_name': row.get('reporter_name'),
                'complaint_type': row.get('complaint_type'),
                'status': row.get('status'),
                'reported_shop_id': row.get('reported_shop_id'),
                'reported_product_id': row.get('reported_product_id'),
                'offense_level': row.get('offense_level'),
                'created_at': created_str,
            })

        count_cur = conn.cursor()
        count_cur.execute(
            """
            SELECT COUNT(*) FROM reports
            WHERE status IS NULL OR LOWER(status) <> 'resolved'
            """
        )
        count_row = count_cur.fetchone()
        unresolved_count = int(count_row[0]) if count_row else 0

        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count,
            'unread_ids': unread_ids,
            'report_alerts': report_alerts,
            'unresolved_reports_count': unresolved_count,
            'fetched_at': datetime.utcnow().isoformat(),
        }), 200
    except Exception:
        try:
            app.logger.exception('Failed to fetch admin notifications')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'failed'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if meta_cur:
                meta_cur.close()
        except Exception:
            pass
        try:
            if report_cur:
                report_cur.close()
        except Exception:
            pass
        try:
            if count_cur:
                count_cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/admin/notifications/mark_read', methods=['POST'])
def api_admin_notifications_mark_read():
    if not admin_required():
        return jsonify({'success': False, 'msg': 'unauthorized'}), 403

    data = request.get_json(silent=True) or request.form or {}
    mark_all = str(data.get('mark') or '').strip().lower() == 'all'

    ids_value = data.get('ids') if data.get('ids') is not None else data.get('id')
    ids_list = []
    if isinstance(ids_value, (list, tuple, set)):
        ids_list = list(ids_value)
    elif ids_value not in (None, ''):
        ids_list = [ids_value]

    cleaned_ids = []
    if not mark_all:
        for raw in ids_list:
            try:
                if raw is None or raw == '':
                    continue
                cleaned_ids.append(int(raw))
            except Exception:
                continue
        if not cleaned_ids:
            return jsonify({'success': False, 'msg': 'no_ids'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    meta_cur = None
    try:
        cur = conn.cursor()
        meta_cur = conn.cursor()
        meta_cur.execute('SHOW COLUMNS FROM notifications')
        columns = [row[0] for row in meta_cur.fetchall() or []]
        id_col = 'notificationID' if 'notificationID' in columns else 'id'
        if 'is_read' not in columns:
            return jsonify({'success': False, 'msg': 'unsupported'}), 400

        if mark_all:
            cur.execute("UPDATE notifications SET is_read = 1 WHERE recipient_type = 'admin' AND is_read = 0")
        else:
            placeholders = ','.join(['%s'] * len(cleaned_ids))
            cur.execute(
                f"UPDATE notifications SET is_read = 1 WHERE recipient_type = 'admin' AND {id_col} IN ({placeholders})",
                tuple(cleaned_ids)
            )
        updated = cur.rowcount
        conn.commit()
        return jsonify({'success': True, 'updated': int(updated)}), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            app.logger.exception('Failed to mark admin notifications read')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'failed'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if meta_cur:
                meta_cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/admin/featured/<int:product_id>/update', methods=['POST'])
def admin_update_featured(product_id):
    if not admin_required():
        return jsonify({'success': False, 'msg': 'unauthorized'}), 403
    data = request.get_json(silent=True) or request.form
    action = (data.get('action') or '').lower()
    if action not in ('approve', 'reject', 'remove'):
        return jsonify({'success': False, 'msg': 'invalid action'}), 400
    status = 'approved' if action == 'approve' else ('rejected' if action == 'reject' else 'removed')
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db connection error'}), 500
    try:
        cur = conn.cursor()
        if action == 'remove':
            cur.execute("DELETE FROM featured_products WHERE productID = %s", (product_id,))
        else:
            cur.execute("INSERT INTO featured_products (productID, status) VALUES (%s, %s) ON DUPLICATE KEY UPDATE status = VALUES(status)", (product_id, status))
        conn.commit()
        return jsonify({'success': True, 'status': status}), 200
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'success': False, 'msg': f'error: {str(e)}'}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass


@app.route('/admin/sellers/<int:seller_id>/update', methods=['POST'])
def admin_update_seller(seller_id):
    if not admin_required():
        return jsonify({'success': False, 'msg': 'unauthorized'}), 403

    data = request.get_json(silent=True) or request.form or {}
    action = (data.get('action') or '').lower()
    if action not in ('approve', 'reject'):
        return jsonify({'success': False, 'msg': 'invalid action'}), 400

    new_status = 'approved' if action == 'approve' else 'rejected'

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db connection error'}), 500

    cur = None
    meta_cur = None
    try:
        meta_cur = conn.cursor()
        meta_cur.execute("SHOW COLUMNS FROM sellers")
        columns = [row[0] for row in meta_cur.fetchall()]
        id_columns = [c for c in columns if c and c.lower() in ('sellerid', 'seller_id', 'id')]
        if not id_columns:
            id_columns = ['sellerID']

        where_clause = " OR ".join([f"`{col}` = %s" for col in id_columns])
        params = tuple([seller_id] * len(id_columns))

        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT * FROM sellers WHERE {where_clause} LIMIT 1", params)
        seller = cur.fetchone()
        if not seller:
            return jsonify({'success': False, 'msg': 'seller not found'}), 404

        pk_col = None
        pk_val = None
        for col in id_columns:
            if col in seller and seller.get(col) is not None:
                pk_col = col
                pk_val = seller.get(col)
                break
        if pk_col is None:
            pk_col = id_columns[0]
            pk_val = seller.get(pk_col, seller_id)

        cur.execute(f"UPDATE sellers SET status = %s WHERE `{pk_col}` = %s LIMIT 1", (new_status, pk_val))
        conn.commit()

        try:
            seller_email = seller.get('selleremail')
            seller_name = seller.get('sellername') or seller.get('storename')
            if action == 'approve':
                send_approve_email(seller_email, seller_name)
            else:
                send_reject_email(seller_email, seller_name)
        except Exception:
            app.logger.exception('Failed to send seller approval email')

        return jsonify({'success': True, 'status': new_status}), 200
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        app.logger.exception('Failed to update seller status')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if meta_cur:
                meta_cur.close()
        except Exception:
            pass
        try: conn.close()
        except Exception: pass


@app.route('/admin/riders/<int:rider_id>/update', methods=['POST'])
def admin_update_rider(rider_id):
    if not admin_required():
        return jsonify({'success': False, 'msg': 'unauthorized'}), 403

    data = request.get_json(silent=True) or request.form or {}
    action = (data.get('action') or '').lower()
    if action not in ('approve', 'reject'):
        return jsonify({'success': False, 'msg': 'invalid action'}), 400

    new_status = 'active' if action == 'approve' else 'rejected'

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db connection error'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        # check rider exists
        cur.execute('SELECT riderID, ridername, rideremail FROM riders WHERE riderID = %s LIMIT 1', (rider_id,))
        rider = cur.fetchone()
        if not rider:
            return jsonify({'success': False, 'msg': 'rider not found'}), 404

        # perform update (also set is_available=1 for approved riders)
        if action == 'approve':
            try:
                cur.execute("UPDATE riders SET status = %s, is_available = 1 WHERE riderID = %s", (new_status, rider_id))
            except Exception:
                # fall back to simple update if column missing
                cur.execute("UPDATE riders SET status = %s WHERE riderID = %s", (new_status, rider_id))
        else:
            cur.execute("UPDATE riders SET status = %s WHERE riderID = %s", (new_status, rider_id))

        conn.commit()

        # Send notification email (best-effort)
        try:
            if action == 'approve':
                send_rider_approve_email(rider.get('rideremail'), rider.get('ridername'))
            else:
                send_rider_reject_email(rider.get('rideremail'), rider.get('ridername'))
        except Exception:
            app.logger.exception('Failed to send rider notification email')

        return jsonify({'success': True, 'status': new_status}), 200
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        app.logger.exception('Failed to update rider status')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass


@app.route('/api/rider/stats/daily-deliveries')
@rider_required
def api_rider_stats_daily_deliveries():
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT DATE(h.timestamp) AS day, COUNT(*) AS deliveries
            FROM order_status_history h
            INNER JOIN seller_orders so ON so.sellerOrderID = h.sellerOrderID
            WHERE so.riderID = %s AND h.status = 'delivered'
            GROUP BY DATE(h.timestamp)
            ORDER BY day ASC
            LIMIT 30
        """, (rider_id,))
        rows = cur.fetchall() or []
        labels = []
        data = []
        for row in rows:
            day = row.get('day')
            labels.append(str(day))
            data.append(int(row.get('deliveries') or 0))
        return jsonify({'success': True, 'labels': labels, 'data': data}), 200
    except Exception:
        app.logger.exception('Failed to load rider daily deliveries')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/rider/stats/acceptance-overview')
@rider_required
def api_rider_stats_acceptance_overview():
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    _ensure_rider_response_audit_table()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT DATE(created_at) AS day,
                   SUM(CASE WHEN action = 'accept' THEN 1 ELSE 0 END) AS accepted,
                   SUM(CASE WHEN action = 'decline' THEN 1 ELSE 0 END) AS declined
            FROM rider_response_audit
            WHERE riderID = %s
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            LIMIT 30
        """, (rider_id,))
        rows = cur.fetchall() or []
        labels = []
        accepted = []
        declined = []
        for row in rows:
            day = row.get('day')
            labels.append(str(day))
            accepted.append(int(row.get('accepted') or 0))
            declined.append(int(row.get('declined') or 0))
        return jsonify({'success': True, 'labels': labels, 'accepted': accepted, 'declined': declined}), 200
    except Exception:
        app.logger.exception('Failed to load rider acceptance overview')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/rider/stats/recent-deliveries')
@rider_required
def api_rider_stats_recent_deliveries():
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    try:
        limit = int(request.args.get('limit', 10))
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT sellerOrderID, userID, order_number, status, total_amount,
                   shipping_address, contact_number, payment_method, tracking_number,
                   current_location, estimated_delivery, created_at, updated_at
            FROM seller_orders
            WHERE riderID = %s
            ORDER BY COALESCE(updated_at, created_at) DESC
            LIMIT %s
        """, (rider_id, limit))
        rows = cur.fetchall() or []
        data = []
        for row in rows:
            data.append({
                'orderID': row.get('sellerOrderID'),
                'userID': row.get('userID'),
                'order_number': row.get('order_number'),
                'status': row.get('status'),
                'total_amount': float(row.get('total_amount') or 0.0),
                'shipping_address': row.get('shipping_address'),
                'contact_number': row.get('contact_number'),
                'payment_method': row.get('payment_method'),
                'tracking_number': row.get('tracking_number'),
                'current_location': row.get('current_location'),
                'estimated_delivery': row.get('estimated_delivery'),
                'created_at': row.get('created_at').isoformat() if row.get('created_at') else None,
                'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None,
            })
        return jsonify({'success': True, 'data': data}), 200
    except Exception:
        app.logger.exception('Failed to load rider recent deliveries')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _compute_rider_summary_stats(rider_id):
    """Return (total_deliveries, pending_orders, completed_today, total_earnings,
    earnings_week, earnings_month) for a rider.

    - total_deliveries: count of delivered orders (status = 'delivered') for this rider.
    - pending_orders: count of orders with status in ('pending', 'on_the_way').
    - completed_today: delivered orders where delivery date is today.
    - total_earnings: total_deliveries * 30 (₱30 per successful delivery).
    - earnings_week: earnings from delivered orders in the current week (last 7 days including today).
    - earnings_month: earnings from delivered orders in the current calendar month.
    """
    total_deliveries = 0
    pending_orders = 0
    completed_today = 0
    total_earnings = 0.0
    earnings_week = 0.0
    earnings_month = 0.0

    conn = get_db_connection()
    if not conn:
        return (
            total_deliveries,
            pending_orders,
            completed_today,
            total_earnings,
            earnings_week,
            earnings_month,
        )

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT 
                SUM(CASE WHEN LOWER(IFNULL(status, '')) = 'delivered' THEN 1 ELSE 0 END) AS delivered,
                SUM(CASE WHEN LOWER(IFNULL(status, '')) IN ('pending','on_the_way') THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN LOWER(IFNULL(status, '')) = 'delivered' 
                          AND DATE(COALESCE(updated_at, created_at)) = CURDATE() THEN 1 ELSE 0 END) AS completed_today,
                
                SUM(CASE WHEN revenue_released = 1 THEN 1 ELSE 0 END) AS paid_deliveries,
                
                SUM(CASE WHEN revenue_released = 1 
                          AND DATE(COALESCE(revenue_released_at, updated_at)) BETWEEN (CURDATE() - INTERVAL 6 DAY) AND CURDATE() THEN 1 ELSE 0 END) AS paid_week,
                
                SUM(CASE WHEN revenue_released = 1
                          AND YEAR(DATE(COALESCE(revenue_released_at, updated_at))) = YEAR(CURDATE())
                          AND MONTH(DATE(COALESCE(revenue_released_at, updated_at))) = MONTH(CURDATE()) THEN 1 ELSE 0 END) AS paid_month
            FROM seller_orders
            WHERE riderID = %s
            """,
            (rider_id,)
        )
        row = cur.fetchone() or {}
        total_deliveries = int(row.get('delivered') or 0)
        pending_orders = int(row.get('pending') or 0)
        completed_today = int(row.get('completed_today') or 0)
        
        paid_deliveries = int(row.get('paid_deliveries') or 0)
        paid_week = int(row.get('paid_week') or 0)
        paid_month = int(row.get('paid_month') or 0)

        # Calculate earnings from financial_transactions (hybrid)
        cur.execute("""
            SELECT 
                SUM(
                    CASE 
                        WHEN ft.rider_commission IS NOT NULL THEN ft.rider_commission 
                        ELSE 30.00 
                    END
                ) as total,
                SUM(
                    CASE 
                        WHEN DATE(COALESCE(so.revenue_released_at, so.updated_at)) BETWEEN (CURDATE() - INTERVAL 6 DAY) AND CURDATE() THEN
                            CASE WHEN ft.rider_commission IS NOT NULL THEN ft.rider_commission ELSE 30.00 END
                        ELSE 0 
                    END
                ) as week,
                SUM(
                    CASE 
                        WHEN YEAR(DATE(COALESCE(so.revenue_released_at, so.updated_at))) = YEAR(CURDATE()) AND MONTH(DATE(COALESCE(so.revenue_released_at, so.updated_at))) = MONTH(CURDATE()) THEN
                            CASE WHEN ft.rider_commission IS NOT NULL THEN ft.rider_commission ELSE 30.00 END
                        ELSE 0 
                    END
                ) as month
            FROM seller_orders so
            LEFT JOIN financial_transactions ft ON so.sellerOrderID = ft.order_id
            WHERE so.riderID = %s AND so.revenue_released = 1
        """, (rider_id,))
        
        fin_row = cur.fetchone()
        total_earnings = float(fin_row.get('total') or 0.0)
        earnings_week = float(fin_row.get('week') or 0.0)
        earnings_month = float(fin_row.get('month') or 0.0)
    except Exception:
        try:
            app.logger.exception('Failed to compute rider summary stats')
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    return (
        total_deliveries,
        pending_orders,
        completed_today,
        total_earnings,
        earnings_week,
        earnings_month,
    )


@app.route('/api/rider/stats/summary')
@rider_required
def api_rider_stats_summary():
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    try:
        (
            total_deliveries,
            pending_orders,
            completed_today,
            total_earnings,
            earnings_week,
            earnings_month,
        ) = _compute_rider_summary_stats(rider_id)
        return jsonify({
            'success': True,
            'total_deliveries': total_deliveries,
            'pending_orders': pending_orders,
            'completed_today': completed_today,
            'total_earnings': total_earnings,
            'earnings_week': earnings_week,
            'earnings_month': earnings_month,
        }), 200
    except Exception:
        try:
            app.logger.exception('Failed to load rider summary stats')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'server_error'}), 500


@app.route('/seller/remove/product/<int:productID>', methods=['DELETE'])
def seller_remove_product(productID):
    # determine seller id from JWT cookie or session safely
    seller_id = None
    try:
        cookie_name = app.config.get('JWT_ACCESS_COOKIE_NAME', 'access_token')
        token = request.cookies.get(cookie_name)
        if token:
            decoded = decode_token(token)
            # token may store identity under 'sub' or 'identity'
            identity = None
            if isinstance(decoded, dict):
                identity = decoded.get('sub') or decoded.get('identity') or decoded.get('sub', None)
            if identity and isinstance(identity, dict) and identity.get('role') == 'seller':
                seller_id = identity.get('sellerID') or identity.get('sellerId') or identity.get('id')
    except Exception:
        app.logger.debug("Token decode failed or no token present; falling back to session", exc_info=True)
        seller_id = None

    if not seller_id:
        seller = session.get('seller')
        if seller:
            seller_id = seller.get('id') or seller.get('sellerID')

    if not seller_id:
        return jsonify({'success': False, 'msg': 'Seller not authenticated'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    meta_cursor = conn.cursor()  # will be used for schema inspection
    try:
        # verify ownership (tolerant column names)
        cursor.execute("SELECT * FROM products WHERE productID = %s LIMIT 1", (productID,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'msg': 'Product not found'}), 404

        owner = None
        for k in ('sellerID', 'seller_id', 'sellerid', 'seller'):
            if k in row and row.get(k) is not None:
                owner = row.get(k)
                break

        if owner is None:
            return jsonify({'success': False, 'msg': 'Cannot determine owner'}), 500

        if str(owner) != str(seller_id):
            return jsonify({'success': False, 'msg': 'Not authorized to remove this product'}), 403

        # Inspect actual product columns and build a delete that only references existing columns.
        meta_cursor.execute("SHOW COLUMNS FROM products")
        fields = [r[0] for r in meta_cursor.fetchall()]  # original column names
        seller_cols = [c for c in fields if c.lower() in ('sellerid', 'seller_id', 'seller')]

        if not seller_cols:
            # no seller column to validate against (schema mismatch)
            return jsonify({'success': False, 'msg': 'products table missing seller column'}), 500

        # Build DELETE with only existing seller columns to avoid Unknown column errors
        cond_parts = []
        params = [productID]
        for col in seller_cols:
            cond_parts.append(f"IFNULL(`{col}`, %s) = %s")
            params.extend([seller_id, seller_id])

        where_clause = " OR ".join(cond_parts)
        sql = f"DELETE FROM products WHERE productID = %s AND ({where_clause})"

        cursor.execute(sql, tuple(params))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({'success': False, 'msg': 'Product not found or not owned by seller'}), 404

        conn.commit()

        # update session seller_products: remove deleted product if present
        try:
            sess_products = session.get('seller_products', [])
            if isinstance(sess_products, list):
                sess_products = [p for p in sess_products if str(p.get('productID') or p.get('productId') or p.get('id') or '') != str(productID)]
                session['seller_products'] = sess_products
        except Exception:
            app.logger.exception("Failed to update session seller_products after delete")

        return jsonify({'success': True, 'msg': 'Product removed'}), 200
    except Exception as e:
        conn.rollback()
        app.logger.exception("Error in seller_remove_product")
        return jsonify({'success': False, 'msg': f'Error: {str(e)}'}), 500
    finally:
        try: cursor.close()
        except Exception: pass
        try: meta_cursor.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

@app.route('/report', methods=['POST'])
def submit_product_report():
    user = session.get('user') or {}
    reporter_id = user.get('userID') or user.get('id')
    reporter_name = user.get('username') or user.get('name') or user.get('email')
    if not reporter_id:
        return jsonify({'success': False, 'msg': 'login_required'}), 401

    product_id = request.form.get('reported_product_id') or request.form.get('product_id')
    complaint_type = (request.form.get('complaint_type') or '').strip()
    description = (request.form.get('description') or '').strip()
    additional_message = (request.form.get('message') or '').strip()
    if not product_id or not complaint_type or not description:
        return jsonify({'success': False, 'msg': 'missing_fields'}), 400

    try:
        product_id_int = int(product_id)
    except Exception:
        return jsonify({'success': False, 'msg': 'invalid_product'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    cur = None
    evidence_path = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT sellerID FROM products WHERE productID = %s LIMIT 1",
            (product_id_int,)
        )
        prow = cur.fetchone()
        if not prow:
            return jsonify({'success': False, 'msg': 'product_not_found'}), 404

        seller_id = prow.get('sellerID') or prow.get('seller_id') or prow.get('sellerid')

        evidence_file = request.files.get('evidence')
        if evidence_file and evidence_file.filename:
            filename = secure_filename(evidence_file.filename)
            if filename:
                name, ext = os.path.splitext(filename)
                allowed_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
                if ext.lower() not in allowed_exts:
                    return jsonify({'success': False, 'msg': 'invalid_file_type'}), 400
                target_dir = os.path.join(UPLOAD_DIR, 'reports')
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except Exception:
                    pass
                unique_name = f"report_{uuid.uuid4().hex}{ext.lower()}"
                storage_path = os.path.join(target_dir, unique_name)
                evidence_file.save(storage_path)
                evidence_path = os.path.join('reports', unique_name)

        cur.execute(
            """
            INSERT INTO reports (reporter_id, reporter_name, reported_product_id, reported_shop_id, role, description, message, image_path, status, complaint_type, offense_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'open', %s, 0)
            """,
            (
                reporter_id,
                reporter_name,
                product_id_int,
                seller_id,
                'User',
                description,
                additional_message,
                evidence_path,
                complaint_type,
            )
        )
        conn.commit()
        report_id = cur.lastrowid

        notice_body = f'Product #{product_id_int} has a new report submitted by {reporter_name or "a user"}.'
        try:
            cur.execute(
                "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('admin', %s, %s, %s)",
                (0, 'New product report', notice_body)
            )
            conn.commit()
            emit_notification_event('admin', 0, 'New product report', notice_body)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        return jsonify({'success': True, 'report_id': report_id}), 200
    except Exception as e:
        print(f"ERROR submitting report: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        if evidence_path:
            try:
                os.remove(os.path.join(UPLOAD_DIR, evidence_path))
            except Exception:
                pass
        app.logger.exception('Failed to submit product report')
        return jsonify({'success': False, 'msg': 'server_error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    if not conn:
        abort(500)

    cur = None
    meta = None
    seller_meta = None
    seller_cur = None
    try:
        # Inspect product columns and build safe WHERE
        meta = conn.cursor()
        meta.execute("SHOW COLUMNS FROM products")
        cols = [r[0] for r in meta.fetchall()]

        id_candidates = [c for c in cols if c.lower() in ('productid', 'product_id', 'id')]
        if not id_candidates:
            abort(404)

        where_parts = []
        params = []
        for col in id_candidates:
            where_parts.append(f"`{col}` = %s")
            params.append(product_id)

        sql = "SELECT * FROM products WHERE " + " OR ".join(where_parts) + " LIMIT 1"

        cur = conn.cursor(dictionary=True)
        cur.execute(sql, tuple(params))
        row = cur.fetchone()
        if not row:
            abort(404)

        # tolerant pick helper (case-insensitive)
        row_lower = { (k.lower() if k is not None else k): v for k, v in row.items() }
        def pick(r, candidates, default=None):
            for k in candidates:
                if k in r and r.get(k) is not None:
                    return r.get(k)
            for k in candidates:
                lk = k.lower()
                if lk in row_lower and row_lower.get(lk) is not None:
                    return row_lower.get(lk)
            return default

        raw_image_ref = pick(row, ['image_path', 'image', 'main_image', 'imageurl'])
        normalized_image = _normalize_upload_reference(raw_image_ref)

        product = {
            'id': pick(row, ['productID', 'productId', 'product_id', 'id']),
            'name': pick(row, ['name', 'title']),
            'price': pick(row, ['price']),
            'description': pick(row, ['description', 'desc']),
            'stock': pick(row, ['stock', 'quantity', 'qty']),
            'image': normalized_image,
            'store_name': pick(row, ['storename', 'store_name', 'seller_name', 'vendor']),
            'store_logo': pick(row, ['store_logo', 'logo', 'seller_image', 'store_image', 'image_path']),
            'seller_id': pick(row, ['sellerID', 'seller_id', 'store_id', 'sellerId', 'sellerid']),
            'raw': row
        }

        gallery_candidates = [
            row.get('image_gallery'),
            row.get('image_list'),
            row.get('images'),
            row.get('image_urls'),
            row.get('image_path'),
            row.get('image'),
            row.get('main_image'),
            row.get('primary_image'),
            row.get('imageurl'),
            row.get('image0'),
            row.get('image1'),
            row.get('image2'),
            row.get('image3'),
            row.get('image_0'),
            row.get('image_1'),
            row.get('image_2'),
            row.get('image_3'),
        ]

        gallery_images = []
        seen_refs = set()

        def _append_gallery_sources(raw_value):
            if not raw_value:
                return
            if isinstance(raw_value, (list, tuple, set)):
                for entry in raw_value:
                    _append_gallery_sources(entry)
                return
            text = str(raw_value).strip()
            if not text:
                return
            text = text.replace('\\', '/').strip()
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = None
            if isinstance(parsed, (list, tuple, set)):
                for entry in parsed:
                    _append_gallery_sources(entry)
                return
            if isinstance(parsed, dict):
                for key in ('url', 'path', 'image', 'image_path', 'main_image', 'image0', 'image1', 'image2', 'image3'):
                    if key in parsed:
                        _append_gallery_sources(parsed.get(key))
                return
            if isinstance(parsed, str):
                text = parsed.strip()

            for sep in (',', '|', ';', '\n'):
                if sep in text:
                    for part in text.split(sep):
                        _append_gallery_sources(part)
                    return

            normalized = _normalize_upload_reference(text)
            if not normalized or normalized in seen_refs:
                return
            seen_refs.add(normalized)
            gallery_images.append(normalized)

        for candidate in gallery_candidates:
            _append_gallery_sources(candidate)

        if not gallery_images and normalized_image:
            gallery_images.append(normalized_image)

        product['gallery_images'] = gallery_images

        if gallery_images:
            product['image'] = gallery_images[0]

        # Build image_url if possible
        product['image_url'] = _build_upload_url(product['image'])

        seller_id = product.get('seller_id')
        seller_row = None
        seller_meta = None
        seller_cur = None
        if seller_id:
            try:
                seller_meta = conn.cursor()
                seller_meta.execute("SHOW COLUMNS FROM sellers")
                scols = [r[0] for r in seller_meta.fetchall()]
                sid_candidates = [c for c in scols if c.lower() in ('sellerid', 'seller_id', 'id')]
                if sid_candidates:
                    s_where = []
                    s_params = []
                    for c in sid_candidates:
                        s_where.append(f"`{c}` = %s")
                        s_params.append(seller_id)
                    ssql = "SELECT * FROM sellers WHERE " + " OR ".join(s_where) + " LIMIT 1"
                    seller_cur = conn.cursor(dictionary=True)
                    seller_cur.execute(ssql, tuple(s_params))
                    seller_row = seller_cur.fetchone()
            except Exception:
                app.logger.exception("Failed to load seller info for product detail")
            finally:
                try:
                    if seller_cur:
                        seller_cur.close()
                except Exception:
                    pass
                try:
                    if seller_meta:
                        seller_meta.close()
                except Exception:
                    pass

        if seller_row:
            srow_lower = { (k.lower() if k is not None else k): v for k, v in seller_row.items() }

            def spick(r, candidates, default=None):
                for k in candidates:
                    if k in r and r.get(k) is not None:
                        return r.get(k)
                for k in candidates:
                    lk = k.lower()
                    if lk in srow_lower and srow_lower.get(lk) is not None:
                        return srow_lower.get(lk)
                return default

            if not product.get('store_name'):
                product['store_name'] = spick(seller_row, ['storename', 'store_name', 'sellername', 'seller_name', 'vendor'])
            if not product.get('store_logo'):
                product['store_logo'] = spick(seller_row, ['storelogo_path', 'store_logo', 'logo', 'seller_image', 'store_image'])
            if not product.get('seller_id'):
                product['seller_id'] = spick(seller_row, ['sellerID', 'seller_id', 'id'])
            if product.get('store_logo') and not str(product.get('store_logo')).startswith('http'):
                try:
                    product['store_logo'] = url_for('uploaded_file', filename=product['store_logo'])
                except Exception:
                    product['store_logo'] = None

            seller_status_value = str((seller_row.get('status') or '')).lower()
            try:
                seller_offense_level = int(seller_row.get('offense_level') or 0)
            except Exception:
                seller_offense_level = 0
            seller_is_frozen = bool(seller_row.get('is_frozen')) or seller_status_value == 'frozen' or seller_offense_level >= 3
            if seller_is_frozen:
                abort(404)

        # ensure store_logo_url exists if we already had store_logo
        if product.get('store_logo') and not product.get('store_logo_url'):
            if isinstance(product.get('store_logo'), str) and product.get('store_logo').startswith('http'):
                product['store_logo_url'] = product.get('store_logo')
            else:
                try:
                    product['store_logo_url'] = url_for('uploaded_file', filename=product.get('store_logo')) if product.get('store_logo') else None
                except Exception:
                    product['store_logo_url'] = None

        # Fetch 5 random products for "You May Also Like"
        random_products = []
        rand_cur = None
        try:
            # Use product_id from the function argument which is already an int
            rand_sql = "SELECT * FROM products WHERE productID != %s ORDER BY RAND() LIMIT 5"
            rand_cur = conn.cursor(dictionary=True)
            rand_cur.execute(rand_sql, (product_id,))
            rand_rows = rand_cur.fetchall()

            for r in rand_rows:
                image_ref = _normalize_upload_reference([
                    r.get('image_path'),
                    r.get('image'),
                    r.get('main_image'),
                    r.get('imageurl'),
                    r.get('image0'),
                    r.get('image1'),
                    r.get('images'),
                    r.get('image_gallery'),
                ])
                p = {
                    'id': r.get('productID'),
                    'name': r.get('name'),
                    'price': r.get('price'),
                    'stock': r.get('stock'),
                    'image': image_ref,
                    'sellerID': r.get('sellerID') or r.get('seller_id'),
                }
                p['image_url'] = _build_upload_url(image_ref)
                random_products.append(p)
        except Exception as e:
            app.logger.error(f"Error fetching random products: {e}")
        finally:
            try:
                if rand_cur:
                    rand_cur.close()
            except Exception:
                pass
        random_products = _filter_out_frozen_products(conn, random_products)

        return render_template('product_detail.html', product=product, random_products=random_products)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if meta: meta.close()
        except Exception:
            pass
        try:
            if conn and getattr(conn, "is_connected", lambda: True)():
                conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

# Removed duplicate checkout route - using process_checkout instead

@app.route('/seller/<int:seller_id>')
def seller_page(seller_id):
    conn = get_db_connection()
    if not conn:
        abort(500)
    cur = None
    meta = None
    try:
        meta = conn.cursor()
        meta.execute("SHOW COLUMNS FROM sellers")
        cols = [r[0] for r in meta.fetchall()]
        id_candidates = [c for c in cols if c.lower() in ('sellerid', 'seller_id', 'id')]
        if not id_candidates:
            abort(404)
        where_parts = []
        params = []
        for col in id_candidates:
            where_parts.append(f"`{col}` = %s")
            params.append(seller_id)
        sql = "SELECT * FROM sellers WHERE " + " OR ".join(where_parts) + " LIMIT 1"
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, tuple(params))
        srow = cur.fetchone()
        if not srow:
            abort(404)

        # tolerant lookup (case-insensitive)
        srow_lower = { (k.lower() if k is not None else k): v for k, v in srow.items() }
        def pick(r, candidates, default=None):
            for k in candidates:
                if k in r and r.get(k) is not None:
                    return r.get(k)
            for k in candidates:
                lk = k.lower()
                if lk in srow_lower and srow_lower.get(lk) is not None:
                    return srow_lower.get(lk)
            return default

        seller = {
            'id': pick(srow, ['sellerID', 'sellerId', 'seller_id', 'id']),
            'name': pick(srow, ['storename', 'sellername', 'store_name', 'seller_name']) or 'Store',
            'email': pick(srow, ['selleremail', 'email']),
            'description': pick(srow, ['storedesc', 'store_description', 'description']),
            'logo': pick(srow, ['storelogo_path', 'store_logo', 'logo', 'seller_image', 'store_image']),
            'raw': srow
        }

        # build logo url if file path
        if seller.get('logo'):
            try:
                if isinstance(seller['logo'], str) and seller['logo'].startswith('http'):
                    seller['logo_url'] = seller['logo']
                else:
                    seller['logo_url'] = url_for('uploaded_file', filename=seller['logo'])
            except Exception:
                seller['logo_url'] = None
        else:
            seller['logo_url'] = None

        # try to include created_at if available in raw row
        try:
            raw = srow or {}
            seller['created_at'] = raw.get('created_at') or raw.get('createdAt') or raw.get('joined') or raw.get('created')
        except Exception:
            seller['created_at'] = None

        # Fetch seller products to render on the storefront
        products = []
        try:
            prod_cur = None
            rows = []
            try:
                prod_cur = conn.cursor(dictionary=True)
                _ensure_restriction_tables(conn)
                prod_cur.execute(
                    "SELECT * FROM products WHERE sellerID = %s ORDER BY productID DESC",
                    (seller.get('id') or seller_id,)
                )
                rows = prod_cur.fetchall() or []
            finally:
                try:
                    if prod_cur:
                        prod_cur.close()
                except Exception:
                    pass

            normalized = []
            for r in rows:
                if not isinstance(r, dict):
                    normalized.append(r)
                    continue
                img = r.get('image_path') or r.get('image') or r.get('main_image') or r.get('imageurl')
                
                # Populate images list
                images_list = []
                if img and isinstance(img, str):
                     for p in img.split(','):
                         if p.strip():
                             images_list.append(url_for('uploaded_file', filename=p.strip()))

                # Handle comma-separated images
                if img and isinstance(img, str) and ',' in img:
                    img = img.split(',')[0]

                img_url = url_for('uploaded_file', filename=img) if img else None
                rr = dict(r)
                rr['image_url'] = img_url
                rr['images'] = images_list
                try:
                    rr['stock'] = int(rr.get('stock') or 0)
                except Exception:
                    rr['stock'] = 0
                normalized.append(rr)
            products = normalized
        except Exception:
            try:
                app.logger.debug('Failed to fetch seller products')
            except Exception:
                pass

        return render_template('seller_page.html', seller=seller, products=products)
    finally:
        try: 
            if cur: cur.close()
        except Exception: pass
        try:
            if meta: meta.close()
        except Exception: pass
        try:
            if conn and getattr(conn, "is_connected", lambda: True)():
                conn.close()
        except Exception:
            try: conn.close()
            except Exception: pass

# Alias route so old templates using `store_page` still work
@app.route('/store/<int:store_id>')
def store_page(store_id):
    # redirect/forward to the canonical seller_page handler
    return seller_page(store_id)

# --- Minimal placeholder for websocket probe endpoints ---
@app.route('/ws', methods=['GET'])
def ws_placeholder():
    # This endpoint is a lightweight probe used by development tooling.
    # The app uses Flask-SocketIO for realtime communication; raw WebSocket
    # upgrades to this path are not supported. Return a clear JSON 200 so
    # client tooling can detect the server and get an explicit message.
    try:
        return jsonify({'success': True, 'websocket': False, 'message': 'Probe endpoint; use Socket.IO for realtime connections.'}), 200
    except Exception:
        # Fallback plain-text response in case jsonify fails for any reason.
        return 'Probe endpoint (Socket.IO available)', 200

@app.route('/ws/health', methods=['GET'])
def ws_health():
    # Report whether Socket.IO server object seems configured so healthchecks
    # can decide if realtime features are enabled.
    try:
        sio_available = ('socketio' in globals() and socketio is not None)
    except Exception:
        sio_available = False
    return jsonify({'status': 'ok', 'websocket': bool(sio_available)}), 200

@app.route('/admin/categories/create', methods=['POST'])
def admin_create_category():
    # Simple admin guard - adjust to your real admin check if needed
    if not admin_required():
        return jsonify({'success': False, 'msg': 'unauthorized'}), 403

    # read name from JSON or form
    name = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
    else:
        name = (request.form.get('name') or '').strip()

    if not name:
        return jsonify({'success': False, 'msg': 'Category name required'}), 400

    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or None

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'DB connection failed'}), 500

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        # detect slug column
        try:
            cur.execute("SHOW COLUMNS FROM categories LIKE 'slug'")
            has_slug = bool(cur.fetchone())
        except Exception:
            has_slug = False

        # check existing
        if has_slug:
            cur.execute("SELECT categoryID AS id, slug, name FROM categories WHERE slug = %s OR name = %s LIMIT 1", (slug, name))
        else:
            cur.execute("SELECT categoryID AS id, name FROM categories WHERE name = %s LIMIT 1", (name,))
        existing = cur.fetchone()
        if existing:
            return jsonify({'success': True, 'msg': 'Category exists', 'category': {'id': existing.get('id'), 'name': existing.get('name'), 'slug': existing.get('slug') if has_slug else None}}), 200

        # insert
        if has_slug:
            try:
                cur.execute("INSERT INTO categories (`name`, `slug`) VALUES (%s, %s)", (name, slug))
            except Exception:
                cur.execute("INSERT INTO categories (`name`) VALUES (%s)", (name,))
        else:
            cur.execute("INSERT INTO categories (`name`) VALUES (%s)", (name,))
        conn.commit()

        new_id = getattr(cur, 'lastrowid', None)
        if not new_id:
            if has_slug:
                cur.execute("SELECT categoryID AS id FROM categories WHERE slug = %s OR name = %s LIMIT 1", (slug, name))
            else:
                cur.execute("SELECT categoryID AS id FROM categories WHERE name = %s ORDER BY categoryID DESC LIMIT 1", (name,))
            row = cur.fetchone()
            new_id = int(row.get('id')) if row and row.get('id') else None

        return jsonify({'success': True, 'msg': 'Category created', 'category': {'id': new_id, 'name': name, 'slug': slug if has_slug else None}}), 201

    except Exception:
        app.logger.exception("Failed to create category")
        return jsonify({'success': False, 'msg': 'Server error'}), 500
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

@app.route('/admin/categories/delete', methods=['POST'])
def admin_delete_category():
    """Delete a category by id or slug/name. Admin only.

    Accepts JSON or form data with one of: id, slug, name.
    Returns JSON {success, msg}.
    """
    # Simple admin guard - adjust to your real admin check if needed
    if not admin_required():
        return jsonify({'success': False, 'msg': 'unauthorized'}), 403

    data = request.get_json(silent=True) or request.form
    cat_id = (data.get('id') or data.get('categoryID') or '').strip() if hasattr(data.get('id') or data.get('categoryID'), 'strip') else (data.get('id') or data.get('categoryID'))
    slug = (data.get('slug') or '').strip() if hasattr(data.get('slug'), 'strip') else data.get('slug')
    name = (data.get('name') or '').strip() if hasattr(data.get('name'), 'strip') else data.get('name')

    if not cat_id and not slug and not name:
        return jsonify({'success': False, 'msg': 'Missing category identifier'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'DB connection failed'}), 500

    cur = None
    meta = None
    try:
        cur = conn.cursor()
        meta = conn.cursor()

        # Introspect categories columns
        meta.execute("SHOW COLUMNS FROM categories")
        cols = [r[0] for r in meta.fetchall()]

        # Determine id column
        id_candidates = [c for c in cols if c.lower() in ('categoryid', 'category_id', 'id')]
        slug_exists = any(c.lower() == 'slug' for c in cols)
        name_exists = any(c.lower() == 'name' for c in cols)

        where_parts = []
        params = []

        # Prefer deleting by id if provided
        if cat_id:
            try:
                cat_id_int = int(str(cat_id))
            except Exception:
                cat_id_int = None
            if cat_id_int is not None and id_candidates:
                where_parts.append("(" + " OR ".join([f"`{c}` = %s" for c in id_candidates]) + ")")
                for _ in id_candidates:
                    params.append(cat_id_int)

        # Fallback to slug
        if not where_parts and slug and slug_exists:
            where_parts.append("`slug` = %s")
            params.append(slug)

        # Fallback to name
        if not where_parts and name and name_exists:
            where_parts.append("`name` = %s")
            params.append(name)

        if not where_parts:
            return jsonify({'success': False, 'msg': 'Cannot resolve category identifier'}), 400

        # Build and execute DELETE
        sql = "DELETE FROM categories WHERE " + " OR ".join(where_parts) + " LIMIT 1"
        cur.execute(sql, tuple(params))
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({'success': False, 'msg': 'Category not found'}), 404

        conn.commit()
        return jsonify({'success': True, 'msg': 'Category deleted'}), 200
    except mysql.connector.Error as db_err:
        try:
            conn.rollback()
        except Exception:
            pass
        # Common case: foreign key constraint
        return jsonify({'success': False, 'msg': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception("Failed to delete category")
        return jsonify({'success': False, 'msg': 'Server error'}), 500
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if meta: meta.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

@app.route('/rider_dashboard', methods=['GET'])
def rider_dashboard():
    rider = session.get('rider')
    if not rider:
        return redirect(url_for('rider_login'))
    # Server-side: fetch delivered orders for "My Orders" so they appear in the sidebar
    my_orders = []
    conn = get_db_connection()
    rider_id = _get_rider_id_from_session()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            
            # Refresh rider status to ensure overlay doesn't show for active riders with stale sessions
            try:
                cur.execute("SELECT status FROM riders WHERE riderID = %s", (rider_id,))
                s_row = cur.fetchone()
                if s_row:
                    db_status = s_row.get('status')
                    if rider.get('status') != db_status:
                        rider['status'] = db_status
                        session['rider'] = rider
                        session.modified = True
            except Exception:
                pass

            try:
                cur.execute(
                    """
                    SELECT so.sellerOrderID, so.order_number, so.total_amount, so.status, so.updated_at,
                           s.storename AS shop_name, u.username AS user_name
                    FROM seller_orders so
                    LEFT JOIN sellers s ON so.sellerID = s.sellerID
                    LEFT JOIN users u ON so.userID = u.userID
                    WHERE so.riderID = %s AND LOWER(IFNULL(so.status, '')) = 'delivered'
                    ORDER BY so.updated_at DESC
                    """,
                    (rider_id,)
                )
                rows = cur.fetchall() or []
                for r in rows:
                    my_orders.append({
                        'sellerOrderID': r.get('sellerOrderID'),
                        'order_number': r.get('order_number'),
                        'shop_name': r.get('shop_name') or 'Shop',
                        'user_name': r.get('user_name') or 'Customer',
                        'total_amount': float(r.get('total_amount') or 0.0),
                        'status': r.get('status') or 'delivered',
                        'updated_at': r.get('updated_at')
                    })
            except Exception:
                app.logger.exception('Failed to fetch rider delivered orders for My Orders')
            try:
                cur.close()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # Compute summary stats for initial render (JS will also refresh these via API)
    total_deliveries = 0
    pending_orders = 0
    completed_today = 0
    total_earnings = 0.0
    earnings_week = 0.0
    earnings_month = 0.0
    try:
        if rider_id:
            (
                total_deliveries,
                pending_orders,
                completed_today,
                total_earnings,
                earnings_week,
                earnings_month,
            ) = _compute_rider_summary_stats(rider_id)
    except Exception:
        pass

    return render_template(
        'rider_dashboard.html',
        rider=rider,
        my_orders=my_orders,
        total_deliveries=total_deliveries,
        total_earnings=total_earnings,
        pending_orders=pending_orders,
        completed_today=completed_today,
        earnings_week=earnings_week,
        earnings_month=earnings_month,
    )

# Rider Profile page (view + edit)
@app.route('/rider/profile', methods=['GET', 'POST'])
def rider_profile():
    rider = session.get('rider') or {}
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return redirect(url_for('rider_login'))
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if request.method == 'POST':
            rider_name = (request.form.get('ridername') or request.form.get('rider_name') or '').strip()
            phone = (request.form.get('phone') or '').strip()
            email = (request.form.get('rideremail') or '').strip()
            vehicle_type = (request.form.get('vehicle_type') or '').strip()

            new_name = rider_name or rider.get('ridername') or rider.get('name')
            new_phone = phone or rider.get('phone') or ''
            new_email = email or rider.get('rideremail') or rider.get('email') or ''
            new_vehicle_type = vehicle_type or rider.get('vehicle_type') or ''

            upload_root = app.config.get('UPLOAD_FOLDER', UPLOAD_DIR)
            image_file = request.files.get('image_path') or request.files.get('avatar')
            saved_image_path = None
            saved_image_abs = None
            previous_image_path = rider.get('profile_path')
            image_invalid = False

            if image_file and image_file.filename:
                if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXT):
                    flash('Profile picture must be an image (png/jpg/jpeg/gif/webp).', 'danger')
                    image_invalid = True
                else:
                    filename = secure_filename(image_file.filename)
                    unique_name = f"rider_{rider_id}_{uuid.uuid4().hex}_{filename}"
                    try:
                        os.makedirs(upload_root, exist_ok=True)
                    except Exception:
                        pass
                    saved_image_abs = os.path.join(upload_root, unique_name)
                    image_file.save(saved_image_abs)
                    saved_image_path = unique_name

            if not image_invalid:
                try:
                    params = [new_name, new_phone, new_email, new_vehicle_type]
                    sql = """
                        UPDATE riders
                        SET ridername = %s, phone = %s, rideremail = %s, vehicle_type = %s
                    """
                    if saved_image_path:
                        sql += ", profile_path = %s"
                        params.append(saved_image_path)
                    sql += " WHERE riderID = %s"
                    params.append(rider_id)
                    cur.execute(sql, tuple(params))
                    conn.commit()

                    session_image = saved_image_path or previous_image_path
                    normalized = _normalize_session_rider(
                        rider_id=rider_id,
                        ridername=new_name,
                        rideremail=new_email,
                        profile_path=session_image,
                    ) or {}
                    normalized['phone'] = new_phone
                    normalized['vehicle_type'] = new_vehicle_type
                    session['rider'] = normalized

                    if saved_image_path and previous_image_path and previous_image_path != saved_image_path:
                        if not str(previous_image_path).lower().startswith(('http://', 'https://')):
                            old_path = os.path.join(upload_root, previous_image_path)
                            if os.path.exists(old_path):
                                try:
                                    os.remove(old_path)
                                except Exception:
                                    app.logger.debug('Failed to remove old rider image', exc_info=True)
                    flash('Profile updated', 'success')
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    if saved_image_abs and os.path.exists(saved_image_abs):
                        try:
                            os.remove(saved_image_abs)
                        except Exception:
                            pass
                    flash('Failed to update profile', 'danger')
            else:
                if saved_image_abs and os.path.exists(saved_image_abs):
                    try:
                        os.remove(saved_image_abs)
                    except Exception:
                        pass
        cur.execute("SELECT riderID, ridername, rideremail, phone, vehicle_type, profile_path FROM riders WHERE riderID = %s LIMIT 1", (rider_id,))
        row = cur.fetchone() or {}
        profile_path = row.get('profile_path') or rider.get('profile_path') or rider.get('avatar') or ''
        rider_payload = {
            'id': row.get('riderID') or rider_id,
            'riderID': row.get('riderID') or rider_id,
            'name': row.get('ridername') or rider.get('ridername') or 'Rider',
            'ridername': row.get('ridername') or rider.get('ridername') or '',
            'email': row.get('rideremail') or rider.get('rideremail') or '',
            'rideremail': row.get('rideremail') or rider.get('rideremail') or '',
            'phone': row.get('phone') or rider.get('phone') or '',
            'vehicle_type': row.get('vehicle_type') or rider.get('vehicle_type') or '',
            'profile_path': profile_path,
            'image_path': profile_path,
        }
        return render_template('rider_profile.html', rider=rider_payload)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if conn: conn.close()
        except Exception:
            pass

@app.route('/rider/settings/password', methods=['POST'])
def rider_settings_password():
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return redirect(url_for('rider_login'))
    current_password = request.form.get('current_password') or ''
    new_password = request.form.get('new_password') or ''
    confirm_password = request.form.get('confirm_password') or ''
    if not new_password or new_password != confirm_password:
        flash('Passwords do not match', 'danger')
        return redirect(url_for('rider_profile'))
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT riderpass FROM riders WHERE riderID = %s", (rider_id,))
        row = cur.fetchone() or {}
        hashed = row.get('riderpass') or ''
        if not hashed or not check_password_hash(hashed, current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('rider_profile'))
        new_hash = generate_password_hash(new_password)
        cur.execute("UPDATE riders SET riderpass = %s WHERE riderID = %s", (new_hash, rider_id))
        conn.commit()
        flash('Password updated', 'success')
        return redirect(url_for('rider_profile'))
    except Exception:
        try: conn.rollback()
        except Exception: pass
        flash('Failed to update password', 'danger')
        return redirect(url_for('rider_profile'))
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        try:
            if conn: conn.close()
        except Exception:
            pass

@app.route('/rider_login', methods=['GET', 'POST'])
def rider_login():
    if request.method == 'GET':
        return render_template('rider_login.html')

    rideremail = (request.form.get('rideremail') or '').strip()
    riderpass = request.form.get('riderpass') or ''

    if not rideremail or not riderpass:
        flash('Please provide both email and password', 'danger')
        return render_template('rider_login.html')

    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return render_template('rider_login.html')

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM riders WHERE rideremail = %s LIMIT 1", (rideremail,))
        row = cursor.fetchone()
        if not row:
            flash('Invalid credentials', 'danger')
            return render_template('rider_login.html')

        hashed = row.get('riderpass') or row.get('password') or row.get('passwd') or ''
        if not hashed or not check_password_hash(hashed, riderpass):
            flash('Invalid credentials', 'danger')
            return render_template('rider_login.html')

        status = (row.get('status') or 'pending')
        rider_id = row.get('riderID') or row.get('id')
        rider_name = row.get('ridername') or 'Rider'
        fallback_avatar = None
        for key in ('avatar', 'profile_pic', 'profile_picture'):
            val = row.get(key)
            if val:
                fallback_avatar = val
                break
        rider_profile_path = row.get('profile_path') or fallback_avatar
        # Only allow active riders to login
        if status != 'active':
            if status == 'pending':
                flash('Your account is pending admin approval.', 'warning')
            elif status == 'rejected':
                flash('Your account was rejected by the admin.', 'danger')
            elif status == 'inactive':
                flash('Your rider account is inactive.', 'danger')
            else:
                flash('Your account is not active. Contact admin.', 'danger')
            return render_template('rider_login.html')

        # JWT for rider with role
        access_token = create_access_token(
            identity=str(rider_id),
            additional_claims={'rider': {'riderID': rider_id, 'ridername': rider_name, 'rideremail': rideremail}, 'role': 'rider'},
        )
        _normalize_session_rider(
            rider_id=rider_id,
            ridername=rider_name,
            rideremail=rideremail,
            status=status,
            profile_path=rider_profile_path,
            image_path=row.get('image_path'),
        )
        try:
            session['rider_id'] = rider_id
            session['rider_token'] = access_token
            rider_session_token = secrets.token_urlsafe(32)
            session['rider_session'] = rider_session_token
            _set_active_role('rider')
        except Exception:
            pass
        resp = make_response(redirect(url_for('rider_dashboard')))
        _set_role_cookie(resp, 'rider', rider_session_token)
        
        # Set JWT cookie for API access
        set_access_cookies(resp, access_token)
        return resp
    except Exception:
        app.logger.exception('Rider login error')
        flash('Server error, try again later', 'danger')
        return render_template('rider_login.html')
    finally:
        try:
            cursor.close(); conn.close()
        except Exception:
            pass

@app.route('/rider_signup', methods=['GET', 'POST'])
def rider_signup():
    if request.method == 'POST':
        # Read form fields
        ridername = (request.form.get('ridername') or '').strip()
        rideremail = (request.form.get('rideremail') or '').strip()
        riderpass = (request.form.get('riderpass') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        confirmriderpass = (request.form.get('confirmriderpass') or '').strip()
        
        # Location fields
        region = (request.form.get('region') or '').strip()
        province = (request.form.get('province') or '').strip()
        city = (request.form.get('city') or '').strip()
        barangay = (request.form.get('barangay') or '').strip()
        
        # Vehicle info
        vehicle_type = (request.form.get('vehicle_type') or '').strip()

        # Basic validation
        if not all([ridername, rideremail, riderpass, confirmriderpass, phone]):
            flash('Please fill in all required fields', 'error')
            return render_template('rider_signup.html')

        if riderpass != confirmriderpass:
            flash('Passwords do not match', 'error')
            return render_template('rider_signup.html')

        # Hash the password
        hashed_password = generate_password_hash(riderpass)

        # Handle driver's license image upload
        driverlicense_file = request.files.get('driverlicense')

        # Prepare upload folder
        try:
            os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(parent_dir, 'uploads')), exist_ok=True)
        except Exception:
            app.logger.exception("Failed to ensure upload folder")
            flash('Server configuration error (uploads).', 'error')
            return render_template('rider_signup.html')

        driverlicense_path = None
        if driverlicense_file and driverlicense_file.filename:
            if not allowed_file(driverlicense_file.filename, ALLOWED_IMAGE_EXT):
                flash("Driver's license must be an image (png/jpg/jpeg)", 'error')
                return render_template('rider_signup.html')
            filename = secure_filename(driverlicense_file.filename)
            unique = f"license_{uuid.uuid4().hex}_{filename}"
            driverlicense_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
            driverlicense_path = unique

        # Database connection
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return render_template('rider_signup.html')

        try:
            cursor = conn.cursor()
            # Detect table structure
            cursor.execute("SHOW COLUMNS FROM riders")
            columns = [r[0].lower() for r in cursor.fetchall()]

            # Determine password column name
            if 'riderpass' in columns:
                pw_col = 'riderpass'
            elif 'password' in columns:
                pw_col = 'password'
            elif 'passwd' in columns:
                pw_col = 'passwd'
            else:
                # Add riderpass column on the fly
                cursor.execute("ALTER TABLE riders ADD COLUMN riderpass VARCHAR(255) NULL")
                pw_col = 'riderpass'
            
            # Ensure location columns exist
            for loc_col in ['region', 'province', 'city', 'barangay', 'vehicle_type']:
                if loc_col not in columns:
                    cursor.execute(f"ALTER TABLE riders ADD COLUMN {loc_col} VARCHAR(100) NULL")

            # Prepare data for insertion
            cols = ['ridername', 'rideremail', pw_col, 'image_path', 'phone', 'status', 'region', 'province', 'city', 'barangay', 'vehicle_type']
            values = [ridername, rideremail, hashed_password, driverlicense_path, phone, 'pending', region, province, city, barangay, vehicle_type]

            placeholders = ','.join(['%s'] * len(cols))
            sql = "INSERT INTO riders ({}) VALUES ({})".format(','.join(cols), placeholders)
            cursor.execute(sql, tuple(values))
            conn.commit()

        except Exception as e:
            conn.rollback()
            app.logger.exception("Rider signup DB error")
            flash('Error saving rider data', 'error')
            return render_template('rider_signup.html')

        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        flash('Thanks! Please wait for admin approval before you can use the dashboard.', 'success')
        # Notify rider that the account is pending admin review (approval email will be sent later).
        send_rider_pending_review_email(rideremail, ridername)
        return redirect(url_for('rider_login'))

    # Render the signup page
    return render_template('rider_signup.html')


@app.route('/test-products')
def test_products():
    """Test endpoint to check products in database"""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT productID, name, price, image_path FROM products LIMIT 5")
        products = cursor.fetchall()
        
        result = "<h1>Test Products</h1>"
        for p in products:
            result += f"<p>ID: {p.get('productID')}, Name: {p.get('name')}, Price: {p.get('price')}, Image: {p.get('image_path')}</p>"
            result += f'<a href="/test-add-to-cart/{p.get("productID")}">Add to Cart</a><br><br>'
        
        return result
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()

@app.route('/test-add-to-cart/<int:product_id>')
def test_add_to_cart(product_id):
    """Test adding a product to cart"""
    # Simulate form data
    from flask import request
    request.form = {'quantity': '1'}
    
    # Call the add_to_cart function
    return add_to_cart(product_id)

@app.route('/update_cart_quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    """Update quantity of a product in cart"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    if not user_id:
        flash('Please log in to update cart.', 'warning')
        return redirect(url_for('login'))
    
    # Get new quantity from form
    new_quantity = request.form.get('quantity', type=int)
    
    if not new_quantity or new_quantity < 1:
        flash('Invalid quantity.', 'error')
        return redirect(url_for('cart'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('cart'))
    
    try:
        # Use dictionary cursor so we can read columns by name
        cursor = conn.cursor(dictionary=True)

        # Check if item exists in cart
        cursor.execute("""
            SELECT cartID, quantity FROM cart 
            WHERE userID = %s AND productID = %s AND status = 'active'
        """, (user_id, product_id))

        result = cursor.fetchone()
        if not result:
            flash('Item not found in cart.', 'error')
            return redirect(url_for('cart'))

        # Fetch current product stock and price
        cursor.execute("SELECT productID, price, stock, name FROM products WHERE productID = %s LIMIT 1", (product_id,))
        prod = cursor.fetchone()
        if not prod:
            flash('Product not found.', 'error')
            return redirect(url_for('cart'))

        try:
            available = int(prod.get('stock') or 0)
        except Exception:
            available = 0

        if new_quantity > available:
            flash(f'Requested quantity ({new_quantity}) exceeds available stock ({available}).', 'error')
            return redirect(url_for('cart'))

        # Compute total price safely in Python
        try:
            price_val = float(prod.get('price') or 0)
        except Exception:
            price_val = 0.0
        total_price = new_quantity * price_val

        # Update quantity and total_price
        cursor.execute("""
            UPDATE cart 
            SET quantity = %s, total_price = %s, updated_at = CURRENT_TIMESTAMP
            WHERE userID = %s AND productID = %s AND status = 'active'
        """, (new_quantity, total_price, user_id, product_id))

        conn.commit()
        flash('Cart updated successfully.', 'success')

    except Exception as e:
        conn.rollback()
        app.logger.exception("Error updating cart quantity")
        flash('Error updating cart.', 'error')
    finally:
        try:
            conn.close()
        except Exception:
            pass
    
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """Remove a product from cart"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')

    if not user_id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Not logged in'}), 401
        flash('Please log in to update cart.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        flash('Database connection failed.', 'error')
        return redirect(url_for('cart'))

    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM cart
            WHERE userID = %s AND productID = %s AND status = 'active'
        """, (user_id, product_id))
        conn.commit()

        if is_ajax:
            # Compute remaining cart totals for UI update
            cursor.execute("""
                SELECT SUM(c.quantity * p.price) as subtotal, COUNT(*) as item_count
                FROM cart c
                JOIN products p ON c.productID = p.productID
                WHERE c.userID = %s AND c.status = 'active'
            """, (user_id,))
            row = cursor.fetchone()
            subtotal = float(row[0] or 0)
            item_count = int(row[1] or 0)
            return jsonify({
                'success': True,
                'new_subtotal': subtotal,
                'new_total': subtotal + 30,
                'item_count': item_count
            })

        flash('Item removed from cart.', 'success')

    except Exception as e:
        conn.rollback()
        app.logger.exception("Error removing from cart")
        if is_ajax:
            return jsonify({'success': False, 'message': 'Error removing item'}), 500
        flash('Error removing item from cart.', 'error')
    finally:
        conn.close()

    return redirect(url_for('cart'))

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    """Clear all items from cart"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    if not user_id:
        flash('Please log in to update cart.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection failed.', 'error')
        return redirect(url_for('cart'))
    
    try:
        cursor = conn.cursor()
        
        # Clear all items from cart
        cursor.execute("DELETE FROM cart WHERE userID = %s AND status = 'active'", (user_id,))
        
        conn.commit()
        flash('Cart cleared successfully.', 'success')
        
    except Exception as e:
        conn.rollback()
        app.logger.exception("Error clearing cart")
        flash('Error clearing cart.', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('cart'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    
    # Debug logging
    app.logger.info(f"Adding product {product_id} to cart with quantity {quantity}")
    
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    # Require user to be logged in to add items to cart
    if not user_id:
        flash('Please log in to add items to your cart.', 'warning')
        return redirect(url_for('login'))
    
    # Use database-based cart for logged-in users
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.", "error")
        return redirect(url_for('home'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get product details
        cursor.execute("SELECT * FROM products WHERE productID = %s LIMIT 1", (product_id,))
        product = cursor.fetchone()
        
        app.logger.info(f"Product query result: {product}")
        
        if not product:
            flash("Product not found.", "error")
            return redirect(url_for('home'))
        
        # Check if item already exists in cart
        cursor.execute("SELECT cartID, quantity FROM cart WHERE userID = %s AND productID = %s", (user_id, product_id))
        existing_item = cursor.fetchone()
        
        if existing_item:
            # Update existing item
            new_quantity = existing_item['quantity'] + quantity
            total_price = new_quantity * float(product['price'])
            
            cursor.execute("""
                UPDATE cart 
                SET quantity = %s, total_price = %s, updated_at = CURRENT_TIMESTAMP
                WHERE cartID = %s
            """, (new_quantity, total_price, existing_item['cartID']))
        else:
            # Add new item
            total_price = quantity * float(product['price'])
            cursor.execute("""
                INSERT INTO cart (userID, productID, quantity, price, total_price, status)
                VALUES (%s, %s, %s, %s, %s, 'active')
            """, (user_id, product_id, quantity, product['price'], total_price))
        
        conn.commit()
        flash(f"Added {product['name']} to cart!", "success")
        return redirect(url_for('cart'))
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error adding to cart: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
def _get_seller_pickup_location(cursor, seller_id):
    try:
        cursor.execute(
            'SELECT region, province, city, barangay, exact_address FROM sellers WHERE sellerID = %s LIMIT 1',
            (seller_id,)
        )
        row = cursor.fetchone()
        return row or {}
    except Exception:
        return {}


def _group_checkout_items_by_seller(cart_items):
    seller_groups = []
    groups_by_key = {}
    for item in cart_items:
        seller_id = item.get('sellerID')
        seller_key = seller_id if seller_id is not None else f'item:{item.get("productID")}'
        if seller_key not in groups_by_key:
            group = {'seller_id': seller_id, 'items': []}
            groups_by_key[seller_key] = group
            seller_groups.append(group)
        groups_by_key[seller_key]['items'].append(item)
    return seller_groups


@app.route('/checkout', methods=['GET', 'POST'])
def process_checkout():
    """Render checkout page (GET) or process checkout (POST)."""
    # Get user ID from session
    user_obj = {}
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
        user_obj = user_obj if isinstance(user_obj, dict) else {}

    buyer_display_name = None
    if isinstance(user_obj, dict):
        first_name = user_obj.get('firstname') or user_obj.get('first_name') or user_obj.get('firstName')
        last_name = user_obj.get('lastname') or user_obj.get('last_name') or user_obj.get('lastName')
        name_parts = [part.strip() for part in (first_name, last_name) if part]
        if name_parts:
            buyer_display_name = ' '.join(name_parts)
        if not buyer_display_name:
            buyer_display_name = user_obj.get('username') or user_obj.get('name') or user_obj.get('email')
    if not buyer_display_name:
        buyer_display_name = f"User #{user_id}" if user_id else 'Customer'

    # GET: render checkout page with current cart or a direct product
    if request.method == 'GET':
        if not user_id:
            flash('Please log in to checkout.', 'warning')
            return redirect(url_for('login'))

        mode = 'cart'
        direct_item = None
        cart_items = []

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)

                # Direct single-product checkout (from product page)
                raw_pid = request.args.get('product_id') or request.args.get('pid')
                raw_qty = request.args.get('qty') or request.args.get('quantity')
                if raw_pid and raw_qty:
                    try:
                        pid = int(raw_pid)
                        qty = int(raw_qty)
                    except Exception:
                        pid = None
                        qty = 0
                    if pid and qty > 0:
                        cursor.execute(
                            "SELECT productID, name, price, stock, image_path FROM products WHERE productID = %s LIMIT 1",
                            (pid,),
                        )
                        row = cursor.fetchone()
                        if row:
                            mode = 'direct'
                            price = float(row.get('price') or 0)
                            stock = int(row.get('stock') or 0)
                            direct_item = {
                                'product_id': row.get('productID'),
                                'name': row.get('name') or 'Product',
                                'price': price,
                                'quantity': qty,
                                'stock': stock,
                                'image': row.get('image_path'),
                                'total_price': price * qty,
                            }

                # Fallback to cart-based checkout summary
                if mode == 'cart':
                    # Check for specific items selected from cart
                    selected_items_str = request.args.get('items')
                    selected_ids = []
                    if selected_items_str:
                        try:
                            selected_ids = [int(x) for x in selected_items_str.split(',') if x.strip()]
                        except:
                            pass

                    base_query = """
                        SELECT 
                            c.cartID,
                            c.productID as product_id,
                            p.name,
                            p.image_path as image,
                            p.stock as stock,
                            c.quantity,
                            c.price,
                            c.total_price
                        FROM cart c
                        JOIN products p ON c.productID = p.productID
                        WHERE c.userID = %s AND c.status = 'active'
                    """
                    params = [user_id]

                    if selected_ids:
                        placeholders = ','.join(['%s'] * len(selected_ids))
                        base_query += f" AND c.productID IN ({placeholders})"
                        params.extend(selected_ids)

                    base_query += " ORDER BY c.added_at DESC"

                    cursor.execute(base_query, tuple(params))
                    rows = cursor.fetchall() or []
                    for item in rows:
                        cart_items.append(
                            {
                                'product_id': item.get('product_id'),
                                'name': item.get('name'),
                                'price': float(item.get('price') or 0),
                                'stock': int(item.get('stock') or 0),
                                'quantity': int(item.get('quantity') or 0),
                                'image': item.get('image'),
                                'total_price': float(item.get('total_price') or 0),
                            }
                        )
            except Exception:
                try:
                    app.logger.exception("Failed to build checkout summary")
                except Exception:
                    pass
            finally:
                try:
                    cursor.close()
                    conn.close()
                except Exception:
                    pass

        # Validate stock availability
        if cart_items:
            for item in cart_items:
                if item['quantity'] > item['stock']:
                    flash(f"Item '{item['name']}' has insufficient stock (Requested: {item['quantity']}, Available: {item['stock']}). Please update your cart.", 'error')
                    return redirect(url_for('cart'))
        
        if direct_item:
            if direct_item['quantity'] > direct_item['stock']:
                flash(f"Item '{direct_item['name']}' has insufficient stock (Requested: {direct_item['quantity']}, Available: {direct_item['stock']}).", 'error')
                return redirect(url_for('cart'))

        # If there is no direct item and no cart items, send user back to cart
        if not direct_item and not cart_items:
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('cart'))

        return render_template(
            'checkout.html',
            mode=mode,
            direct_item=direct_item,
            cart_items=cart_items,
            user_id=user_id,
        )

    # POST: process checkout and create pending order
    # Require user to be logged in
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in to checkout'}), 401

    # Get form data
    data = request.get_json() or request.form
    region = data.get('region', '').strip()
    province = data.get('province', '').strip()
    city = data.get('city', '').strip()
    barangay = data.get('barangay', '').strip()
    home_address = data.get('home_address', '').strip()
    contact_number = data.get('contact_number', '').strip()
    payment_method = data.get('payment_method', 'cash_on_delivery').strip()
    
    # Validate required fields
    if not all([region, province, city, barangay, home_address, contact_number]):
        return jsonify({'success': False, 'msg': 'Please fill in all required fields'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)

        # Determine if this is a direct single-product checkout (from product detail modal)
        direct_mode = False
        cart_items = []

        raw_pid = None
        raw_qty = None
        try:
            raw_pid = data.get('product_id') or data.get('direct_product_id')
            raw_qty = data.get('quantity') or data.get('direct_quantity')
        except Exception:
            raw_pid = None
            raw_qty = None

        if raw_pid is not None and raw_qty is not None:
            try:
                pid = int(raw_pid)
                qty = int(raw_qty)
            except Exception:
                pid = None
                qty = 0
            if pid and qty > 0:
                direct_mode = True
                cursor.execute("SELECT productID, price, sellerID, name, stock FROM products WHERE productID = %s LIMIT 1", (pid,))
                product_row = cursor.fetchone()
                if not product_row:
                    return jsonify({'success': False, 'msg': 'Product not found for checkout'}), 400
                price = float(product_row['price'])
                cart_items = [{
                    'productID': product_row['productID'],
                    'name': product_row['name'],
                    'stock': product_row['stock'],
                    'quantity': qty,
                    'price': price,
                    'total_price': price * qty,
                    'sellerID': product_row.get('sellerID')
                }]
            else:
                return jsonify({'success': False, 'msg': 'Invalid product or quantity for checkout'}), 400

        if not direct_mode:
            # Normal cart-based checkout: pull active items from cart table
            cursor.execute("""
                SELECT c.*, p.name, p.image_path, p.sellerID, p.stock
                FROM cart c
                JOIN products p ON c.productID = p.productID
                WHERE c.userID = %s AND c.status = 'active'
            """, (user_id,))
            all_cart_items = cursor.fetchall()
            
            # Filter by selected items if provided
            selected_ids = data.get('items')
            if selected_ids and isinstance(selected_ids, list):
                try:
                    sel_set = set(int(x) for x in selected_ids)
                    cart_items = [i for i in all_cart_items if i['productID'] in sel_set]
                except ValueError:
                    cart_items = all_cart_items
            else:
                cart_items = all_cart_items
        
        if not cart_items:
            return jsonify({'success': False, 'msg': 'Your cart is empty or no items selected'}), 400

        shipping_address = f"{home_address}, {barangay}, {city}, {province}, {region}"
        delivery_location = {
            'region': region,
            'province': province,
            'city': city,
            'barangay': barangay,
        }

        generated_order_numbers = []
        generated_pending_ids = []

        has_shipping_fee_col = False
        try:
            cursor.execute("SHOW COLUMNS FROM user_pending_orders LIKE 'shipping_fee'")
            has_shipping_fee_col = cursor.fetchone() is not None
        except Exception:
            has_shipping_fee_col = False

        import datetime
        import random

        for group_index, seller_group in enumerate(_group_checkout_items_by_seller(cart_items)):
            group_items = seller_group['items']
            seller_id = seller_group.get('seller_id')

            current_shipping = estimate_shipping_fee(
                _get_seller_pickup_location(cursor, seller_id) if seller_id else {},
                delivery_location,
            )

            order_subtotal = 0.0
            normalized_items = []
            for item in group_items:
                try:
                    req_qty = int(item.get('quantity') or 0)
                except Exception:
                    req_qty = 0
                prod_id = item.get('productID')

                if req_qty <= 0:
                    conn.rollback()
                    return jsonify({'success': False, 'msg': f'Invalid quantity for product {prod_id}.'}), 400

                cursor.execute(
                    "UPDATE products SET stock = stock - %s WHERE productID = %s AND stock >= %s",
                    (req_qty, prod_id, req_qty)
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    pname = item.get('name') or str(prod_id)
                    avail = int(item.get('stock') or 0)
                    return jsonify({
                        'success': False,
                        'msg': f'Requested quantity for "{pname}" exceeds available stock ({avail}).',
                        'product_id': prod_id,
                        'available_stock': avail
                    }), 400

                item_price = float(item['price'])
                item_total = item_price * req_qty
                order_subtotal += item_total
                normalized_items.append((item, prod_id, req_qty, item_price, item_total))

            now = datetime.datetime.now()
            order_number = (
                f"BB{now.strftime('%Y%m%d%H%M%S')}"
                f"{now.microsecond:06d}"
                f"{random.randint(10000, 99999)}{group_index}{user_id}"
            )

            order_total = order_subtotal + current_shipping

            if has_shipping_fee_col:
                cursor.execute("""
                    INSERT INTO user_pending_orders (userID, order_number, total_amount, shipping_fee, shipping_address, contact_number, payment_method, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'confirmed')
                """, (user_id, order_number, order_total, current_shipping, shipping_address, contact_number, payment_method))
            else:
                cursor.execute("""
                    INSERT INTO user_pending_orders (userID, order_number, total_amount, shipping_address, contact_number, payment_method, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'confirmed')
                """, (user_id, order_number, order_total, shipping_address, contact_number, payment_method))

            pending_id = cursor.lastrowid
            generated_pending_ids.append(pending_id)
            generated_order_numbers.append(order_number)

            for item, prod_id, req_qty, item_price, item_total in normalized_items:
                cursor.execute("""
                    INSERT INTO user_pending_order_items (pendingID, productID, quantity, price, total_price)
                    VALUES (%s, %s, %s, %s, %s)
                """, (pending_id, prod_id, req_qty, item_price, item_total))

            if seller_id:
                cursor.execute("""
                    INSERT INTO seller_orders (originalPendingID, userID, sellerID, order_number, total_amount,
                                               shipping_address, contact_number, payment_method, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """, (pending_id, user_id, seller_id, order_number, order_total,
                      shipping_address, contact_number, payment_method))

                seller_order_id = cursor.lastrowid

                for item, prod_id, req_qty, item_price, item_total in normalized_items:
                    cursor.execute("""
                        INSERT INTO seller_order_items (sellerOrderID, productID, quantity, price, total_price)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (seller_order_id, prod_id, req_qty, item_price, item_total))

                cursor.execute("""
                    INSERT INTO order_status_history (sellerOrderID, status, message)
                    VALUES (%s, 'pending', 'Order confirmed and received by seller')
                """, (seller_order_id,))

                try:
                    item_names = ', '.join(str(item.get('name') or 'Product').strip() for item, *_ in normalized_items)
                    notif_title = 'New order placed'
                    notif_body = (
                        f"{buyer_display_name} ordered {item_names} "
                        f"(Order {order_number}) - Shipping ₱{current_shipping:.2f}, Total ₱{order_total:.2f}"
                    )
                    cursor.execute(
                        "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)",
                        (seller_id, notif_title, notif_body)
                    )
                    emit_notification_event(
                        'seller',
                        seller_id,
                        notif_title,
                        notif_body,
                        {'sellerOrderID': seller_order_id, 'order_number': order_number}
                    )
                except Exception:
                    app.logger.debug('Failed to enqueue seller notification for %s', order_number, exc_info=True)

            if not direct_mode:
                for _, prod_id, _, _, _ in normalized_items:
                    cursor.execute("DELETE FROM cart WHERE userID = %s AND productID = %s AND status = 'active'", (user_id, prod_id))

        conn.commit()
        
        app.logger.info(f"Checkout complete. Generated orders: {generated_order_numbers}")
        
        return jsonify({
            'success': True, 
            'msg': 'Orders placed successfully! You can track them in Your Orders.',
            'order_numbers': generated_order_numbers,
            'pending_ids': generated_pending_ids
        }), 200

    except Exception as e:
        conn.rollback()
        app.logger.exception("Error processing checkout")
        msg = str(e)
        if "Duplicate entry" in msg and "order_number" in msg:
             msg = "System error: Duplicate order number generated. Please try again."
        return jsonify({'success': False, 'msg': f'Error processing order: {msg}'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/shipping/estimate', methods=['POST'])
def estimate_shipping():
    user_obj = session.get('user') or {}
    user_id = user_obj.get('userID') or session.get('user_id')
    app.logger.info('ShippingEst: user_id=%s session_keys=%s', user_id, list(session.keys()))
    if not user_id:
        app.logger.info('ShippingEst: REJECTED — unauthorized')
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or request.form or {}
    region = (payload.get('region') or '').strip()
    province = (payload.get('province') or '').strip()
    city = (payload.get('city') or '').strip()
    barangay = (payload.get('barangay') or '').strip()
    app.logger.info('ShippingEst: region=%r province=%r city=%r barangay=%r raw_items=%r raw_pid=%r',
                    region, province, city, barangay,
                    payload.get('items'), payload.get('product_id'))

    # Only region + province are needed to compute the fee; city and barangay
    # are collected here for record-keeping but not required for the estimate.
    if not region:
        app.logger.info('ShippingEst: REJECTED — missing region')
        return jsonify({'success': False, 'msg': 'Missing delivery region'}), 400

    delivery_location = {
        'region': region,
        'province': province,
        'city': city,
        'barangay': barangay,
    }

    product_ids = []
    raw_items = payload.get('items')
    raw_product_id = payload.get('product_id') or payload.get('direct_product_id')
    if isinstance(raw_items, list):
        for value in raw_items:
            try:
                product_ids.append(int(value))
            except (TypeError, ValueError):
                continue
    elif raw_product_id is not None:
        try:
            product_ids.append(int(raw_product_id))
        except (TypeError, ValueError):
            pass

    app.logger.info('ShippingEst: product_ids=%s', product_ids)
    if not product_ids:
        app.logger.info('ShippingEst: REJECTED — no product_ids parsed')
        return jsonify({'success': False, 'msg': 'Missing product selection'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        placeholders = ','.join(['%s'] * len(product_ids))
        cursor.execute(
            f"SELECT productID, sellerID FROM products WHERE productID IN ({placeholders})",
            tuple(product_ids),
        )
        rows = cursor.fetchall() or []
        app.logger.info('ShippingEst: product query returned %d rows: %s', len(rows), rows)
        # If none of the requested product IDs exist, do NOT silently fall back
        # to the base fee — surface it so the frontend can warn.
        if not rows:
            app.logger.info('ShippingEst: REJECTED — no matching products for IDs %s', product_ids)
            return jsonify({
                'success': False,
                'msg': 'No matching sellers for the selected products.',
            }), 404
        shipping_total = 0.0
        seen_sellers = set()
        for row in rows:
            seller_id = row.get('sellerID')
            if seller_id in seen_sellers:
                continue
            seen_sellers.add(seller_id)
            pickup = _get_seller_pickup_location(cursor, seller_id) if seller_id else {}
            fee = estimate_shipping_fee(pickup, delivery_location)
            app.logger.info('ShippingEst: seller=%s pickup=%s delivery_region=%r delivery_province=%r fee=%.2f',
                            seller_id, pickup, region, province, fee)
            shipping_total += fee

        final_fee = round(float(max(shipping_total, DEFAULT_SHIPPING_FEE)), 2)
        app.logger.info('ShippingEst: shipping_total=%.2f final_fee=%.2f', shipping_total, final_fee)
        return jsonify({
            'success': True,
            'shipping_fee': final_fee,
            'delivery_address': delivery_location,
        }), 200
    except Exception as e:
        app.logger.exception('Shipping estimate failed')
        return jsonify({'success': False, 'msg': f'Failed to estimate shipping: {e}'}), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

@app.route('/checkout/modal', methods=['GET'])
def checkout_modal():
    """Return the checkout modal HTML fragment so other pages can fetch it via AJAX."""
    try:
        return render_template('partials/checkout_modal.html')
    except Exception as e:
        app.logger.exception('Failed to render checkout modal')
        return jsonify({'success': False, 'msg': 'Failed to load modal'}), 500


@app.route('/api/user/address', methods=['GET', 'POST'])
def api_user_address():
    """GET: return saved address for current user (structured fields).
       POST: save/overwrite the user's saved address. We persist structured
       values and also update the most recent seller_orders.shipping_address
       for compatibility.
    """
    user_obj = session.get('user') or {}
    user_id = user_obj.get('userID') or session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        if request.method == 'GET':
            # Try to read most recent structured address from a lightweight table
            try:
                cur.execute("SHOW TABLES LIKE 'user_saved_addresses'")
                if cur.fetchone():
                    cur.execute("SELECT * FROM user_saved_addresses WHERE userID = %s LIMIT 1", (user_id,))
                    row = cur.fetchone()
                    if row:
                        return jsonify({'success': True, 'address': {
                            'region': row.get('region') or '',
                            'province': row.get('province') or '',
                            'city': row.get('city') or '',
                            'barangay': row.get('barangay') or '',
                            'home_address': row.get('home_address') or '',
                            'contact_number': row.get('contact_number') or ''
                        }}), 200
            except Exception:
                # ignore and fallback
                pass

            # Fallback: try seller_orders shipping_address (string) then user_pending_orders
            try:
                cur.execute("SELECT shipping_address, contact_number FROM seller_orders WHERE userID = %s AND shipping_address IS NOT NULL ORDER BY created_at DESC LIMIT 1", (user_id,))
                r = cur.fetchone()
                if not r:
                    cur.execute("SELECT shipping_address, contact_number FROM user_pending_orders WHERE userID = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
                    r = cur.fetchone()
                if r and r.get('shipping_address'):
                    # shipping_address is stored as: "home_address, barangay, city, province, region"
                    parts = [p.strip() for p in (r.get('shipping_address') or '').split(',')]
                    # Map parts from right-to-left to region/province/city/barangay/home
                    parts = [p for p in parts if p]
                    # assign defaults
                    region = parts[-1] if len(parts) >= 1 else ''
                    province = parts[-2] if len(parts) >= 2 else ''
                    city = parts[-3] if len(parts) >= 3 else ''
                    barangay = parts[-4] if len(parts) >= 4 else ''
                    home_address = ', '.join(parts[0: max(0, len(parts)-4)]) if len(parts) > 4 else (parts[0] if parts else '')
                    return jsonify({'success': True, 'address': {
                        'region': region,
                        'province': province,
                        'city': city,
                        'barangay': barangay,
                        'home_address': home_address,
                        'contact_number': r.get('contact_number') or ''
                    }}), 200
            except Exception:
                pass

            return jsonify({'success': True, 'address': None}), 200

        # POST: save/overwrite address
        data = request.get_json(silent=True) or request.form or {}
        region = (data.get('region') or '').strip()
        province = (data.get('province') or '').strip()
        city = (data.get('city') or '').strip()
        barangay = (data.get('barangay') or '').strip()
        home_address = (data.get('home_address') or '').strip()
        contact_number = (data.get('contact_number') or '').strip()

        if not all([region, province, city, barangay, home_address, contact_number]):
            return jsonify({'success': False, 'msg': 'Missing address fields'}), 400

        # Create table if needed
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_saved_addresses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    userID INT NOT NULL UNIQUE,
                    region VARCHAR(255),
                    province VARCHAR(255),
                    city VARCHAR(255),
                    barangay VARCHAR(255),
                    home_address TEXT,
                    contact_number VARCHAR(64),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        except Exception:
            # ignore create errors
            pass

        # Upsert saved address
        try:
            cur.execute("SELECT userID FROM user_saved_addresses WHERE userID = %s LIMIT 1", (user_id,))
            if cur.fetchone():
                cur.execute("UPDATE user_saved_addresses SET region=%s, province=%s, city=%s, barangay=%s, home_address=%s, contact_number=%s WHERE userID=%s",
                            (region, province, city, barangay, home_address, contact_number, user_id))
            else:
                cur.execute("INSERT INTO user_saved_addresses (userID, region, province, city, barangay, home_address, contact_number) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (user_id, region, province, city, barangay, home_address, contact_number))
        except Exception:
            # ignore upsert failures
            pass

        # For compatibility, also update most recent seller_orders shipping_address/contact_number if exists
        try:
            shipping_address = f"{home_address}, {barangay}, {city}, {province}, {region}"
            cur.execute("UPDATE seller_orders SET shipping_address = %s, contact_number = %s WHERE userID = %s ORDER BY created_at DESC LIMIT 1", (shipping_address, contact_number, user_id))
        except Exception:
            # ignore if table/columns missing
            pass

        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        app.logger.exception('api_user_address failed')
        return jsonify({'success': False, 'msg': 'Server error'}), 500
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass
        

@app.route('/orders')
def user_orders():
    """Display user's orders with pending confirmation"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    # Require user to be logged in
    if not user_id:
        flash('Please log in to view your orders.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    pending_orders = []
    confirmed_orders = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get user's pending orders (waiting for confirmation)
            cursor.execute("""
                SELECT upo.*, 
                       COUNT(upoi.itemID) as item_count
                FROM user_pending_orders upo
                LEFT JOIN user_pending_order_items upoi ON upo.pendingID = upoi.pendingID
                WHERE upo.userID = %s AND upo.status = 'pending_confirmation'
                GROUP BY upo.pendingID
                ORDER BY upo.created_at DESC
            """, (user_id,))
            pending_orders = cursor.fetchall()
            
            # Get order items for each pending order
            for order in pending_orders:
                cursor.execute("""
                    SELECT upoi.*, p.name, p.image_path
                    FROM user_pending_order_items upoi
                    JOIN products p ON upoi.productID = p.productID
                    WHERE upoi.pendingID = %s
                """, (order['pendingID'],))
                order['order_items'] = cursor.fetchall()
            
            # Get confirmed orders (from seller_orders) - exclude cancelled orders
            cursor.execute("""
                SELECT so.*, 
                       COUNT(soi.itemID) as item_count
                FROM seller_orders so
                LEFT JOIN seller_order_items soi ON so.sellerOrderID = soi.sellerOrderID
                WHERE so.userID = %s AND (so.status IS NULL OR so.status != 'cancelled')
                GROUP BY so.sellerOrderID
                ORDER BY so.created_at DESC
            """, (user_id,))
            confirmed_orders = cursor.fetchall()
            
            # Get order items for each confirmed order and attach report metadata
            for order in confirmed_orders:
                cursor.execute("""
                    SELECT soi.*, p.name, p.image_path
                    FROM seller_order_items soi
                    JOIN products p ON soi.productID = p.productID
                    WHERE soi.sellerOrderID = %s
                """, (order['sellerOrderID'],))
                order['order_items'] = cursor.fetchall()

                # Normalize confirmation flags so templates can check booleans safely
                order['buyer_received'] = bool(order.get('buyer_received'))
                order['revenue_released'] = bool(order.get('revenue_released'))
                order['has_active_report'] = False
                order['report'] = None

                try:
                    cursor.execute(
                        """
                        SELECT id, status, issue_type, description, message, created_at,
                               escalated_to_admin, escalated_at, escalation_note
                        FROM reports
                        WHERE reported_order_id = %s AND reporter_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (order['sellerOrderID'], user_id)
                    )
                    report_row = cursor.fetchone()
                    if report_row:
                        order['report'] = {
                            'id': report_row.get('id'),
                            'status': report_row.get('status'),
                            'issue_type': report_row.get('issue_type') or report_row.get('description'),
                            'description': report_row.get('description'),
                            'message': report_row.get('message'),
                            'created_at': report_row.get('created_at'),
                            'escalated_to_admin': bool(report_row.get('escalated_to_admin')),
                            'escalated_at': report_row.get('escalated_at'),
                            'escalation_note': report_row.get('escalation_note')
                        }
                        active_status = (order['report']['status'] or '').lower() in ('open', 'pending', 'escalated')
                        order['has_active_report'] = active_status
                except Exception:
                    order['report'] = None

                # Attach POD data for delivered orders
                order['pod_image_url'] = None
                order['pod_uploaded_at'] = None
                if order.get('status') == 'delivered':
                    try:
                        cursor.execute(
                            "SELECT image_path, upload_timestamp FROM proof_of_delivery WHERE seller_order_id = %s LIMIT 1",
                            (order['sellerOrderID'],)
                        )
                        pod_row = cursor.fetchone()
                        if pod_row:
                            order['pod_image_url'] = pod_row.get('image_path')
                            order['pod_uploaded_at'] = pod_row.get('upload_timestamp')
                    except Exception:
                        pass
                
        except Exception as e:
            app.logger.exception("Error fetching orders")
        finally:
            conn.close()
    
    return render_template('orders.html', 
                         pending_orders=pending_orders, 
                         confirmed_orders=confirmed_orders)


@app.route('/orders/cancelled')
def cancelled_orders():
    """Display user's cancelled orders"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    # Require user to be logged in
    if not user_id:
        flash('Please log in to view your cancelled orders.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cancelled_pending_orders = []
    cancelled_confirmed_orders = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get cancelled pending orders
            cursor.execute("""
                SELECT upo.*, 
                       COUNT(upoi.itemID) as item_count
                FROM user_pending_orders upo
                LEFT JOIN user_pending_order_items upoi ON upo.pendingID = upoi.pendingID
                WHERE upo.userID = %s AND upo.status = 'cancelled'
                GROUP BY upo.pendingID
                ORDER BY upo.created_at DESC
            """, (user_id,))
            cancelled_pending_orders = cursor.fetchall()
            
            # Get order items for each cancelled pending order
            for order in cancelled_pending_orders:
                cursor.execute("""
                    SELECT upoi.*, p.name, p.image_path, p.stock
                    FROM user_pending_order_items upoi
                    JOIN products p ON upoi.productID = p.productID
                    WHERE upoi.pendingID = %s
                """, (order['pendingID'],))
                order['order_items'] = cursor.fetchall()
            
            # Get cancelled confirmed orders (from seller_orders)
            cursor.execute("""
                SELECT so.*, 
                       COUNT(soi.itemID) as item_count
                FROM seller_orders so
                LEFT JOIN seller_order_items soi ON so.sellerOrderID = soi.sellerOrderID
                WHERE so.userID = %s AND so.status = 'cancelled'
                GROUP BY so.sellerOrderID
                ORDER BY so.created_at DESC
            """, (user_id,))
            cancelled_confirmed_orders = cursor.fetchall()
            
            # Get order items for each cancelled confirmed order
            for order in cancelled_confirmed_orders:
                cursor.execute("""
                    SELECT soi.*, p.name, p.image_path, p.stock
                    FROM seller_order_items soi
                    JOIN products p ON soi.productID = p.productID
                    WHERE soi.sellerOrderID = %s
                """, (order['sellerOrderID'],))
                order['order_items'] = cursor.fetchall()
                
        except Exception as e:
            app.logger.exception("Error fetching cancelled orders")
        finally:
            conn.close()
    
    return render_template('cancelled_orders.html', 
                         cancelled_pending_orders=cancelled_pending_orders, 
                         cancelled_confirmed_orders=cancelled_confirmed_orders)

@app.route('/api/orders/confirm/<int:pending_id>', methods=['POST'])
def confirm_order(pending_id):
    """Confirm a pending order and move it to seller orders"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Prevent duplicate seller_orders creation if they already exist for this pending order
        try:
            cursor.execute("SELECT COUNT(*) AS c FROM seller_orders WHERE originalPendingID = %s", (pending_id,))
            _row = cursor.fetchone() or {'c': 0}
            if int(_row.get('c') or 0) > 0:
                # Just mark as confirmed if still pending and return success
                cursor.execute("""
                    UPDATE user_pending_orders 
                    SET status = 'confirmed' 
                    WHERE pendingID = %s AND userID = %s AND status = 'pending_confirmation'
                """, (pending_id, user_id))
                conn.commit()
                return jsonify({'success': True, 'msg': 'Order already forwarded to sellers. Marked confirmed.'}), 200
        except Exception:
            # Non-fatal: proceed with normal flow
            pass

        # Get pending order details
        cursor.execute("""
            SELECT upo.*, upoi.*, p.sellerID
            FROM user_pending_orders upo
            JOIN user_pending_order_items upoi ON upo.pendingID = upoi.pendingID
            JOIN products p ON upoi.productID = p.productID
            WHERE upo.pendingID = %s AND upo.userID = %s AND upo.status = 'pending_confirmation'
        """, (pending_id, user_id))
        order_data = cursor.fetchall()
        
        if not order_data:
            return jsonify({'success': False, 'msg': 'Order not found or already processed'}), 404
        
        # Group by seller to create separate seller orders
        seller_orders = {}
        for item in order_data:
            seller_id = item['sellerID']
            if seller_id not in seller_orders:
                seller_orders[seller_id] = {
                    'order_number': item['order_number'],
                    'total_amount': 0,
                    'shipping_address': item['shipping_address'],
                    'contact_number': item['contact_number'],
                    'payment_method': item['payment_method'],
                    'items': []
                }
            seller_orders[seller_id]['items'].append(item)
            seller_orders[seller_id]['total_amount'] += float(item['total_price'])
        
        # Create seller orders for each seller
        for seller_id, order_info in seller_orders.items():
            cursor.execute("""
                INSERT INTO seller_orders (originalPendingID, userID, sellerID, order_number, total_amount, 
                                         shipping_address, contact_number, payment_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (pending_id, user_id, seller_id, order_info['order_number'], 
                  order_info['total_amount'], order_info['shipping_address'], 
                  order_info['contact_number'], order_info['payment_method']))
            
            seller_order_id = cursor.lastrowid
            
            # Create seller order items and decrement product stock
            for item in order_info['items']:
                cursor.execute("""
                    INSERT INTO seller_order_items (sellerOrderID, productID, quantity, price, total_price)
                    VALUES (%s, %s, %s, %s, %s)
                """, (seller_order_id, item['productID'], item['quantity'], 
                      item['price'], item['total_price']))
                # Reduce stock (prevent negative values)
                try:
                    cursor.execute(
                        "UPDATE products SET stock = CASE WHEN stock >= %s THEN stock - %s ELSE 0 END WHERE productID = %s",
                        (int(item['quantity']), int(item['quantity']), int(item['productID']))
                    )
                except Exception:
                    # If stock column missing, ignore gracefully
                    pass
            
            # Add initial status history entry
            cursor.execute("""
                INSERT INTO order_status_history (sellerOrderID, status, message)
                VALUES (%s, 'pending', 'Order confirmed and received by seller')
            """, (seller_order_id,))
        
        # Update pending order status to confirmed
        cursor.execute("""
            UPDATE user_pending_orders 
            SET status = 'confirmed' 
            WHERE pendingID = %s
        """, (pending_id,))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'msg': 'Order confirmed successfully! It has been sent to the seller(s).'
        }), 200
        
    except Exception as e:
        conn.rollback()
        app.logger.exception("Error confirming order")
        return jsonify({'success': False, 'msg': f'Error confirming order: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/orders/cancel/<int:pending_id>', methods=['POST'])
def cancel_order(pending_id):
    """Cancel a pending order with reason"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in'}), 401
    
    # Get cancellation reason
    data = request.get_json() or request.form
    cancellation_reason = data.get('reason', '').strip()
    
    if not cancellation_reason:
        return jsonify({'success': False, 'msg': 'Please provide a cancellation reason'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Update pending order status to cancelled
        cursor.execute("""
            UPDATE user_pending_orders 
            SET status = 'cancelled', cancellation_reason = %s
            WHERE pendingID = %s AND userID = %s AND status = 'pending_confirmation'
        """, (cancellation_reason, pending_id, user_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'msg': 'Order not found or already processed'}), 404

        # Fetch order items once so we can restock and log consistently
        order_items = []
        try:
            cursor.execute("SELECT productID, quantity FROM user_pending_order_items WHERE pendingID = %s", (pending_id,))
            order_items = cursor.fetchall() or []
        except Exception:
            order_items = []

        # Restore product stock for cancelled quantities
        for item in order_items:
            try:
                product_id = int(item.get('productID'))
                qty = int(item.get('quantity') or 0)
            except Exception:
                product_id = None
                qty = 0
            if not product_id or qty <= 0:
                continue
            try:
                cursor.execute(
                    "UPDATE products SET stock = stock + %s WHERE productID = %s",
                    (qty, product_id)
                )
            except Exception:
                try:
                    app.logger.warning('Failed to restock product %s after cancellation', product_id)
                except Exception:
                    pass
        
        # Log out-of-stock related cancellations into audit table if reason matches
        try:
            if 'out of stock' in cancellation_reason.lower():
                for it in order_items:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO order_cancellation_log (pendingID, userID, productID, quantity, reason, status, created_at)
                            VALUES (%s, %s, %s, %s, %s, 'cancelled', NOW())
                            """,
                            (pending_id, user_id, it.get('productID'), it.get('quantity'), cancellation_reason)
                        )
                    except Exception:
                        try:
                            app.logger.debug('order_cancellation_log missing; run migration to enable cancellation tracking')
                        except Exception:
                            pass
                try:
                    cursor.execute(
                        """
                        INSERT INTO order_cancellation_audit (pendingID, userID, action, note, created_at)
                        VALUES (%s, %s, 'cancelled', %s, NOW())
                        """,
                        (pending_id, user_id, cancellation_reason)
                    )
                except Exception:
                    pass
        except Exception:
            try: app.logger.exception('Failed to log cancellation')
            except Exception: pass

        conn.commit()
        
        return jsonify({
            'success': True, 
            'msg': 'Order cancelled successfully.'
        }), 200
        
    except Exception as e:
        conn.rollback()
        app.logger.exception("Error cancelling order")
        return jsonify({'success': False, 'msg': f'Error cancelling order: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/orders/<int:seller_order_id>/received', methods=['POST'])
def acknowledge_delivered_order(seller_order_id):
    """Allow a user to confirm receipt of a delivered order so revenue can be released."""
    user_obj = session.get('user') or {}
    user_id = user_obj.get('userID') or session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT sellerOrderID, userID, status, buyer_received, revenue_released
            FROM seller_orders
            WHERE sellerOrderID = %s
            LIMIT 1
            """,
            (seller_order_id,)
        )
        order_row = cur.fetchone()
        if not order_row:
            return jsonify({'success': False, 'msg': 'Order not found'}), 404
        if int(order_row.get('userID') or 0) != int(user_id):
            return jsonify({'success': False, 'msg': 'Unauthorized'}), 403
        current_status = (order_row.get('status') or '').lower()
        if current_status != 'delivered':
            return jsonify({'success': False, 'msg': 'Order is not marked as delivered yet'}), 400

        already_received = bool(order_row.get('buyer_received'))
        if not already_received:
            cur.execute(
                "UPDATE seller_orders SET buyer_received = 1, buyer_received_at = NOW() WHERE sellerOrderID = %s",
                (seller_order_id,)
            )
            try:
                cur.execute(
                    "INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s, %s, %s)",
                    (seller_order_id, 'buyer_received', 'Buyer confirmed receipt of the order')
                )
            except Exception:
                pass

        released, error_code = _release_financials_for_order(conn, seller_order_id, context_note='buyer_confirmed')
        if error_code in ('not_found', 'no_connection'):
            conn.rollback()
            return jsonify({'success': False, 'msg': 'Failed to release funds. Please contact support.'}), 500

        conn.commit()

        msg = 'Thank you for confirming receipt!'
        if not released and error_code == 'already_released':
            msg += ' Funds for this order were already released.'
        return jsonify({'success': True, 'msg': msg}), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('Failed to acknowledge delivered order')
        return jsonify({'success': False, 'msg': 'Server error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/orders/<int:seller_order_id>/report', methods=['POST'])
def report_delivered_order_issue(seller_order_id):
    """Allow a user to report issues with a delivered order."""
    user_obj = session.get('user') or {}
    user_id = user_obj.get('userID') or session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in'}), 401

    payload = request.get_json(silent=True) or {}
    issue_key = (payload.get('issue_type') or '').strip().lower()
    details = (payload.get('details') or '').strip()

    issue_map = {
        'not_received': 'Product not received',
        'product_problem': 'Product problems or discrepancies'
    }
    if issue_key not in issue_map:
        return jsonify({'success': False, 'msg': 'Invalid issue type'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT sellerOrderID, userID, sellerID, riderID, status, order_number
            FROM seller_orders
            WHERE sellerOrderID = %s
            LIMIT 1
            """,
            (seller_order_id,)
        )
        order_row = cur.fetchone()
        if not order_row:
            return jsonify({'success': False, 'msg': 'Order not found'}), 404
        if int(order_row.get('userID') or 0) != int(user_id):
            return jsonify({'success': False, 'msg': 'Unauthorized'}), 403
        if (order_row.get('status') or '').lower() != 'delivered':
            return jsonify({'success': False, 'msg': 'Order must be delivered before reporting'}), 400

        cur.execute(
            "SELECT id FROM reports WHERE reported_order_id = %s AND reporter_id = %s AND status IN ('open','pending','escalated') LIMIT 1",
            (seller_order_id, user_id)
        )
        if cur.fetchone():
            return jsonify({'success': False, 'msg': 'You already submitted a report for this order'}), 409

        product_id = None
        try:
            cur.execute(
                "SELECT productID FROM seller_order_items WHERE sellerOrderID = %s LIMIT 1",
                (seller_order_id,)
            )
            prod_row = cur.fetchone()
            if prod_row and prod_row.get('productID') is not None:
                product_id = int(prod_row.get('productID'))
        except Exception:
            product_id = None

        reporter_name = user_obj.get('username') or user_obj.get('email') or 'User'
        description = issue_map[issue_key]
        message_text = details if details else None

        cur.execute(
            """
            INSERT INTO reports (
                reporter_id, reporter_name, reported_product_id, reported_order_id,
                reported_shop_id, reported_rider_id, role, description, message,
                status, complaint_type, issue_type, offense_level
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'User', %s, %s, 'open', %s, %s, 0)
            """,
            (
                user_id,
                reporter_name,
                product_id,
                seller_order_id,
                order_row.get('sellerID'),
                order_row.get('riderID'),
                description,
                message_text,
                description,
                issue_key
            )
        )
        report_id = cur.lastrowid

        # Notify seller (best-effort)
        seller_id = order_row.get('sellerID')
        if seller_id:
            notice = f"Order #{seller_order_id} has a new user report: {description}."
            try:
                # Ensure query string is valid
                cur.execute(
                    "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)",
                    (seller_id, 'New order report', notice)
                )
                emit_notification_event('seller', seller_id, 'New order report', notice)
            except Exception:
                app.logger.debug('Failed to notify seller about order report %s', report_id, exc_info=True)

        # Let admin know there is a new order report (best-effort)
        try:
            admin_notice = f"Order #{seller_order_id} reported by user {reporter_name}."
            cur.execute(
                "INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('admin', %s, %s, %s)",
                (0, 'New order report', admin_notice)
            )
            emit_notification_event('admin', 0, 'New order report', admin_notice)
        except Exception:
            pass

        conn.commit()

        return jsonify({'success': True, 'msg': 'Report submitted successfully'}), 200
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        app.logger.exception('Failed to submit order report')
        return jsonify({'success': False, 'msg': 'Server error'}), 500
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

@app.route('/api/orders/cancellation-reasons')
def get_cancellation_reasons():
    """Get available cancellation reasons"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT reasonID, reason, description 
            FROM order_cancellation_reasons 
            WHERE is_active = TRUE 
            ORDER BY reasonID
        """)
        reasons = cursor.fetchall()
        
        return jsonify({'success': True, 'reasons': reasons}), 200
        
    except Exception as e:
        app.logger.exception("Error fetching cancellation reasons")
        return jsonify({'success': False, 'msg': f'Error fetching reasons: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/orders/cancelled', methods=['GET'])
def api_cancelled_orders():
    """Return cancelled pending orders for the logged-in user with item availability."""
    user = session.get('user') or {}
    user_id = user.get('userID') or session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in'}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT pendingID, order_number, total_amount, cancellation_reason, created_at FROM user_pending_orders WHERE userID = %s AND status = 'cancelled' ORDER BY created_at DESC", (user_id,))
        orders = cur.fetchall() or []
        result = []
        for o in orders:
            pid = o.get('pendingID')
            cur.execute("""
                SELECT i.productID, i.quantity, p.name, p.stock
                FROM user_pending_order_items i
                LEFT JOIN products p ON p.productID = i.productID
                WHERE i.pendingID = %s
            """, (pid,))
            items = cur.fetchall() or []
            all_available = True
            for it in items:
                try:
                    q = int(it.get('quantity') or 0)
                    s = int(it.get('stock') or 0)
                    if s < q:
                        all_available = False
                except Exception:
                    all_available = False
            result.append({
                'pendingID': pid,
                'order_number': o.get('order_number'),
                'total_amount': float(o.get('total_amount') or 0.0),
                'cancellation_reason': o.get('cancellation_reason') or '',
                'created_at': o.get('created_at'),
                'items': items,
                'all_available': all_available
            })
        return jsonify({'success': True, 'orders': result}), 200
    except Exception as e:
        app.logger.exception('Failed to fetch cancelled orders')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass


@app.route('/api/orders/reinstate/<int:pending_id>', methods=['POST'])
def api_reinstate_cancelled(pending_id):
    """Reinstate a cancelled pending order if stock is sufficient. Owner-only."""
    user = session.get('user') or {}
    user_id = user.get('userID') or session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Please log in'}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT userID, status FROM user_pending_orders WHERE pendingID = %s", (pending_id,))
        o = cur.fetchone()
        if not o or int(o.get('userID') or 0) != int(user_id):
            return jsonify({'success': False, 'msg': 'Not authorized'}), 403
        if (o.get('status') or '').lower() != 'cancelled':
            return jsonify({'success': False, 'msg': 'Order is not cancelled'}), 400
        # Check availability
        cur.execute("SELECT productID, quantity FROM user_pending_order_items WHERE pendingID = %s", (pending_id,))
        items = cur.fetchall() or []
        for it in items:
            cur.execute("SELECT stock, name FROM products WHERE productID = %s", (it.get('productID'),))
            prow = cur.fetchone() or {}
            s = int(prow.get('stock') or 0)
            q = int(it.get('quantity') or 0)
            if s < q:
                return jsonify({'success': False, 'msg': f"{(prow.get('name') or 'Product')} insufficient stock"}), 400
        # Reinstate: set status back to pending_confirmation
        cur.execute("UPDATE user_pending_orders SET status = 'pending_confirmation', updated_at = NOW() WHERE pendingID = %s", (pending_id,))
        # Audit and log
        try:
            cur.execute("INSERT INTO order_cancellation_audit (pendingID, userID, action, note, created_at) VALUES (%s, %s, 'reinstated', 'user reinstated after restock', NOW())", (pending_id, user_id))
        except Exception:
            pass
        try:
            cur.execute("UPDATE order_cancellation_log SET status = 'reinstated' WHERE pendingID = %s AND userID = %s", (pending_id, user_id))
        except Exception:
            pass
        conn.commit()
        return jsonify({'success': True, 'msg': 'Order reinstated. Please confirm in Your Orders.'}), 200
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        app.logger.exception('Failed to reinstate cancelled order')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass

@app.route('/api/orders/rider-cancellation')
def get_rider_cancellation():
    """Get available cancellation reasons"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT r_reasonID, r_reason, description 
            FROM order_rider_cancellation
            WHERE is_active = TRUE 
            ORDER BY r_reasonID
        """)
        reasons = cursor.fetchall()
        
        return jsonify({'success': True, 'reasons': reasons}), 200
        
    except Exception as e:
        app.logger.exception("Error fetching cancellation reasons")
        return jsonify({'success': False, 'msg': f'Error fetching reasons: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/seller/orders/<int:seller_order_id>/status', methods=['POST'])
def api_update_seller_order_status(seller_order_id):
    """API: seller updates the status of a seller_order (packing, picked_up, on_the_way, delivered, cancelled)
    Expects JSON or form data: { status: <new_status>, notes: <optional notes> }
    Only the seller who owns the order may update it.
    Returns JSON { success: True } on success.
    """
    seller = session.get('seller')
    if not seller:
        return jsonify({'success': False, 'msg': 'Seller not authenticated'}), 401

    seller_id = seller.get('id') or seller.get('sellerID')
    if not seller_id:
        return jsonify({'success': False, 'msg': 'Seller not authenticated'}), 401

    data = request.get_json(silent=True) or request.form
    new_status = (data.get('status') or '').strip()
    notes = (data.get('notes') or '').strip()

    if not new_status:
        return jsonify({'success': False, 'msg': 'Missing status'}), 400

    # Basic allowlist for statuses
    allowed = {'pending', 'packing', 'packed', 'assigned_to_rider', 'picked_up', 'on_the_way', 'delivered', 'cancelled'}
    if new_status not in allowed:
        return jsonify({'success': False, 'msg': 'Invalid status'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    try:
        _ensure_seller_order_status_enum()
        cursor = conn.cursor(dictionary=True)
        # Verify ownership: sellerID on seller_orders
        cursor.execute("SELECT sellerOrderID, riderID FROM seller_orders WHERE sellerOrderID = %s AND sellerID = %s LIMIT 1", (seller_order_id, seller_id))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'msg': 'Order not found or not owned by you'}), 404

        # Get current status and rider info for comparison
        cursor.execute("SELECT status, riderID FROM seller_orders WHERE sellerOrderID = %s", (seller_order_id,))
        current_row = cursor.fetchone()
        current_status = current_row['status'] if current_row else 'unknown'
        current_rider_id = current_row['riderID'] if current_row else None

        # Prevent further updates to cancelled orders
        if current_status == 'cancelled':
            return jsonify({'success': False, 'msg': 'Cannot update a cancelled order'}), 400

        # Get rider name if riderID is set
        rider_name = None
        if current_rider_id:
            try:
                cursor.execute("SELECT ridername FROM riders WHERE riderID = %s LIMIT 1", (current_rider_id,))
                rider_row = cursor.fetchone()
                if rider_row:
                    rider_name = rider_row['ridername']
            except Exception:
                pass

        # Update status and optional notes (if the column exists)
        try:
            # Try to update notes column if present
            cursor.execute("UPDATE seller_orders SET status = %s, updated_at = NOW(), notes = %s WHERE sellerOrderID = %s", (new_status, notes, seller_order_id))
        except Exception:
            # Fallback: update without notes
            cursor.execute("UPDATE seller_orders SET status = %s, updated_at = NOW() WHERE sellerOrderID = %s", (new_status, seller_order_id))

        # Add status history entry with rider information when relevant
        status_messages = {
            'pending': 'Order received and is being processed',
            'packing': 'Order is being prepared for shipment',
            'packed': 'Order has been packed and is ready for pickup',
            'assigned_to_rider': f'Order assigned to rider{" " + rider_name if rider_name else ""}',
            'picked_up': f'Order has been picked up{" by " + rider_name if rider_name else " by delivery service"}',
            'on_the_way': f'Order is on its way to you{" (delivered by " + rider_name + ")" if rider_name else ""}',
            'delivered': 'Order has been delivered successfully',
            'cancelled': 'Order has been cancelled'
        }
        
        message = status_messages.get(new_status, f'Order status changed to {new_status}')
        if notes:
            message += f' - {notes}'
            
        cursor.execute("""
            INSERT INTO order_status_history (sellerOrderID, status, message)
            VALUES (%s, %s, %s)
        """, (seller_order_id, new_status, message))

        if new_status == 'delivered':
            try:
                cursor.execute("SELECT total_amount, sellerID FROM seller_orders WHERE sellerOrderID = %s LIMIT 1", (seller_order_id,))
                o = cursor.fetchone() or {}
                total_amount = Decimal(str(o.get('total_amount') or '0'))
                seller_id = o.get('sellerID')
                VAT_RATE = Decimal('0.02')
                COMMISSION_RATE = Decimal('0.05')
                seller_commission = (total_amount * COMMISSION_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                vat_amount = (total_amount * VAT_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                seller_net = (total_amount - vat_amount - seller_commission).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                admin_share = (seller_commission + vat_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                try:
                    cursor.execute(
                        """
                        INSERT INTO financial_transactions (order_id, seller_id, total_amount, seller_commission, rider_commission, admin_share, vat_amount, seller_net, note)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (seller_order_id, seller_id, str(total_amount), str(seller_commission), '0.00', str(admin_share), str(vat_amount), str(seller_net), 'seller marked delivered; 2% VAT')
                    )
                except Exception:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO financial_transactions (order_id, seller_id, total_amount, seller_commission, rider_commission, admin_share, note)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (seller_order_id, seller_id, str(total_amount), str(seller_commission), '0.00', str(admin_share), 'seller marked delivered; 2% VAT')
                        )
                    except Exception:
                        pass
                try:
                    cursor.execute("INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('seller', %s, %s, %s)", (seller_id, "Sale completed", f"Order #{seller_order_id}: Total ₱{total_amount:.2f} • VAT(2%) ₱{vat_amount:.2f} • Net to seller ₱{seller_net:.2f}"))
                    emit_notification_event('seller', seller_id, "Sale completed", f"Order #{seller_order_id}: Total ₱{total_amount:.2f} • VAT(2%) ₱{vat_amount:.2f} • Net to seller ₱{seller_net:.2f}")
                except Exception:
                    pass
                try:
                    cursor.execute("INSERT INTO notifications (recipient_type, recipient_id, title, body) VALUES ('admin', %s, %s, %s)", (0, "VAT collected", f"Order #{seller_order_id}: VAT(2%) ₱{vat_amount:.2f} from total ₱{total_amount:.2f}"))
                    emit_notification_event('admin', 0, "VAT collected", f"Order #{seller_order_id}: VAT(2%) ₱{vat_amount:.2f} from total ₱{total_amount:.2f}")
                except Exception:
                    pass
            except Exception:
                pass

        conn.commit()
        return jsonify({'success': True, 'msg': 'Status updated'}), 200
    except Exception as e:
        conn.rollback()
        app.logger.exception('Failed to update seller order status')
        return jsonify({'success': False, 'msg': f'Error: {str(e)}'}), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/seller/riders', methods=['GET'])
def api_list_riders():
    """Return active riders for assignment. Seller must be logged in."""
    seller = session.get('seller')
    if not seller:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT riderID, ridername, rideremail, phone, status FROM riders WHERE status = 'active' AND (is_available = 1 OR is_available IS NULL) ORDER BY ridername ASC")
        riders = cur.fetchall() or []
        return jsonify({'success': True, 'riders': riders}), 200
    except Exception as e:
        app.logger.exception('Failed to list riders')
        return jsonify({'success': False, 'msg': f'Error: {str(e)}'}), 500
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/seller/orders/<int:seller_order_id>/assign-rider', methods=['POST'])
def api_assign_rider(seller_order_id):
    """Assign a rider to a seller's order. Requires logged-in seller who owns the order."""
    seller = session.get('seller')
    if not seller:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    seller_id = seller.get('id') or seller.get('sellerID')
    if not seller_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    rider_id = data.get('riderID') or data.get('rider_id')
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Missing riderID'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        # Verify seller owns this order
        cur.execute("SELECT sellerID FROM seller_orders WHERE sellerOrderID = %s LIMIT 1", (seller_order_id,))
        row = cur.fetchone()
        if not row or int(row.get('sellerID')) != int(seller_id):
            return jsonify({'success': False, 'msg': 'Order not found or not owned by you'}), 404

        # Verify rider exists and is active
        cur.execute("SELECT riderID, ridername FROM riders WHERE riderID = %s AND status = 'active'", (rider_id,))
        r = cur.fetchone()
        if not r:
            return jsonify({'success': False, 'msg': 'Rider not found or inactive'}), 400

        # Get order info for notifications
        cur.execute("SELECT userID, order_number FROM seller_orders WHERE sellerOrderID = %s LIMIT 1", (seller_order_id,))
        order_info = cur.fetchone()
        user_id = order_info.get('userID') if order_info else None
        order_number = order_info.get('order_number') if order_info else str(seller_order_id)
        
        # Assign
        cur.execute("UPDATE seller_orders SET riderID = %s, status = 'assigned_to_rider', updated_at = NOW() WHERE sellerOrderID = %s", (rider_id, seller_order_id))
        
        # Create status history entry: "Seller assigns order to [ridername]"
        rider_name = r['ridername']
        cur.execute("INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s, %s, %s)", 
                   (seller_order_id, 'assigned_to_rider', f'Seller assigns order to {rider_name}'))
        
        # Notify rider via notification system
        cur.execute("""
            INSERT INTO notifications (recipient_type, recipient_id, title, body)
            VALUES ('rider', %s, 'New Order Assignment', %s)
        """, (rider_id, f'You have been assigned to deliver Order #{order_number}'))
        
        # Notify seller
        cur.execute("""
            INSERT INTO notifications (recipient_type, recipient_id, title, body)
            VALUES ('seller', %s, 'Rider Assigned', %s)
        """, (seller_id, f'Order #{order_number} has been assigned to {rider_name}'))
        
        # Emit real-time notification to rider via Socket.IO
        try:
            emit_notification_event('rider', rider_id, 'New Order Assignment', f'You have been assigned to deliver Order #{order_number}')
            emit_notification_event('seller', seller_id, 'Rider Assigned', f'Order #{order_number} has been assigned to {rider_name}')
        except Exception:
            pass  # Non-fatal if socket emit fails

        # Create or seed a chat row so the rider sees a conversation entry for this order
        try:
            try:
                # create a short system message linking seller, user, rider and the sellerOrderID
                chat.save_chat_message(conn,
                                       '',
                                       sender_type='seller',
                                       senderID=seller_id,
                                       message=f'Order #{order_number} assigned to {rider_name}',
                                       productID=seller_order_id,
                                       sellerID=seller_id,
                                       userID=user_id,
                                       riderID=rider_id)
            except Exception:
                # non-fatal; still proceed
                app.logger.debug('Failed to create chat seed for assigned order', exc_info=True)
        except Exception:
            pass

        conn.commit()
        return jsonify({'success': True, 'msg': 'Rider assigned', 'rider': {'riderID': r['riderID'], 'ridername': r['ridername']}}), 200
    except Exception as e:
        conn.rollback()
        app.logger.exception('Failed to assign rider')
        return jsonify({'success': False, 'msg': f'Error: {str(e)}'}), 500
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


@app.route('/seller/<int:seller_id>')
def seller_store_page(seller_id):
    """Public store page listing all products for a seller."""
    conn = get_db_connection()
    seller = {'id': seller_id, 'name': 'Store', 'email': None, 'logo_url': None, 'description': None}
    products = []
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            # Fetch seller info if table exists
            try:
                cur.execute("SELECT * FROM sellers WHERE sellerID = %s OR id = %s LIMIT 1", (seller_id, seller_id))
                row = cur.fetchone()
                if row:
                    seller = {
                        'id': row.get('sellerID') or row.get('id') or seller_id,
                        'name': row.get('storename') or row.get('sellername') or 'Store',
                        'email': row.get('selleremail'),
                        'logo_url': url_for('uploaded_file', filename=row.get('storelogo_path')) if row.get('storelogo_path') else None,
                        'description': row.get('storedesc')
                    }
            except Exception:
                pass
            # Fetch seller products
            cur.execute("SELECT * FROM products WHERE sellerID = %s ORDER BY productID DESC", (seller_id,))
            products = cur.fetchall() or []
            # add image_url normalization
            normalized = []
            for r in products:
                if not isinstance(r, dict):
                    normalized.append(r); continue
                img = r.get('image_path') or r.get('image') or r.get('main_image') or r.get('imageurl')
                img_url = url_for('uploaded_file', filename=img) if img else None
                rr = dict(r); rr['image_url'] = img_url
                normalized.append(rr)
            products = normalized
        finally:
            try: cur.close(); conn.close()
            except Exception: pass
    return render_template('seller_page.html', seller=seller, products=products)

@app.route('/seller/orders')
def seller_orders():
    """Display seller's orders"""
    seller = session.get('seller')
    if not seller:
        return redirect(url_for('seller_login'))
    
    seller_id = seller.get('id') or seller.get('sellerID')
    if not seller_id:
        return redirect(url_for('seller_login'))
    
    conn = get_db_connection()
    orders = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get all orders with items aggregated as a proper JSON array
            # Use JSON_ARRAYAGG(JSON_OBJECT(...)) so we receive a JSON array string
            # (safer than GROUP_CONCAT which can break when fields contain commas)
            cursor.execute("""
                SELECT 
                    so.*,
                    u.username as customer_name,
                    r.ridername AS rider_name,
                    GROUP_CONCAT(
                        CONCAT(
                            '{"order_item_id":', soi.itemID,
                            ',"productID":', soi.productID,
                            ',"name":"', COALESCE(p.name, 'Unknown'), '"',
                            ',"quantity":', soi.quantity,
                            ',"price":', soi.price,
                            ',"image_path":"', COALESCE(p.image_path, ''), '"}'
                        ) SEPARATOR ','
                    ) AS items_json
                FROM seller_orders so
                LEFT JOIN seller_order_items soi ON so.sellerOrderID = soi.sellerOrderID 
                LEFT JOIN products p ON soi.productID = p.productID
                LEFT JOIN users u ON so.userID = u.userID
                LEFT JOIN riders r ON so.riderID = r.riderID
                WHERE so.sellerID = %s
                GROUP BY so.sellerOrderID
                ORDER BY so.created_at DESC
            """, (seller_id,))
            db_orders = cursor.fetchall()

            # Process the orders and parse the JSON items (items_json is a JSON array)
            orders = []
            for order in db_orders:
                try:
                    items_json = order.get('items_json')
                    items = []
                    if items_json:
                        try:
                            # Parse GROUP_CONCAT JSON format: {"item1"},{"item2"}
                            items_json = '[' + items_json + ']'
                            items = json.loads(items_json)
                        except Exception:
                            # Fallback: try to parse individual items
                            items = []
                            for part in (items_json or '').split(','):
                                try:
                                    items.append(json.loads(part))
                                except Exception:
                                    continue

                    # Normalize item types and provide safe defaults
                    processed_items = []
                    for it in items:
                        try:
                            processed_items.append({
                                'order_item_id': it.get('order_item_id'),
                                'productID': it.get('productID'),
                                'name': it.get('name'),
                                'quantity': int(it.get('quantity') or 0),
                                'price': float(it.get('price') or 0.0),
                                'image_path': it.get('image_path')
                            })
                        except Exception:
                            # If an individual item is malformed, skip it but continue
                            continue

                    orders.append({
                        'order_number': order.get('order_number'),
                        'sellerOrderID': order.get('sellerOrderID'),
                        'total_amount': float(order.get('total_amount') or 0.0),
                        'status': order.get('status') or 'pending',
                        'created_at': order.get('created_at'),
                        'updated_at': order.get('updated_at'),
                        'customer_name': order.get('customer_name'),
                        'rider_name': order.get('rider_name'),
                        'items': processed_items
                    })
                except Exception as e:
                    app.logger.exception(f"Error processing order {order.get('sellerOrderID')}: {e}")
                    continue
                
        except Exception as e:
            app.logger.exception("Error fetching seller orders")
        finally:
            conn.close()
    
    # Render the dedicated seller orders page so the sidebar "Orders" button
    # navigates to a full orders management view where sellers can update status.
    return render_template('seller_orders.html', orders=orders, seller=seller)

@app.route('/api/orders/<int:order_id>/track')
def track_order(order_id):
    """Get order tracking information"""
    # Get user ID from session
    user_id = None
    try:
        user_obj = session.get('user') or {}
        user_id = user_obj.get('userID') or session.get('user_id')
    except Exception:
        user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        # Try to find the order in the legacy `orders` table first (orderID)
        cursor.execute("""
            SELECT * FROM seller_orders 
            WHERE sellerOrderID = %s AND userID = %s
        """, (order_id, user_id))
        order = cursor.fetchone()

        source_table = 'orders'

        # If not found in orders, try seller_orders (sellerOrderID)
        if not order:
            cursor.execute("""
                SELECT * FROM seller_orders
                WHERE sellerOrderID = %s AND userID = %s
            """, (order_id, user_id))
            order = cursor.fetchone()
            source_table = 'seller_orders' if order else source_table

        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Build a normalized tracking_info structure from either table
        tracking_info = {
            'order_number': order.get('order_number'),
            'status': order.get('status'),
            'current_location': order.get('current_location', ''),
            'estimated_delivery': order.get('estimated_delivery'),
            'tracking_number': order.get('tracking_number', ''),
            'updates': []
        }
        
        # Helper to safely format timestamps for JSON
        def _ts(v):
            try:
                return v.isoformat()
            except Exception:
                return v

        # Get status history from order_status_history table if using seller_orders
        if source_table == 'seller_orders':
            cursor.execute("""
                SELECT status, message, timestamp
                FROM order_status_history
                WHERE sellerOrderID = %s
                ORDER BY timestamp ASC
            """, (order_id,))
            status_history = cursor.fetchall()
            
            for update in status_history:
                message = update['message']
                # Filter out "Rider accepted assignment" messages from user view
                if 'Rider accepted assignment' not in message:
                    tracking_info['updates'].append({
                        'status': update['status'],
                        'message': message,
                        'timestamp': _ts(update['timestamp'])
                    })
        else:
            # Generate tracking updates based on status for legacy orders
            st = tracking_info.get('status')
            if st == 'pending':
                tracking_info['updates'] = [
                    {'status': 'pending', 'message': 'Order received and being processed', 'timestamp': _ts(order.get('created_at'))}
                ]
            elif st == 'packing':
                tracking_info['updates'] = [
                    {'status': 'pending', 'message': 'Order received and being processed', 'timestamp': _ts(order.get('created_at'))},
                    {'status': 'packing', 'message': 'Your order is being prepared for shipment', 'timestamp': _ts(order.get('updated_at'))}
                ]
            elif st == 'picked_up':
                tracking_info['updates'] = [
                    {'status': 'pending', 'message': 'Order received and being processed', 'timestamp': _ts(order.get('created_at'))},
                    {'status': 'packing', 'message': 'Your order is being prepared for shipment', 'timestamp': _ts(order.get('updated_at'))},
                    {'status': 'picked_up', 'message': 'Order picked up by delivery rider', 'timestamp': _ts(order.get('updated_at'))}
                ]
            elif st == 'on_the_way':
                tracking_info['updates'] = [
                    {'status': 'pending', 'message': 'Order received and being processed', 'timestamp': _ts(order.get('created_at'))},
                    {'status': 'packing', 'message': 'Your order is being prepared for shipment', 'timestamp': _ts(order.get('updated_at'))},
                    {'status': 'picked_up', 'message': 'Order picked up by delivery rider', 'timestamp': _ts(order.get('updated_at'))},
                    {'status': 'on_the_way', 'message': f"Out for delivery - Current location: {order.get('current_location', 'In transit')}", 'timestamp': _ts(order.get('updated_at'))}
                ]
            elif st == 'delivered':
                tracking_info['updates'] = [
                    {'status': 'pending', 'message': 'Order received and being processed', 'timestamp': _ts(order.get('created_at'))},
                    {'status': 'packing', 'message': 'Your order is being prepared for shipment', 'timestamp': _ts(order.get('updated_at'))},
                    {'status': 'picked_up', 'message': 'Order picked up by delivery rider', 'timestamp': _ts(order.get('updated_at'))},
                    {'status': 'on_the_way', 'message': 'Out for delivery', 'timestamp': _ts(order.get('updated_at'))},
                    {'status': 'delivered', 'message': 'Order delivered successfully', 'timestamp': _ts(order.get('updated_at'))}
                ]
        
        return jsonify(tracking_info), 200
        
    except Exception as e:
        app.logger.exception("Error tracking order")
        return jsonify({'error': 'Failed to track order'}), 500
    finally:
        conn.close()


# ----------------------
# Socket.IO chat handlers (private messaging model)
# ----------------------

def resolve_socket_identity(role_hint=None, session_token=None):
    """Return (role, id) inferred from the current request/session."""
    role_hint = (role_hint or '').strip().lower() or None
    session_token = (session_token or '').strip() if isinstance(session_token, str) else None

    def _cookie(name):
        try:
            return request.cookies.get(name)
        except Exception:
            return None

    candidates = []

    user_obj = session.get('user') if isinstance(session.get('user'), dict) else None
    if user_obj:
        user_id = user_obj.get('userID') or user_obj.get('id')
        if user_id is not None:
            token_name = 'user_session'
            token_value = session.get(token_name)
            candidates.append({
                'role': 'user',
                'id': str(user_id),
                'token_name': token_name,
                'stored': token_value,
                'cookie': _cookie(token_name),
            })

    admin_obj = session.get('admin') if isinstance(session.get('admin'), dict) else None
    if not admin_obj and user_obj and session.get('user_type') == 'admin':
        admin_obj = {
            'adminID': user_obj.get('userID') or user_obj.get('id'),
            'username': user_obj.get('username'),
            'email': user_obj.get('email'),
        }
    if admin_obj:
        admin_id = admin_obj.get('adminID') or admin_obj.get('id') or admin_obj.get('userID')
        if admin_id is not None:
            token_name = 'admin_session'
            candidates.append({
                'role': 'admin',
                'id': str(admin_id),
                'token_name': token_name,
                'stored': session.get(token_name),
                'cookie': _cookie(token_name),
            })

    seller_obj = session.get('seller') if isinstance(session.get('seller'), dict) else None
    if seller_obj:
        seller_id = seller_obj.get('sellerID') or seller_obj.get('id')
        if seller_id is not None:
            token_name = 'seller_session'
            candidates.append({
                'role': 'seller',
                'id': str(seller_id),
                'token_name': token_name,
                'stored': session.get(token_name),
                'cookie': _cookie(token_name),
            })

    rider_obj = session.get('rider') if isinstance(session.get('rider'), dict) else None
    if rider_obj:
        rider_id = rider_obj.get('riderID') or rider_obj.get('id')
        if rider_id is not None:
            token_name = 'rider_session'
            candidates.append({
                'role': 'rider',
                'id': str(rider_id),
                'token_name': token_name,
                'stored': session.get(token_name),
                'cookie': _cookie(token_name),
            })

    def _matches(candidate):
        if role_hint:
            if candidate['role'] != role_hint:
                return False
        stored = candidate.get('stored')
        cookie_val = candidate.get('cookie')
        if stored and cookie_val and stored != cookie_val:
            return False
        if session_token:
            if stored and session_token != stored:
                return False
            if not stored and cookie_val and session_token != cookie_val:
                return False
            if not stored and not cookie_val:
                return False
        return True

    matches = [c for c in candidates if _matches(c)] or []

    # If multiple matches found, prioritize specific roles over generic 'user'
    if len(matches) > 1:
        # Priority order: admin > seller > rider > user
        for role in ['admin', 'seller', 'rider']:
            match = next((m for m in matches if m['role'] == role), None)
            if match:
                return match['role'], match['id']

    if len(matches) == 1:
        selected = matches[0]
        return selected['role'], selected['id']

    if not matches and candidates and not role_hint and not session_token and len(candidates) == 1:
        c = candidates[0]
        return c['role'], c['id']

    if not matches and role_hint:
        fallback = [c for c in candidates if c['role'] == role_hint]
        if len(fallback) == 1:
            c = fallback[0]
            return c['role'], c['id']

    try:
        token = request.cookies.get('access_token')
    except Exception:
        token = None
    if token:
        try:
            decoded = decode_token(token)
            identity = extract_identity_from_decoded(decoded)
            if isinstance(identity, dict):
                for key, role in (('userID', 'user'), ('sellerID', 'seller'), ('riderID', 'rider')):
                    if identity.get(key) is not None:
                        return role, str(identity.get(key))
        except Exception:
            pass

    return None, None


def _get_identity_from_socket():
    sid = getattr(request, 'sid', None)
    cached = legacy_sid_identity.get(sid) if sid else None
    if cached:
        return cached

    role_hint = None
    session_token = None
    try:
        if request.args:
            role_hint = request.args.get('role') or request.args.get('auth_role') or role_hint
            session_token = request.args.get('session') or request.args.get('session_token') or session_token
    except Exception:
        pass
    try:
        role_header = request.headers.get('X-Chat-Role') if request.headers else None
        session_header = request.headers.get('X-Chat-Session') if request.headers else None
        role_hint = role_header or role_hint
        session_token = session_header or session_token
    except Exception:
        pass

    role, ident = resolve_socket_identity(role_hint=role_hint, session_token=session_token)
    if sid and role and ident:
        legacy_sid_identity[sid] = (role, ident)
    return role, ident


@socketio.on('connect')
def _on_connect(auth):
    role_hint = None
    session_token = None
    if isinstance(auth, dict):
        role_hint = auth.get('role')
        session_token = auth.get('session') or auth.get('session_token')
    role, ident = resolve_socket_identity(role_hint=role_hint, session_token=session_token)
    if not role or not ident:
        # reject unauthenticated socket connections for chat
        try:
            app.logger.debug('Socket connect rejected: unauthenticated')
        except Exception:
            pass
        return False
    legacy_sid_identity[request.sid] = (role, ident)
    key = f"{role}:{ident}"
    sid = request.sid
    s = connected_users.get(key)
    if s is None:
        connected_users[key] = {sid}
    else:
        s.add(sid)
    # Join room for notifications
    room = f'{role}_{ident}'
    join_room(room)
    try:
        app.logger.info(f"Socket connected: key={key} sid={sid} room={room} current_clients={len(connected_users.get(key,[]))}")
    except Exception:
        pass


@socketio.on('join')
def handle_join(data):
    """Handle explicit room join request."""
    role, ident = _get_identity_from_socket()
    if role and ident:
        room = data.get('room') or f'{role}_{ident}'
        join_room(room)
        app.logger.debug(f'Socket joined room: {room}')


@socketio.on('disconnect')
def _on_disconnect():
    sid = request.sid
    # remove sid from any mapping it belongs to
    try:
        for key, sids in list(connected_users.items()):
            if sid in sids:
                sids.remove(sid)
                if not sids:
                    del connected_users[key]
                break
    except Exception:
        try:
            app.logger.exception('Error cleaning disconnected sid')
        except Exception:
            pass
    legacy_sid_identity.pop(sid, None)


def send_chat_message(sender_role, sender_id, recipient_role, recipient_id, message, productID=None, room=None, validation=None, local_id=None):
    """Persist a chat message and emit it privately to recipient's connected socket(s).

    sender_role: 'user' or 'seller' or 'rider'
    sender_id: string id
    recipient_role: 'user' or 'seller' or 'rider'
    recipient_id: string id
    message: message text

    Returns the payload emitted (includes messageID when persisted) or None.
    """
    if not sender_role or not sender_id or not recipient_role or not recipient_id or not message:
        return None

    saved_id = None
    saved_ts = None
    try:
        conn = get_db_connection()
        if conn:
            try:
                # legacy save helper expects room and sender_type; room isn't stored in schema so pass empty string
                # pass userID when recipient is a user so messages have both userID and sellerID populated
                saved = None
                if sender_role in ('user','seller') and recipient_role in ('user','seller'):
                    saved = chat.save_chat_message(
                        conn,
                        '',
                        sender_type=sender_role,
                        senderID=sender_id or '',
                        message=message,
                        productID=productID,
                        sellerID=(recipient_id if recipient_role == 'seller' else None),
                        userID=(recipient_id if recipient_role == 'user' else None)
                    )
                elif sender_role == 'seller' and recipient_role == 'rider':
                    saved = chat.save_chat_message(
                        conn,
                        '',
                        sender_type=sender_role,
                        senderID=sender_id or '',
                        message=message,
                        productID=productID,
                        sellerID=sender_id,
                        userID=None,
                        riderID=recipient_id
                    )
                elif sender_role == 'user' and recipient_role == 'rider':
                    saved = chat.save_chat_message(
                        conn,
                        '',
                        sender_type=sender_role,
                        senderID=sender_id or '',
                        message=message,
                        productID=productID,
                        sellerID=None,
                        userID=sender_id,
                        riderID=recipient_id
                    )
                elif sender_role == 'rider':
                    if recipient_role == 'seller':
                        saved = chat.save_chat_message(
                            conn,
                            '',
                            sender_type=sender_role,
                            senderID=sender_id or '',
                            message=message,
                            productID=productID,
                            sellerID=recipient_id,
                            userID=None,
                            riderID=sender_id
                        )
                    elif recipient_role == 'user':
                        saved = chat.save_chat_message(
                            conn,
                            '',
                            sender_type=sender_role,
                            senderID=sender_id or '',
                            message=message,
                            productID=productID,
                            sellerID=None,
                            userID=recipient_id,
                            riderID=sender_id
                        )
                if isinstance(saved, dict):
                    saved_id = saved.get('chatID')
                    saved_ts = saved.get('created_at')
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    except Exception:
        try:
            app.logger.exception('Error saving chat message')
        except Exception:
            pass

    # Build a canonical payload using persisted values when available.
    payload = {
        'message': message,
        'messages': message,
        'sender_role': sender_role,
        'senderID': sender_id,
        'recipient_role': recipient_role,
        'recipientID': recipient_id,
        'productID': productID,
        'messageID': saved_id or None,
        'chatID': saved_id or None,
        'created_at': (saved_ts.isoformat() if saved_ts is not None else None),
        # helpful compatibility fields for older clients
        'ts': (saved_ts.isoformat() if saved_ts is not None else datetime.utcnow().isoformat()),
        # include userID / sellerID so clients can rely on explicit ids
        'userID': None,
        'sellerID': None,
        'riderID': None,
        'is_read': 0
    }

    if local_id is not None:
        payload['localId'] = local_id

    # Attach room and validation metadata when provided so clients can
    # understand which canonical 1:1 room this message belongs to and
    # whether the backend validation passed.
    try:
        if room:
            payload['room'] = room
        if isinstance(validation, dict):
            try:
                v = {
                    'ok': bool(validation.get('ok')),
                    'reason': validation.get('reason'),
                    'kind': validation.get('kind'),
                    'room': validation.get('room') or room,
                }
            except Exception:
                v = {
                    'ok': bool(validation.get('ok')),
                    'reason': validation.get('reason'),
                }
            payload['validation'] = v
    except Exception:
        try:
            app.logger.debug('failed to attach validation metadata to payload', exc_info=True)
        except Exception:
            pass

    # Populate userID/sellerID according to sender/recipient mapping and parameters
    try:
        if recipient_role == 'user':
            payload['userID'] = int(recipient_id) if str(recipient_id).isdigit() else recipient_id
            # seller might be the sender
            if sender_role == 'seller':
                payload['sellerID'] = int(sender_id) if str(sender_id).isdigit() else sender_id
        elif recipient_role == 'seller':
            payload['sellerID'] = int(recipient_id) if str(recipient_id).isdigit() else recipient_id
            if sender_role == 'user':
                payload['userID'] = int(sender_id) if str(sender_id).isdigit() else sender_id
        elif recipient_role == 'rider':
            payload['riderID'] = int(recipient_id) if str(recipient_id).isdigit() else recipient_id
            if sender_role == 'seller':
                payload['sellerID'] = int(sender_id) if str(sender_id).isdigit() else sender_id
            elif sender_role == 'user':
                payload['userID'] = int(sender_id) if str(sender_id).isdigit() else sender_id
        
        # Add riderID to payload when rider is sender
        if sender_role == 'rider':
            payload['riderID'] = int(sender_id) if str(sender_id).isdigit() else sender_id

        # If the save helper returned an inserted id, and the chats table contains userID/sellerID,
        # try to reflect the values passed into save_chat_message
        if isinstance(saved, dict):
            # saved may include created_at already
            if saved.get('created_at') and not payload.get('created_at'):
                try:
                    payload['created_at'] = saved.get('created_at').isoformat() if hasattr(saved.get('created_at'), 'isoformat') else str(saved.get('created_at'))
                except Exception:
                    payload['created_at'] = str(saved.get('created_at'))
            # is_read defaults to 0
            payload['is_read'] = 0
    except Exception:
        try:
            app.logger.exception('Error populating payload user/seller ids')
        except Exception:
            pass

    # Emit to recipient's sids if online
    try:
        recipient_key = f"{recipient_role}:{recipient_id}"
        sids = connected_users.get(recipient_key) or set()
        for sid in list(sids):
            try:
                socketio.emit('chat_message', payload, to=sid)
            except Exception:
                pass
        try:
            app.logger.info(f"send_chat_message: recipient_key={recipient_key} sids_found={len(sids)} saved_id={saved_id}")
        except Exception:
            pass
    except Exception:
        try:
            app.logger.exception('Failed to emit to recipient')
        except Exception:
            pass

    # Also echo back to sender's sockets so their UI can reflect message
    try:
        sender_key = f"{sender_role}:{sender_id}"
        sids = connected_users.get(sender_key) or set()
        for sid in list(sids):
            try:
                socketio.emit('chat_message', payload, to=sid)
            except Exception:
                pass
        try:
            app.logger.info(f"send_chat_message: echoed to sender_key={sender_key} sids_found={len(sids)}")
        except Exception:
            pass
    except Exception:
        try:
            app.logger.exception('Failed to emit to sender')
        except Exception:
            pass

    return payload


@socketio.on('chat_message')
def _on_chat_message(data):
    """Handle incoming private chat messages.

    Expected data (from client): {
        message: 'text',
        sellerID: 123,          # when user is sending
        userID: 456,            # when seller is sending
        productID: 789 (optional)
    }
    The server derives sender identity from the socket's JWT cookie.
    """
    if not isinstance(data, dict):
        return
    message = data.get('message')
    # Normalize incoming keys (accept both product_id/productID and seller_id/sellerID and user_id/userID)
    productID = data.get('productID') or data.get('product_id')
    sellerID = data.get('sellerID') or data.get('seller_id')
    userID = data.get('userID') or data.get('user_id')
    riderID = data.get('riderID') or data.get('rider_id')
    local_id = data.get('localId') or data.get('local_id')

    # Ensure productID aligns with legacy schema (numeric columns)
    if productID is not None:
        try:
            product_str = str(productID).strip()
            if product_str.isdigit():
                productID = int(product_str)
            else:
                productID = None
        except Exception:
            productID = None
    if not message:
        return

    # Derive sender identity from socket authentication (do NOT trust client-provided senderID)
    sender_role, sender_ident = _get_identity_from_socket()
    if not sender_role or not sender_ident:
        return

    # Determine recipient: if sender is user -> recipient is seller (sellerID must be present)
    recipient_role = None
    recipient_ident = None
    if sender_role == 'user':
        if not sellerID:
            return
        recipient_role = 'seller'
        recipient_ident = str(sellerID)
    elif sender_role == 'seller':
        # seller must send userID in payload so we can route to the correct user
        if userID:
            recipient_role = 'user'
            recipient_ident = str(userID)
        elif riderID:
            recipient_role = 'rider'
            recipient_ident = str(riderID)
        else:
            return
    elif sender_role == 'rider':
        if sellerID:
            recipient_role = 'seller'
            recipient_ident = str(sellerID)
        elif userID:
            recipient_role = 'user'
            recipient_ident = str(userID)
        else:
            return
    else:
        return

    # Validate the requested chat pair against order/product rules and
    # compute the canonical room name.
    validation = None
    room_name = None
    try:
        validation = _validate_legacy_chat_pair(sender_role, sender_ident, recipient_role, recipient_ident, productID)
        if isinstance(validation, dict):
            room_name = validation.get('room')
    except Exception:
        try:
            app.logger.exception('legacy chat validation failed')
        except Exception:
            pass
        validation = None

    if validation and not validation.get('ok'):
        try:
            socketio.emit(
                'system',
                {
                    'type': 'chat_validation_failed',
                    'ok': False,
                    'reason': validation.get('reason'),
                    'kind': validation.get('kind'),
                    'room': room_name,
                    'sender_role': sender_role,
                    'sender_id': sender_ident,
                    'recipient_role': recipient_role,
                    'recipient_id': recipient_ident,
                    'productID': productID,
                },
                to=request.sid,
            )
        except Exception:
            pass
        return

    # Join the canonical 1:1 room for this conversation when available.
    try:
        if room_name:
            join_room(room_name)
    except Exception:
        try:
            app.logger.debug('failed to join canonical chat room', exc_info=True)
        except Exception:
            pass

    # Persist and emit privately
    try:
        send_chat_message(
            sender_role,
            sender_ident,
            recipient_role,
            recipient_ident,
            message,
            productID=productID,
            room=room_name,
            validation=validation,
            local_id=local_id,
        )
    except Exception:
        try:
            app.logger.exception('Failed in send_chat_message')
        except Exception:
            pass


@app.route('/api/chat/history')
def api_chat_history():
    """Return recent chat history. Query params: sellerID, userID, riderID, productID, limit"""
    sellerID = request.args.get('sellerID') or request.args.get('seller_id')
    userID = request.args.get('userID') or request.args.get('user_id')
    riderID = request.args.get('riderID') or request.args.get('rider_id')
    productID = request.args.get('productID') or request.args.get('product_id')
    limit = request.args.get('limit', 50)
    try:
        sellerID = int(sellerID) if sellerID is not None and sellerID != '' else None
    except Exception:
        sellerID = None
    try:
        userID = int(userID) if userID is not None and userID != '' else None
    except Exception:
        userID = None
    try:
        riderID = int(riderID) if riderID is not None and riderID != '' else None
    except Exception:
        riderID = None
    try:
        productID = int(productID) if productID is not None and productID != '' else None
    except Exception:
        productID = None
    try:
        limit = int(limit)
    except Exception:
        limit = 50

    # When both sides of a conversation are specified, validate that the
    # pair is allowed and, when applicable, that the order/product
    # relationship is correct. This mirrors the Socket.IO validation but
    # is safe to skip when only a single id is provided (old callers).
    validation = None
    room_name = None
    try:
        if userID is not None and sellerID is not None:
            validation = _validate_legacy_chat_pair('user', userID, 'seller', sellerID, productID)
        elif riderID is not None and sellerID is not None:
            validation = _validate_legacy_chat_pair('rider', riderID, 'seller', sellerID, productID)
        elif riderID is not None and userID is not None:
            validation = _validate_legacy_chat_pair('rider', riderID, 'user', userID, productID)
        if isinstance(validation, dict):
            room_name = validation.get('room')
    except Exception:
        try:
            app.logger.exception('chat history validation failed')
        except Exception:
            pass
        validation = validation or None

    if validation and not validation.get('ok'):
        return jsonify({
            'success': False,
            'msg': 'chat_validation_failed',
            'reason': validation.get('reason'),
            'validation': validation,
        }), 403

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        # Check which columns exist in chats table
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM chats")
            chat_cols = [r[0] for r in meta.fetchall()]
            meta.close()
        except Exception:
            chat_cols = []
        
        has_riderID = 'riderID' in chat_cols
        has_sender_role = 'sender_role' in chat_cols

        if riderID is not None and not has_riderID:
            schema_cur = None
            try:
                schema_cur = conn.cursor()
                schema_cur.execute("ALTER TABLE chats ADD COLUMN riderID INT NULL AFTER sellerID")
                try:
                    schema_cur.close()
                except Exception:
                    pass
                chat_cols.append('riderID')
                has_riderID = True
            except Exception:
                try:
                    if schema_cur:
                        schema_cur.close()
                except Exception:
                    pass
                # leave has_riderID as False; fallback logic below will handle filtering
                pass
        
        # Fetch chat history - support sellerID, userID, and riderID
        cur = conn.cursor(dictionary=True)
        clauses = []
        params = []
        if sellerID is not None:
            clauses.append('sellerID = %s')
            params.append(sellerID)
        if userID is not None:
            clauses.append('userID = %s')
            params.append(userID)
        if productID is not None:
            # support both productID and sellerOrderID/orderID columns in chats
            if 'productID' in chat_cols:
                clauses.append('productID = %s')
                params.append(productID)
            elif 'sellerOrderID' in chat_cols:
                clauses.append('sellerOrderID = %s')
                params.append(productID)
            elif 'orderID' in chat_cols:
                clauses.append('orderID = %s')
                params.append(productID)
        if riderID is not None:
            if has_riderID:
                clauses.append('riderID = %s')
                params.append(riderID)
            elif has_sender_role:
                # Fallback: sender_role records both sides of the rider conversation when riderID column is missing
                clauses.append('(sender_role = %s OR sender_role = %s)')
                params.extend(['rider', 'seller'])
                if 'userID' in chat_cols:
                    clauses.append('(userID IS NULL OR userID = 0)')
        
        if not clauses:
            return jsonify({'success': False, 'msg': 'Must provide sellerID, userID, or riderID'}), 400
        
        sql = 'SELECT * FROM chats WHERE ' + ' AND '.join(clauses) + ' ORDER BY chatID ASC LIMIT %s'
        params.append(limit)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []
        cur.close()
        return jsonify({'success': True, 'messages': rows, 'room': room_name, 'validation': validation}), 200
    except Exception:
        try:
            app.logger.exception('Failed to fetch chat history')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to fetch chat history'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/notifications')
def api_notifications():
    """Return recent unread chat notifications for the authenticated user.

    Response: { success: True, notifications: [ { sellerID, sellerName, unreadCount, lastMessage, productID, last_ts } ] }
    """
    # Derive user identity from session or JWT cookie
    user = None
    try:
        user = session.get('user')
    except Exception:
        user = None

    if not user or not (user.get('userID') or user.get('id')):
        # attempt to decode from access_token cookie
        try:
            token = request.cookies.get('access_token')
            if token:
                decoded = decode_token(token)
                ident = extract_identity_from_decoded(decoded)
                if isinstance(ident, dict) and (ident.get('userID') or ident.get('id')):
                    user = {'userID': ident.get('userID') or ident.get('id')}
        except Exception:
            user = None

    if not user or not user.get('userID'):
        return jsonify({'success': False, 'msg': 'Not authenticated as user'}), 401

    user_id = user.get('userID')
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500

    try:
        cur = conn.cursor(dictionary=True)
        # Check for schema features (is_read, sender_role, productID)
        try:
            meta = conn.cursor()
            meta.execute('SHOW COLUMNS FROM chats')
            cols = [r[0] for r in meta.fetchall()]
            try: meta.close()
            except Exception: pass
        except Exception:
            cols = []

        notifications = []
        has_is_read = ('is_read' in cols)
        has_sender_role = ('sender_role' in cols)
        has_product_id = ('productID' in cols)
        if has_is_read and has_sender_role:
            # Group unread messages from sellers by sellerID and return latest message per seller
            product_fragment = (
                "SUBSTRING_INDEX(GROUP_CONCAT(productID ORDER BY created_at DESC SEPARATOR ','), ',', 1) AS productID "
                if has_product_id else
                "NULL AS productID "
            )
            sql = (
                "SELECT sellerID, COUNT(*) AS unreadCount, MAX(created_at) AS last_ts, "
                "SUBSTRING_INDEX(GROUP_CONCAT(messages ORDER BY created_at DESC SEPARATOR '||'), '||', 1) AS lastMessage, "
                + product_fragment +
                "FROM chats "
                "WHERE userID = %s AND sender_role = 'seller' AND is_read = 0 "
                "GROUP BY sellerID "
                "ORDER BY last_ts DESC LIMIT 50"
            )
            cur.execute(sql, (user_id,))
            rows = cur.fetchall() or []
            # Optionally resolve seller name for each sellerID
            for r in rows:
                seller_id = r.get('sellerID')
                last_msg = r.get('lastMessage')
                product_id = r.get('productID')
                unread = int(r.get('unreadCount') or 0)
                last_ts = r.get('last_ts')
                seller_name = None
                try:
                    if seller_id:
                        scur = conn.cursor(dictionary=True)
                        scur.execute("SELECT storename, sellername, selleremail FROM sellers WHERE sellerID = %s OR id = %s LIMIT 1", (seller_id, seller_id))
                        srow = scur.fetchone()
                        try: scur.close()
                        except Exception: pass
                        if srow:
                            seller_name = srow.get('storename') or srow.get('sellername') or srow.get('selleremail')
                except Exception:
                    seller_name = None

                notifications.append({
                    'sellerID': seller_id,
                    'sellerName': seller_name,
                    'unreadCount': unread,
                    'lastMessage': last_msg,
                    'productID': product_id,
                    'last_ts': last_ts
                })
        else:
            # Fallback: fetch latest messages addressed to this user and treat them as notifications
            try:
                rows = chat.get_chat_history(conn, userID=user_id, limit=50) or []
                # group by sellerID and count entries
                grouped = {}
                for m in rows:
                    try:
                        sid = m.get('sellerID')
                        if not sid:
                            continue
                        g = grouped.setdefault(sid, {'sellerID': sid, 'unreadCount': 0, 'lastMessage': None, 'productID': m.get('productID'), 'last_ts': m.get('created_at')})
                        # treat messages originating from seller as unread (best-effort)
                        # if schema lacks is_read we cannot know read status, so include recent messages
                        g['unreadCount'] = g.get('unreadCount', 0) + 1
                        if not g.get('lastMessage') or (m.get('created_at') and m.get('created_at') > g.get('last_ts')):
                            g['lastMessage'] = m.get('messages') or m.get('message')
                            g['last_ts'] = m.get('created_at')
                    except Exception:
                        continue
                # resolve seller names
                for sid, val in grouped.items():
                    seller_name = None
                    try:
                        scur = conn.cursor(dictionary=True)
                        scur.execute("SELECT storename, sellername, selleremail FROM sellers WHERE sellerID = %s OR id = %s LIMIT 1", (sid, sid))
                        srow = scur.fetchone()
                        try: scur.close()
                        except Exception: pass
                        if srow:
                            seller_name = srow.get('storename') or srow.get('sellername') or srow.get('selleremail')
                    except Exception:
                        seller_name = None
                    notifications.append({
                        'sellerID': sid,
                        'sellerName': seller_name,
                        'unreadCount': int(val.get('unreadCount') or 0),
                        'lastMessage': val.get('lastMessage'),
                        'productID': val.get('productID'),
                        'last_ts': val.get('last_ts')
                    })
            
            
            
            except Exception:
                # Fallback retrieval failed; continue with whatever notifications gathered so far
                try:
                    app.logger.debug('Fallback notifications retrieval failed')
                except Exception:
                    pass

        # Also fetch system notifications for this user from the notifications table
        system_notifications = []
        try:
            meta2 = conn.cursor()
            meta2.execute('SHOW COLUMNS FROM notifications')
            ncols = [r[0] for r in meta2.fetchall()]
            try:
                meta2.close()
            except Exception:
                pass
        except Exception:
            ncols = []

        try:
            ncur = conn.cursor(dictionary=True)
            id_col2 = 'notificationID' if 'notificationID' in ncols else 'id'
            ncur.execute(f"""
                SELECT {id_col2} AS notificationID, title, body, created_at, is_read
                FROM notifications
                WHERE recipient_type = 'user' AND recipient_id = %s
                ORDER BY created_at DESC
                LIMIT 20
            """, (user_id,))
            system_notifications = ncur.fetchall() or []
            try:
                ncur.close()
            except Exception:
                pass
        except Exception:
            system_notifications = []

        try:
            cur.close()
        except Exception:
            pass
        return jsonify({'success': True, 'notifications': notifications, 'system_notifications': system_notifications}), 200
    except Exception as e:
        try:
            app.logger.exception('Failed to fetch notifications')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to fetch notifications'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/seller/chat/conversations')
def api_seller_chat_conversations():
    """Return a list of conversations for the authenticated seller.

    Response: { success: True, conversations: [ { userID, username, lastMessage, lastChatID } ] }
    """
    # Use the shared helper which already understands both the Authorization
    # header (mobile) and the cookie/session (web).
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return jsonify({'success': False, 'msg': 'Not authenticated as seller'}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Check which columns exist in chats table
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM chats")
            chat_cols = [r[0] for r in meta.fetchall()]
            meta.close()
        except Exception:
            chat_cols = []
        
        has_is_read = 'is_read' in chat_cols
        has_sender_role = 'sender_role' in chat_cols
        has_rider_id = 'riderID' in chat_cols

        product_cols = [col for col in ('productID', 'sellerOrderID', 'orderID') if col in chat_cols]
        if product_cols:
            product_expr_c1 = 'COALESCE(' + ', '.join(f'c1.{col}' for col in product_cols) + ')'
            user_last_product_clause = f"{product_expr_c1} AS lastProductID"
        else:
            product_expr_c1 = None
            user_last_product_clause = "NULL AS lastProductID"

        # Build query based on available columns
        if has_is_read and has_sender_role:
            sql = (
                "SELECT c1.chatID AS lastChatID, c1.userID, u.username, c1.messages AS lastMessage, "
                f"{user_last_product_clause}, "
                "(SELECT COUNT(*) FROM chats WHERE sellerID = %s AND userID = c1.userID AND sender_role = 'user' AND is_read = 0) AS unreadCount "
                "FROM chats c1 "
                "JOIN (SELECT userID, MAX(chatID) AS last_chat FROM chats WHERE sellerID = %s AND userID > 0 GROUP BY userID) c2 "
                "ON c1.userID = c2.userID AND c1.chatID = c2.last_chat "
                "LEFT JOIN users u ON u.userID = c1.userID "
                "ORDER BY c1.chatID DESC"
            )
        elif has_sender_role:
            sql = (
                "SELECT c1.chatID AS lastChatID, c1.userID, u.username, c1.messages AS lastMessage, "
                f"{user_last_product_clause}, "
                "(SELECT COUNT(*) FROM chats WHERE sellerID = %s AND userID = c1.userID AND sender_role = 'user') AS unreadCount "
                "FROM chats c1 "
                "JOIN (SELECT userID, MAX(chatID) AS last_chat FROM chats WHERE sellerID = %s AND userID > 0 GROUP BY userID) c2 "
                "ON c1.userID = c2.userID AND c1.chatID = c2.last_chat "
                "LEFT JOIN users u ON u.userID = c1.userID "
                "ORDER BY c1.chatID DESC"
            )
        else:
            # Fallback: no sender_role or is_read columns
            sql = (
                "SELECT c1.chatID AS lastChatID, c1.userID, u.username, c1.messages AS lastMessage, "
                f"{user_last_product_clause}, "
                "0 AS unreadCount "
                "FROM chats c1 "
                "JOIN (SELECT userID, MAX(chatID) AS last_chat FROM chats WHERE sellerID = %s AND userID > 0 GROUP BY userID) c2 "
                "ON c1.userID = c2.userID AND c1.chatID = c2.last_chat "
                "LEFT JOIN users u ON u.userID = c1.userID "
                "ORDER BY c1.chatID DESC"
            )
        cur.execute(sql, (seller_id, seller_id))
        rows = cur.fetchall() or []
        try:
            cur.close()
        except Exception:
            pass
        # Normalize rows
        convos = []
        for r in rows:
            convos.append({
                'type': 'user',
                'id': r.get('userID'),
                'userID': r.get('userID'),
                'name': r.get('username') or f'User {r.get("userID")}',
                'lastMessage': r.get('lastMessage'),
                'lastChatID': r.get('lastChatID'),
                'lastProductID': r.get('lastProductID'),
                'unreadCount': int(r.get('unreadCount') or 0)
            })

        # Include rider conversations when schema supports riderID
        if has_rider_id:
            try:
                cur = conn.cursor(dictionary=True)
                rider_last_product_clause = user_last_product_clause if product_expr_c1 else "NULL AS lastProductID"
                if has_sender_role and has_is_read:
                    rider_sql = (
                        "SELECT c1.chatID AS lastChatID, c1.riderID, r.ridername, c1.messages AS lastMessage, "
                        f"{rider_last_product_clause}, "
                        "(SELECT COUNT(*) FROM chats WHERE sellerID = %s AND riderID = c1.riderID AND sender_role = 'rider' AND (is_read = 0 OR is_read IS NULL)) AS unreadCount "
                        "FROM chats c1 "
                        "JOIN (SELECT riderID, MAX(chatID) AS last_chat FROM chats WHERE sellerID = %s AND riderID > 0 GROUP BY riderID) c2 "
                        "ON c1.riderID = c2.riderID AND c1.chatID = c2.last_chat "
                        "LEFT JOIN riders r ON r.riderID = c1.riderID "
                        "WHERE c1.sellerID = %s AND c1.riderID > 0 "
                        "ORDER BY c1.chatID DESC"
                    )
                    cur.execute(rider_sql, (seller_id, seller_id, seller_id))
                elif has_sender_role:
                    rider_sql = (
                        "SELECT c1.chatID AS lastChatID, c1.riderID, r.ridername, c1.messages AS lastMessage, "
                        f"{rider_last_product_clause}, "
                        "0 AS unreadCount "
                        "FROM chats c1 "
                        "JOIN (SELECT riderID, MAX(chatID) AS last_chat FROM chats WHERE sellerID = %s AND riderID > 0 GROUP BY riderID) c2 "
                        "ON c1.riderID = c2.riderID AND c1.chatID = c2.last_chat "
                        "LEFT JOIN riders r ON r.riderID = c1.riderID "
                        "WHERE c1.sellerID = %s AND c1.riderID > 0 "
                        "ORDER BY c1.chatID DESC"
                    )
                    cur.execute(rider_sql, (seller_id, seller_id))
                else:
                    rider_sql = (
                        "SELECT c1.chatID AS lastChatID, c1.riderID, r.ridername, c1.messages AS lastMessage, "
                        f"{rider_last_product_clause}, "
                        "0 AS unreadCount "
                        "FROM chats c1 "
                        "JOIN (SELECT riderID, MAX(chatID) AS last_chat FROM chats WHERE sellerID = %s AND riderID > 0 GROUP BY riderID) c2 "
                        "ON c1.riderID = c2.riderID AND c1.chatID = c2.last_chat "
                        "LEFT JOIN riders r ON r.riderID = c1.riderID "
                        "WHERE c1.sellerID = %s AND c1.riderID > 0 "
                        "ORDER BY c1.chatID DESC"
                    )
                    cur.execute(rider_sql, (seller_id, seller_id))

                rider_rows = cur.fetchall() or []
                for r in rider_rows:
                    convos.append({
                        'type': 'rider',
                        'id': r.get('riderID'),
                        'riderID': r.get('riderID'),
                        'name': r.get('ridername') or f'Rider {r.get("riderID")}',
                        'lastMessage': r.get('lastMessage'),
                        'lastChatID': r.get('lastChatID'),
                        'lastProductID': r.get('lastProductID'),
                        'unreadCount': int(r.get('unreadCount') or 0)
                    })
                try:
                    cur.close()
                except Exception:
                    pass
            except Exception:
                try:
                    cur.close()
                except Exception:
                    pass

        return jsonify({'success': True, 'conversations': convos}), 200
    except Exception:
        try:
            app.logger.exception('Failed to fetch seller conversations')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to fetch conversations'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/rider/chat/conversations')
@rider_required
def api_rider_chat_conversations():
    """Return list of conversations (sellers and users) for the authenticated rider."""
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        conversations = []
        
        # Check which columns exist in chats table
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM chats")
            chat_cols = [r[0] for r in meta.fetchall()]
            meta.close()
        except Exception:
            chat_cols = []
        
        has_riderID = 'riderID' in chat_cols
        has_sender_role = 'sender_role' in chat_cols
        has_is_read = 'is_read' in chat_cols

        product_cols = []
        for col in ('productID', 'sellerOrderID', 'orderID'):
            if col in chat_cols:
                product_cols.append(col)
        product_expr = f"COALESCE({', '.join(product_cols)})" if product_cols else None

        # Attempt to add riderID column automatically when missing so rider conversations work with older databases
        if not has_riderID:
            schema_cur = None
            try:
                schema_cur = conn.cursor()
                schema_cur.execute("ALTER TABLE chats ADD COLUMN riderID INT NULL AFTER sellerID")
                conn.commit()
                chat_cols.append('riderID')
                has_riderID = True
                try:
                    schema_cur.close()
                except Exception:
                    pass
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                if schema_cur is not None:
                    try:
                        schema_cur.close()
                    except Exception:
                        pass
        
        # Build seller conversations query based on available columns
        if product_expr:
            seller_last_product_clause_rider = f"(SELECT {product_expr} FROM chats WHERE sellerID = c.sellerID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastProductID"
            seller_last_product_clause_sender = f"(SELECT {product_expr} FROM chats WHERE sellerID = c.sellerID AND sender_role = 'rider' ORDER BY chatID DESC LIMIT 1) as lastProductID"
        else:
            seller_last_product_clause_rider = "NULL as lastProductID"
            seller_last_product_clause_sender = "NULL as lastProductID"

        if has_riderID and has_sender_role and has_is_read:
            seller_sql = f"""
                SELECT DISTINCT c.sellerID as id, s.sellername as name, s.storename,
                       (SELECT messages FROM chats WHERE sellerID = c.sellerID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE sellerID = c.sellerID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {seller_last_product_clause_rider},
                       (SELECT COUNT(*) FROM chats WHERE sellerID = c.sellerID AND riderID = %s AND (is_read = 0 OR is_read IS NULL) AND sender_role != 'rider') as unreadCount
                FROM chats c
                LEFT JOIN sellers s ON c.sellerID = s.sellerID
                WHERE c.riderID = %s AND c.sellerID IS NOT NULL
                GROUP BY c.sellerID, s.sellername, s.storename
                ORDER BY lastChatID DESC
            """
        elif has_riderID and has_sender_role:
            seller_sql = f"""
                SELECT DISTINCT c.sellerID as id, s.sellername as name, s.storename,
                       (SELECT messages FROM chats WHERE sellerID = c.sellerID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE sellerID = c.sellerID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {seller_last_product_clause_rider},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN sellers s ON c.sellerID = s.sellerID
                WHERE c.riderID = %s AND c.sellerID IS NOT NULL
                GROUP BY c.sellerID, s.sellername, s.storename
                ORDER BY lastChatID DESC
            """
        elif has_riderID:
            seller_sql = f"""
                SELECT DISTINCT c.sellerID as id, s.sellername as name, s.storename,
                       (SELECT messages FROM chats WHERE sellerID = c.sellerID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE sellerID = c.sellerID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {seller_last_product_clause_rider},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN sellers s ON c.sellerID = s.sellerID
                WHERE c.riderID = %s AND c.sellerID IS NOT NULL
                GROUP BY c.sellerID, s.sellername, s.storename
                ORDER BY lastChatID DESC
            """
        elif has_sender_role:
            seller_sql = f"""
                SELECT DISTINCT c.sellerID as id, s.sellername as name, s.storename,
                       (SELECT messages FROM chats WHERE sellerID = c.sellerID AND sender_role = 'rider' ORDER BY chatID DESC LIMIT 1) as lastMessage,
                      (SELECT chatID FROM chats WHERE sellerID = c.sellerID AND sender_role = 'rider' ORDER BY chatID DESC LIMIT 1) as lastChatID,
                      {seller_last_product_clause_sender},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN sellers s ON c.sellerID = s.sellerID
                WHERE c.sender_role = 'rider' AND c.sellerID IS NOT NULL
                GROUP BY c.sellerID, s.sellername, s.storename
                ORDER BY lastChatID DESC
            """
        else:
            # Fallback: no riderID or sender_role columns
            seller_sql = f"""
                SELECT DISTINCT c.sellerID as id, s.sellername as name, s.storename,
                       (SELECT messages FROM chats WHERE sellerID = c.sellerID ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE sellerID = c.sellerID ORDER BY chatID DESC LIMIT 1) as lastChatID,
                      {'NULL as lastProductID' if not product_expr else f"(SELECT {product_expr} FROM chats WHERE sellerID = c.sellerID ORDER BY chatID DESC LIMIT 1) as lastProductID"},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN sellers s ON c.sellerID = s.sellerID
                WHERE c.sellerID IS NOT NULL
                GROUP BY c.sellerID, s.sellername, s.storename
                ORDER BY lastChatID DESC
            """
        
        if has_riderID and has_sender_role and has_is_read:
            seller_params_list = [rider_id, rider_id]
            if product_expr:
                seller_params_list.append(rider_id)
            seller_params_list.extend([rider_id, rider_id])
            seller_params = tuple(seller_params_list)
        elif has_riderID and has_sender_role:
            seller_params_list = [rider_id, rider_id]
            if product_expr:
                seller_params_list.append(rider_id)
            seller_params_list.append(rider_id)
            seller_params = tuple(seller_params_list)
        elif has_riderID:
            seller_params_list = [rider_id, rider_id]
            if product_expr:
                seller_params_list.append(rider_id)
            seller_params_list.append(rider_id)
            seller_params = tuple(seller_params_list)
        else:
            seller_params = ()

        cur.execute(seller_sql, seller_params)
        seller_convos = cur.fetchall() or []
        for c in seller_convos:
            conversations.append({
                'type': 'seller',
                'id': c['id'],
                'name': c['name'] or c.get('storename') or f"Seller {c['id']}",
                'lastMessage': c.get('lastMessage') or '',
                'lastChatID': c.get('lastChatID'),
                'lastProductID': c.get('lastProductID'),
                'unreadCount': c.get('unreadCount') or 0
            })
        
        # Build user conversations query based on available columns
        if product_expr:
            user_last_product_clause_rider = f"(SELECT {product_expr} FROM chats WHERE userID = c.userID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastProductID"
            user_last_product_clause_sender = f"(SELECT {product_expr} FROM chats WHERE userID = c.userID AND sender_role = 'rider' ORDER BY chatID DESC LIMIT 1) as lastProductID"
        else:
            user_last_product_clause_rider = "NULL as lastProductID"
            user_last_product_clause_sender = "NULL as lastProductID"

        if has_riderID and has_sender_role and has_is_read:
            user_sql = f"""
                SELECT DISTINCT c.userID as id, u.username as name,
                       (SELECT messages FROM chats WHERE userID = c.userID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE userID = c.userID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {user_last_product_clause_rider},
                       (SELECT COUNT(*) FROM chats WHERE userID = c.userID AND riderID = %s AND (is_read = 0 OR is_read IS NULL) AND sender_role != 'rider') as unreadCount
                FROM chats c
                LEFT JOIN users u ON c.userID = u.userID
                WHERE c.riderID = %s AND c.userID IS NOT NULL
                GROUP BY c.userID, u.username
                ORDER BY lastChatID DESC
            """
        elif has_riderID and has_sender_role:
            user_sql = f"""
                SELECT DISTINCT c.userID as id, u.username as name,
                       (SELECT messages FROM chats WHERE userID = c.userID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE userID = c.userID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {user_last_product_clause_rider},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN users u ON c.userID = u.userID
                WHERE c.riderID = %s AND c.userID IS NOT NULL
                GROUP BY c.userID, u.username
                ORDER BY lastChatID DESC
            """
        elif has_riderID:
            user_sql = f"""
                SELECT DISTINCT c.userID as id, u.username as name,
                       (SELECT messages FROM chats WHERE userID = c.userID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE userID = c.userID AND riderID = %s ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {user_last_product_clause_rider},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN users u ON c.userID = u.userID
                WHERE c.riderID = %s AND c.userID IS NOT NULL
                GROUP BY c.userID, u.username
                ORDER BY lastChatID DESC
            """
        elif has_sender_role:
            user_sql = f"""
                SELECT DISTINCT c.userID as id, u.username as name,
                       (SELECT messages FROM chats WHERE userID = c.userID AND sender_role = 'rider' ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE userID = c.userID AND sender_role = 'rider' ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {user_last_product_clause_sender},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN users u ON c.userID = u.userID
                WHERE c.sender_role = 'rider' AND c.userID IS NOT NULL
                GROUP BY c.userID, u.username
                ORDER BY lastChatID DESC
            """
        else:
            # Fallback: no riderID or sender_role columns
            user_sql = f"""
                SELECT DISTINCT c.userID as id, u.username as name,
                       (SELECT messages FROM chats WHERE userID = c.userID ORDER BY chatID DESC LIMIT 1) as lastMessage,
                       (SELECT chatID FROM chats WHERE userID = c.userID ORDER BY chatID DESC LIMIT 1) as lastChatID,
                       {'NULL as lastProductID' if not product_expr else f"(SELECT {product_expr} FROM chats WHERE userID = c.userID ORDER BY chatID DESC LIMIT 1) as lastProductID"},
                       0 as unreadCount
                FROM chats c
                LEFT JOIN users u ON c.userID = u.userID
                WHERE c.userID IS NOT NULL
                GROUP BY c.userID, u.username
                ORDER BY lastChatID DESC
            """
        
        if has_riderID and has_sender_role and has_is_read:
            user_params_list = [rider_id, rider_id]
            if product_expr:
                user_params_list.append(rider_id)
            user_params_list.extend([rider_id, rider_id])
            user_params = tuple(user_params_list)
        elif has_riderID and has_sender_role:
            user_params_list = [rider_id, rider_id]
            if product_expr:
                user_params_list.append(rider_id)
            user_params_list.append(rider_id)
            user_params = tuple(user_params_list)
        elif has_riderID:
            user_params_list = [rider_id, rider_id]
            if product_expr:
                user_params_list.append(rider_id)
            user_params_list.append(rider_id)
            user_params = tuple(user_params_list)
        else:
            user_params = ()

        cur.execute(user_sql, user_params)
        user_convos = cur.fetchall() or []
        for c in user_convos:
            conversations.append({
                'type': 'user',
                'id': c['id'],
                'name': c['name'] or f"User {c['id']}",
                'lastMessage': c.get('lastMessage') or '',
                'lastChatID': c.get('lastChatID'),
                'lastProductID': c.get('lastProductID'),
                'unreadCount': c.get('unreadCount') or 0
            })
        
        # Sort by lastChatID descending
        conversations.sort(key=lambda x: x.get('lastChatID') or 0, reverse=True)
        
        return jsonify({'success': True, 'conversations': conversations}), 200
    except Exception as e:
        try:
            app.logger.exception('Failed to fetch rider conversations')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to fetch conversations'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/rider/notifications')
@rider_required
def api_rider_notifications():
    """Get notifications for the authenticated rider."""
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Check which column name exists (id or notificationID)
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM notifications")
            cols = [r[0] for r in meta.fetchall()]
            meta.close()
        except Exception:
            cols = []
        
        # Use notificationID if available, otherwise id
        id_col = 'notificationID' if 'notificationID' in cols else 'id'
        cur.execute(f"""
            SELECT {id_col} as notificationID, title, body, created_at, is_read
            FROM notifications
            WHERE recipient_type = 'rider' AND recipient_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (rider_id,))
        notifications = cur.fetchall() or []
        return jsonify({'success': True, 'notifications': notifications}), 200
    except Exception as e:
        try:
            app.logger.exception('Failed to fetch rider notifications')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to fetch notifications'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/rider/notifications/mark_read', methods=['POST'])
@rider_required
def api_rider_notifications_mark_read():
    """Mark rider notifications as read. Accepts optional JSON body with ids."""
    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    raw_ids = []
    for key in ('ids', 'notificationIDs', 'notification_ids', 'notificationID', 'id'):
        value = payload.get(key)
        if value is None or value == '':
            continue
        if isinstance(value, (list, tuple, set)):
            raw_ids.extend(value)
        else:
            raw_ids.append(value)

    ids = []
    for item in raw_ids:
        if item is None or item == '':
            continue
        if isinstance(item, str) and ',' in item:
            pieces = [p.strip() for p in item.split(',') if p.strip()]
        else:
            pieces = [item]
        for piece in pieces:
            try:
                ids.append(int(piece))
            except (TypeError, ValueError):
                continue
    # Deduplicate while preserving order
    seen = set()
    ids = [val for val in ids if not (val in seen or seen.add(val))]

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        meta = conn.cursor()
        try:
            meta.execute('SHOW COLUMNS FROM notifications')
            cols = [row[0] for row in meta.fetchall()]
        finally:
            try: meta.close()
            except Exception: pass

        if 'is_read' not in cols:
            # Nothing to update but treat as success so UI doesn't get stuck.
            return jsonify({'success': True, 'updated': 0, 'skipped': True}), 200

        id_col = 'notificationID' if 'notificationID' in cols else 'id'
        updated = 0
        cur = conn.cursor()
        try:
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                query = f"""
                    UPDATE notifications
                    SET is_read = 1
                    WHERE recipient_type = 'rider'
                      AND recipient_id = %s
                      AND {id_col} IN ({placeholders})
                """
                params = [rider_id] + ids
            else:
                query = f"""
                    UPDATE notifications
                    SET is_read = 1
                    WHERE recipient_type = 'rider'
                      AND recipient_id = %s
                      AND (is_read IS NULL OR is_read = 0)
                """
                params = [rider_id]
            cur.execute(query, params)
            conn.commit()
            updated = cur.rowcount or 0
        finally:
            try: cur.close()
            except Exception: pass
        return jsonify({'success': True, 'updated': int(updated)}), 200
    except Exception:
        try:
            app.logger.exception('Failed to mark rider notifications read')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to update notifications'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/seller/notifications')
def api_seller_notifications():
    """Get notifications for the authenticated seller."""
    seller = session.get('seller')
    if not seller:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    seller_id = seller.get('id') or seller.get('sellerID')
    if not seller_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Check which column name exists (id or notificationID)
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM notifications")
            cols = [r[0] for r in meta.fetchall()]
            meta.close()
        except Exception:
            cols = []

        id_col = 'notificationID' if 'notificationID' in cols else 'id'
        cur.execute(f"""
            SELECT {id_col} as notificationID, title, body, is_read, created_at
            FROM notifications
            WHERE recipient_type = 'seller' AND recipient_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (seller_id,))
        notifications = cur.fetchall() or []
        return jsonify({'success': True, 'notifications': notifications}), 200
    except Exception as e:
        try:
            app.logger.exception('Failed to fetch seller notifications')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to fetch notifications'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/seller/notifications/mark_read', methods=['POST'])
def api_seller_notifications_mark_read():
    """Mark all notifications as read for the authenticated seller."""
    seller = session.get('seller')
    if not seller:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    seller_id = seller.get('id') or seller.get('sellerID')
    if not seller_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE recipient_type = 'seller' AND recipient_id = %s AND is_read = 0
        """, (seller_id,))
        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        try:
            app.logger.exception('Failed to mark seller notifications as read')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to mark notifications'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/notifications/mark_read', methods=['POST'])
def api_notifications_mark_read():
    """Mark notifications (chat messages) as read for the authenticated user.

    Accepts optional JSON/form: { sellerID: <id> } to mark only one conversation.
    """
    # derive user identity
    user = None
    try:
        user = session.get('user')
    except Exception:
        user = None
    if not user or not (user.get('userID') or user.get('id')):
        try:
            token = request.cookies.get('access_token')
            if token:
                decoded = decode_token(token)
                ident = extract_identity_from_decoded(decoded)
                if isinstance(ident, dict) and (ident.get('userID') or ident.get('id')):
                    user = {'userID': ident.get('userID') or ident.get('id')}
        except Exception:
            user = None
    if not user or not user.get('userID'):
        return jsonify({'success': False, 'msg': 'Not authenticated as user'}), 401

    user_id = user.get('userID')
    data = request.get_json(silent=True) or request.form or {}
    seller_id = data.get('sellerID') or data.get('seller_id')
    try:
        seller_id = int(seller_id) if seller_id is not None and seller_id != '' else None
    except Exception:
        seller_id = None

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor()
        # detect columns
        try:
            meta = conn.cursor()
            meta.execute('SHOW COLUMNS FROM chats')
            cols = [r[0] for r in meta.fetchall()]
            try: meta.close()
            except Exception: pass
        except Exception:
            cols = []

        # Build update statement conservatively
        if 'is_read' in cols:
            if seller_id:
                sql = "UPDATE chats SET is_read = 1 WHERE userID = %s AND sellerID = %s AND sender_role = 'seller' AND is_read = 0"
                cur.execute(sql, (user_id, seller_id))
            else:
                sql = "UPDATE chats SET is_read = 1 WHERE userID = %s AND sender_role = 'seller' AND is_read = 0"
                cur.execute(sql, (user_id,))
            updated = cur.rowcount
            conn.commit()
            try: cur.close()
            except Exception: pass
            return jsonify({'success': True, 'updated': int(updated)}), 200
        else:
            # If schema lacks is_read, nothing to mark
            try: cur.close()
            except Exception: pass
            return jsonify({'success': False, 'msg': 'Schema does not support marking read'}), 400
    except Exception:
        try: conn.rollback()
        except Exception: pass
        try:
            app.logger.exception('Failed to mark notifications read')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to mark read'}), 500
    finally:
        try: conn.close()
        except Exception: pass

@app.route('/api/chat/mark_read', methods=['POST'])
def api_chat_mark_read():
    """Mark messages as read for authenticated user (seller, rider, or user) viewing a conversation.

    Expects JSON body or form: { userID: <id>, sellerID: <id>, riderID: <id> } (depending on role)
    Requires authentication (session or access_token cookie).
    Returns { success: True, updated: <num_rows> }
    """
    # Determine authenticated role
    role = None
    role_id = None
    
    # Check seller
    seller = session.get('seller')
    if seller and (seller.get('sellerID') or seller.get('id')):
        role = 'seller'
        role_id = seller.get('sellerID') or seller.get('id')
    
    # Check rider
    if not role:
        rider = session.get('rider')
        if rider and (rider.get('riderID') or rider.get('id')):
            role = 'rider'
            role_id = rider.get('riderID') or rider.get('id')
    
    # Check user
    if not role:
        user = session.get('user')
        if user and (user.get('userID') or user.get('id')):
            role = 'user'
            role_id = user.get('userID') or user.get('id')
    
    # Try token if session didn't work
    if not role:
        try:
            token = request.cookies.get('access_token')
            if token:
                decoded = decode_token(token)
                ident = extract_identity_from_decoded(decoded)
                if isinstance(ident, dict):
                    if ident.get('sellerID'):
                        role = 'seller'
                        role_id = ident.get('sellerID')
                    elif ident.get('riderID'):
                        role = 'rider'
                        role_id = ident.get('riderID')
                    elif ident.get('userID'):
                        role = 'user'
                        role_id = ident.get('userID')
        except Exception:
            pass

    if not role or not role_id:
        return jsonify({'success': False, 'msg': 'Not authenticated'}), 401

    data = request.get_json(silent=True) or request.form or {}
    user_id = data.get('userID') or data.get('user_id')
    seller_id = data.get('sellerID') or data.get('seller_id')
    rider_id = data.get('riderID') or data.get('rider_id')
    
    try:
        user_id = int(user_id) if user_id is not None and user_id != '' else None
    except Exception:
        user_id = None
    try:
        seller_id = int(seller_id) if seller_id is not None and seller_id != '' else None
    except Exception:
        seller_id = None
    try:
        rider_id = int(rider_id) if rider_id is not None and rider_id != '' else None
    except Exception:
        rider_id = None

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor()
        # Check column presence
        try:
            meta = conn.cursor()
            meta.execute('SHOW COLUMNS FROM chats')
            cols = [r[0] for r in meta.fetchall()]
            meta.close()
        except Exception:
            cols = []

        if 'is_read' not in cols:
            cur.close()
            return jsonify({'success': False, 'msg': 'is_read column not present'}), 500

        has_sender_role = 'sender_role' in cols
        has_riderID = 'riderID' in cols
        
        updated = 0
        
        # Build SQL based on role and available columns
        # Use direct updates similar to chat_controller to be robust
        
        if role == 'seller' and user_id:
            # Mark messages from user to seller as read
            sql = "UPDATE chats SET is_read = 1 WHERE sellerID = %s AND userID = %s AND sender_role = 'user' AND is_read = 0"
            cur.execute(sql, (role_id, user_id))
            updated = cur.rowcount
        elif role == 'seller' and rider_id:
             # Mark messages from rider to seller as read
            sql = "UPDATE chats SET is_read = 1 WHERE sellerID = %s AND riderID = %s AND sender_role = 'rider' AND is_read = 0"
            cur.execute(sql, (role_id, rider_id))
            updated = cur.rowcount
        elif role == 'rider':
            # Mark messages from seller/user to rider as read
            if seller_id:
                sql = "UPDATE chats SET is_read = 1 WHERE riderID = %s AND sellerID = %s AND sender_role = 'seller' AND is_read = 0"
                cur.execute(sql, (role_id, seller_id))
                updated = cur.rowcount
            elif user_id:
                sql = "UPDATE chats SET is_read = 1 WHERE riderID = %s AND userID = %s AND sender_role = 'user' AND is_read = 0"
                cur.execute(sql, (role_id, user_id))
                updated = cur.rowcount
        elif role == 'user' and seller_id:
            # Mark messages from seller to user as read
            sql = "UPDATE chats SET is_read = 1 WHERE userID = %s AND sellerID = %s AND sender_role = 'seller' AND is_read = 0"
            cur.execute(sql, (role_id, seller_id))
            updated = cur.rowcount
        elif role == 'user' and rider_id:
             # Mark messages from rider to user as read
            sql = "UPDATE chats SET is_read = 1 WHERE userID = %s AND riderID = %s AND sender_role = 'rider' AND is_read = 0"
            cur.execute(sql, (role_id, rider_id))
            updated = cur.rowcount
        
        conn.commit()
        cur.close()
        return jsonify({'success': True, 'updated': int(updated)}), 200
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        app.logger.exception('Failed to mark chat read')
        try: cur.close()
        except Exception: pass
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: conn.close()
        except Exception: pass
@app.route('/api/product/<int:product_id>/seller')
def api_product_seller(product_id: int):
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'db_error'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT sellerID FROM products WHERE productID = %s LIMIT 1", (product_id,))
        row = cur.fetchone() or {}
        sid = row.get('sellerID')
        try: cur.close(); conn.close()
        except Exception: pass
        if not sid:
            return jsonify({'success': False, 'msg': 'not_found'}), 404
        return jsonify({'success': True, 'sellerID': sid}), 200
    except Exception as e:
        try: conn.close()
        except Exception: pass
        return jsonify({'success': False, 'msg': str(e)}), 500


@app.route('/api/products/search')
def api_products_search():
    """Search products by name across all categories.

    Query params:
      q: search query (required)
      category: optional category slug or name to filter

    Returns: { success: True, products: [ { productID, name, image, category, url } ] }
    """
    q = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or '').strip()
    if not q:
        return jsonify({'success': True, 'products': []}), 200

    # tokenize query into words
    import re as _re
    tokens = _re.findall(r"\w+", q)
    if not tokens:
        return jsonify({'success': True, 'products': []}), 200

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Build WHERE clause: require each token to match the start of a word in product name using REGEXP word-boundary
        where_parts = []
        params = []
        for t in tokens:
            # MySQL REGEXP word boundary ([:<:]) matches word-begin
            where_parts.append("name REGEXP %s")
            params.append(f"[[:<:]]{t}")
        if category:
            where_parts.append("(category = %s OR category LIKE %s)")
            params.append(category)
            params.append(f"%{category}%")

        where_sql = ' AND '.join(where_parts)
        sql = f"SELECT productID, name, image_path AS image, category FROM products WHERE {where_sql} ORDER BY productID DESC LIMIT 20"
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []
        cur.close()
        products = []
        for r in rows:
            pid = r.get('productID')
            name = r.get('name')
            img = r.get('image') or ''
            cat = r.get('category') or ''
            url = f"/product/{pid}" if pid else '#'
            products.append({'productID': pid, 'name': name, 'image': img, 'category': cat, 'url': url})
        return jsonify({'success': True, 'products': products}), 200
    except Exception as e:
        app.logger.exception('product search failed')
        try: cur.close()
        except Exception: pass
        return jsonify({'success': False, 'msg': 'Search failed'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/user/chat/partner')
def api_user_chat_partner():
    """Get the seller to chat with for the authenticated user (from their most recent order)."""
    user = session.get('user')
    if not user:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    user_id = user.get('userID') or user.get('id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Get sellerID from the user's most recent confirmed order
        cur.execute("""
            SELECT DISTINCT so.sellerID, s.storename, s.sellername, s.selleremail
            FROM seller_orders so
            LEFT JOIN sellers s ON so.sellerID = s.sellerID
            WHERE so.userID = %s AND (so.status IS NULL OR so.status != 'cancelled')
            ORDER BY so.created_at DESC
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
        
        if row and row.get('sellerID'):
            return jsonify({
                'success': True,
                'sellerID': row.get('sellerID'),
                'sellerName': row.get('storename') or row.get('sellername') or row.get('selleremail') or f"Seller {row.get('sellerID')}"
            }), 200
        else:
            return jsonify({'success': False, 'msg': 'No active orders found'}), 404
    except Exception as e:
        app.logger.exception('Failed to get user chat partner')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/user/chat/conversations')
def api_user_chat_conversations():
    """Return a list of conversations (by seller) for the authenticated user.

    Response: { success: True, conversations: [ { sellerID, sellerName, lastMessage, lastChatID, unreadCount } ] }
    """
    user = session.get('user')
    if not user:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    user_id = user.get('userID') or user.get('id')
    if not user_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Inspect chats table to decide which columns to use
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM chats")
            chat_cols = [r[0] for r in meta.fetchall()]
            meta.close()
        except Exception:
            chat_cols = []

        has_is_read = 'is_read' in chat_cols
        has_sender_role = 'sender_role' in chat_cols

        if has_is_read and has_sender_role:
            sql = (
                "SELECT c1.chatID AS lastChatID, c1.sellerID, s.storename AS sellerName, c1.messages AS lastMessage, "
                "(SELECT COUNT(*) FROM chats WHERE userID = %s AND sellerID = c1.sellerID AND sender_role = 'seller' AND is_read = 0) AS unreadCount "
                "FROM chats c1 "
                "JOIN (SELECT sellerID, MAX(chatID) AS last_chat FROM chats WHERE userID = %s GROUP BY sellerID) c2 "
                "ON c1.sellerID = c2.sellerID AND c1.chatID = c2.last_chat "
                "LEFT JOIN sellers s ON s.sellerID = c1.sellerID "
                "ORDER BY c1.chatID DESC"
            )
        elif has_sender_role:
            sql = (
                "SELECT c1.chatID AS lastChatID, c1.sellerID, s.storename AS sellerName, c1.messages AS lastMessage, "
                "(SELECT COUNT(*) FROM chats WHERE userID = %s AND sellerID = c1.sellerID AND sender_role = 'seller') AS unreadCount "
                "FROM chats c1 "
                "JOIN (SELECT sellerID, MAX(chatID) AS last_chat FROM chats WHERE userID = %s GROUP BY sellerID) c2 "
                "ON c1.sellerID = c2.sellerID AND c1.chatID = c2.last_chat "
                "LEFT JOIN sellers s ON s.sellerID = c1.sellerID "
                "ORDER BY c1.chatID DESC"
            )
        else:
            sql = (
                "SELECT c1.chatID AS lastChatID, c1.sellerID, s.storename AS sellerName, c1.messages AS lastMessage, "
                "0 AS unreadCount "
                "FROM chats c1 "
                "JOIN (SELECT sellerID, MAX(chatID) AS last_chat FROM chats WHERE userID = %s GROUP BY sellerID) c2 "
                "ON c1.sellerID = c2.sellerID AND c1.chatID = c2.last_chat "
                "LEFT JOIN sellers s ON s.sellerID = c1.sellerID "
                "ORDER BY c1.chatID DESC"
            )

        cur.execute(sql, (user_id, user_id))
        rows = cur.fetchall() or []
        try:
            cur.close()
        except Exception:
            pass

        convos = []
        for r in rows:
            convos.append({
                'sellerID': r.get('sellerID'),
                'sellerName': r.get('sellerName') or f"Seller {r.get('sellerID')}",
                'lastMessage': r.get('lastMessage'),
                'lastChatID': r.get('lastChatID'),
                'unreadCount': int(r.get('unreadCount') or 0)
            })
        return jsonify({'success': True, 'conversations': convos}), 200
    except Exception:
        try:
            app.logger.exception('Failed to fetch user conversations')
        except Exception:
            pass
        return jsonify({'success': False, 'msg': 'Failed to fetch conversations'}), 500
    finally:
        try: conn.close()
        except Exception: pass


@app.route('/api/seller/chat/partner')
def api_seller_chat_partner():
    """Get the user to chat with for the authenticated seller (from their most recent order)."""
    seller = session.get('seller')
    if not seller:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    seller_id = seller.get('sellerID') or seller.get('id')
    if not seller_id:
        return jsonify({'success': False, 'msg': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'msg': 'Database connection failed'}), 500
    try:
        cur = conn.cursor(dictionary=True)
        # Get userID from the seller's most recent order
        cur.execute("""
            SELECT DISTINCT so.userID, u.username, u.email
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.sellerID = %s AND (so.status IS NULL OR so.status != 'cancelled')
            ORDER BY so.created_at DESC
            LIMIT 1
        """, (seller_id,))
        row = cur.fetchone()
        cur.close()
        
        if row and row.get('userID'):
            return jsonify({
                'success': True,
                'userID': row.get('userID'),
                'userName': row.get('username') or row.get('email') or f"User {row.get('userID')}"
            }), 200
        else:
            return jsonify({'success': False, 'msg': 'No active orders found'}), 404
    except Exception as e:
        app.logger.exception('Failed to get seller chat partner')
        return jsonify({'success': False, 'msg': str(e)}), 500
    finally:
        try: conn.close()
        except Exception: pass

