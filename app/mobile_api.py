import os
import threading
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app.shipping_utils import estimate_shipping_fee, DEFAULT_SHIPPING_FEE

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Use the same upload directory as the web app
UPLOAD_DIR = os.path.join(PROJECT_ROOT, 'uploads')
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOC_EXT = {'pdf'}  # Business permit must be PDF

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
except Exception:
    pass


def _user_id_from_jwt() -> Optional[int]:
    """Extract the numeric user ID from the current JWT identity.

    The JWT identity is stored as str(user_id) by /api/login and /api/register.
    Returns None when the caller is not a regular user (e.g. seller/rider tokens
    whose identity is their own role-specific ID, not a users.userID).
    """
    try:
        uid = get_jwt_identity()
        if uid is not None:
            return int(uid)
        claims = get_jwt() or {}
        extra = claims.get("user_id") or claims.get("sub")
        return int(extra) if extra is not None else None
    except Exception:
        return None


def _save_upload(file_storage, prefix: str, allowed_exts=None) -> str:
    """Save an uploaded file to UPLOAD_DIR and return the filename.
    Returns empty string if no file or invalid extension."""
    if not file_storage or not file_storage.filename:
        return ''
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower().lstrip('.')
    if allowed_exts and ext not in allowed_exts:
        return ''
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_name = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, unique_name))
    return unique_name


_REG_RATE: Dict[str, list] = {}
_REG_RATE_LOCK = threading.Lock()
_REG_RATE_WINDOW = 900   # 15 minutes
_REG_RATE_MAX    = 5


def _check_reg_rate_limit() -> bool:
    """Return True if the current IP is within the registration rate limit."""
    ip = request.remote_addr or 'unknown'
    now = time.time()
    with _REG_RATE_LOCK:
        hits = [t for t in _REG_RATE.get(ip, []) if now - t < _REG_RATE_WINDOW]
        if len(hits) >= _REG_RATE_MAX:
            _REG_RATE[ip] = hits
            return False
        hits.append(now)
        _REG_RATE[ip] = hits
        return True


def _save_base64(b64_data: str, original_filename: str, prefix: str, allowed_exts=None) -> str:
    """Decode a base64 string and save it to UPLOAD_DIR.
    Returns the saved filename, or empty string on failure."""
    import base64 as _b64
    try:
        # Strip data URI prefix if present (e.g. "data:application/pdf;base64,...")
        if ',' in b64_data:
            b64_data = b64_data.split(',', 1)[1]
        data = _b64.b64decode(b64_data)
        ext = os.path.splitext(secure_filename(original_filename))[1].lower().lstrip('.')
        if not ext:
            ext = 'bin'
        if allowed_exts and ext not in allowed_exts:
            return ''
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_name = f"{prefix}_{uuid.uuid4().hex}.{ext}"
        with open(os.path.join(UPLOAD_DIR, unique_name), 'wb') as f:
            f.write(data)
        return unique_name
    except Exception as e:
        print(f"[api] _save_base64 failed: {e}", flush=True)
        return ''


api_bp = Blueprint("mobile_api", __name__, url_prefix="/api")


@api_bp.before_request
def _log_incoming():
    """Log every /api/* hit to the Flask console so we can confirm
    requests are actually arriving from the mobile client."""
    print(
        f"[api] {request.method} {request.path} "
        f"from {request.remote_addr} ct={request.content_type}",
        flush=True,
    )


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


from app.db import get_db as _get_db_connection


def _api_response(status: str, message: str, data: Any = None, http_status: int = 200):
    return jsonify({"status": status, "message": message, "data": data}), http_status

def _api_success(message: str, data: Any = None, http_status: int = 200):
    return _api_response("success", message, data, http_status)


def _api_error(message: str, data: Any = None, http_status: int = 400):
    return _api_response("error", message, data, http_status)


def _require_json() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    if not request.is_json:
        return None, _api_error("Expected JSON body", {"expected": "application/json"}, 400)
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return None, _api_error("Invalid JSON body", None, 400)
    return payload, None


def _get_seller_pickup_location(cur, seller_id):
    try:
        cur.execute(
            'SELECT region, province, city, barangay, exact_address FROM sellers WHERE sellerID = %s LIMIT 1',
            (seller_id,)
        )
        row = cur.fetchone()
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


def _discover_roles_by_email(cur, email: str) -> Tuple[list, Dict[str, Any]]:
    roles = []
    ids: Dict[str, Any] = {}

    # User
    try:
        cur.execute("SELECT userID FROM users WHERE email = %s LIMIT 1", (email,))
        row = cur.fetchone()
        if row and row.get("userID") is not None:
            roles.append("user")
            ids["user_id"] = int(row["userID"])
    except Exception:
        pass

    # Seller
    try:
        cur.execute("SELECT sellerID FROM sellers WHERE selleremail = %s LIMIT 1", (email,))
        row = cur.fetchone()
        if row and row.get("sellerID") is not None:
            roles.append("seller")
            ids["seller_id"] = int(row["sellerID"])
    except Exception:
        pass

    # Rider
    try:
        cur.execute("SELECT riderID FROM riders WHERE rideremail = %s LIMIT 1", (email,))
        row = cur.fetchone()
        if row and row.get("riderID") is not None:
            roles.append("rider")
            ids["rider_id"] = int(row["riderID"])
    except Exception:
        pass

    return roles, ids


def _get_users_password_column(cur) -> str:
    cur.execute("SHOW COLUMNS FROM users")
    cols = [r["Field"].lower() for r in cur.fetchall()]
    for candidate in ("password", "userpassword", "passwd", "pass"):
        if candidate in cols:
            return candidate
    return "password"


def _coerce_stock(value: Any) -> int:
    """Stock is stored as varchar in the DB — coerce to int safely."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return 0


def _product_to_api(row: Dict[str, Any]) -> Dict[str, Any]:
    product_id = row.get("productID") or row.get("id") or row.get("product_id")
    return {
        "id": int(product_id) if product_id is not None else None,
        "name": row.get("name") or row.get("productname") or "",
        "price": float(row.get("price") or 0),
        "description": row.get("description") or row.get("productdesc") or row.get("desc") or "",
        "stock": _coerce_stock(row.get("stock")),
        "category": row.get("category"),
        "image_path": row.get("image_path") or row.get("imageurl") or row.get("image") or "",
    }


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@api_bp.post("/auth/exchange")
def api_auth_exchange():
    """
    Exchange a Firebase ID token for a backend JWT.
    Body: { email, id_token }
    """
    payload, err = _require_json()
    if err:
        return err

    email = (payload.get("email") or "").strip().lower()
    id_token = (payload.get("id_token") or "").strip()

    if not email or not id_token:
        return _api_error("Missing email or id_token", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        roles, ids = _discover_roles_by_email(cur, email)

        if not roles:
            return _api_error("Account not found in backend DB", {"email": email}, 404)

        subject = ids.get("user_id") or ids.get("seller_id") or ids.get("rider_id")
        additional_claims: Dict[str, Any] = {"roles": roles, "email": email}

        if "seller_id" in ids:
            additional_claims["seller"] = {"sellerID": ids["seller_id"], "email": email}
        if "rider_id" in ids:
            additional_claims["rider"] = {"riderID": ids["rider_id"], "email": email}

        access_token = create_access_token(identity=str(subject), additional_claims=additional_claims)
        return _api_success("Token exchanged", {"access_token": access_token, "roles": roles})
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
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


@api_bp.post("/roles")
def api_roles():
    """Return roles for a given email. Body: { email }"""
    payload, err = _require_json()
    if err:
        return err

    email = (payload.get("email") or "").strip().lower()
    if not email:
        return _api_error("Missing email", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        roles, ids = _discover_roles_by_email(cur, email)
        return _api_success("Roles fetched", {"roles": roles, "ids": ids})
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
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


@api_bp.post("/register")
def api_register():
    payload, err = _require_json()
    if err:
        return err

    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    region = (payload.get("region") or payload.get("reg-region") or "").strip()
    province = (payload.get("province") or payload.get("reg-province") or "").strip()
    city = (payload.get("city") or payload.get("reg-city") or "").strip()
    barangay = (payload.get("barangay") or payload.get("reg-barangay") or "").strip()
    home_address = (payload.get("home_address") or payload.get("reg-home-address") or "").strip()
    contact_number = (payload.get("contact_number") or payload.get("reg-contact-number") or "").strip()

    required = [username, email, password, region, province, city, barangay, home_address, contact_number]
    if not all(required):
        return _api_error(
            "Missing required fields",
            {"required": ["username", "email", "password", "region", "province", "city", "barangay", "home_address", "contact_number"]},
            400,
        )

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        pw_col = _get_users_password_column(cur)

        cur.execute("SELECT userID FROM users WHERE username = %s OR email = %s LIMIT 1", (username, email))
        if cur.fetchone():
            return _api_error("User already exists", None, 400)

        hashed = generate_password_hash(password)
        cur.execute(
            f"INSERT INTO users (username, email, {pw_col}) VALUES (%s, %s, %s)",
            (username, email, hashed),
        )
        user_id = cur.lastrowid

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
        cur.execute(
            """
            INSERT INTO user_saved_addresses (userID, region, province, city, barangay, home_address, contact_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                region = VALUES(region),
                province = VALUES(province),
                city = VALUES(city),
                barangay = VALUES(barangay),
                home_address = VALUES(home_address),
                contact_number = VALUES(contact_number)
            """,
            (user_id, region, province, city, barangay, home_address, contact_number),
        )
        conn.commit()

        access_token = create_access_token(identity=str(user_id))
        return _api_success(
            "Registered successfully",
            {"access_token": access_token, "user": {"id": user_id, "username": username, "email": email}},
            200,
        )
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _api_error("Server error registering user", {"error": str(e)}, 500)
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


@api_bp.post("/login")
def api_login():
    payload, err = _require_json()
    if err:
        return err

    identifier = (payload.get("username") or payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not identifier or not password:
        return _api_error("Missing username/email or password", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM users WHERE username = %s OR email = %s LIMIT 1",
            (identifier, identifier),
        )
        user = cur.fetchone()
        if not user:
            return _api_error("Invalid credentials", None, 401)

        pw_col = _get_users_password_column(cur)
        stored_hash = user.get(pw_col) or user.get("password") or ""
        if not check_password_hash(stored_hash, password):
            return _api_error("Invalid credentials", None, 401)

        user_id = user.get("userID") or user.get("id")
        access_token = create_access_token(identity=str(user_id))
        refresh_token = create_refresh_token(identity=str(user_id))
        return _api_success(
            "Login successful",
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user_id,
                    "username": user.get("username"),
                    "email": user.get("email"),
                },
            },
        )
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
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
# Seller / Rider login (mobile, JWT-based)
#
# These return access tokens whose additional_claims include a `seller` or
# `rider` dict, so the existing helpers `_get_authenticated_seller_id` and
# `_get_rider_id_from_session` (in app/authentication.py) recognize the
# caller and the existing /api/seller/stats/* and /api/rider/orders endpoints
# work for mobile clients without changes.
# ---------------------------------------------------------------------------

def _select_password_column(cur, table: str, candidates) -> Optional[str]:
    cur.execute(f"SHOW COLUMNS FROM {table}")
    cols = [r["Field"].lower() for r in cur.fetchall()]
    for candidate in candidates:
        if candidate.lower() in cols:
            return candidate
    return None
@api_bp.get("/seller/categories")
@jwt_required()
def api_seller_categories():
    """Returns the list of categories assigned to the logged-in seller."""
    try:
        user_id = _user_id_from_jwt()
        if not user_id:
            return _api_error("Unauthorized", None, 401)
            
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Check if seller_categories table exists, fallback to all categories if not
        try:
            cur.execute("""
                SELECT c.categoryID as id, c.name, c.slug 
                FROM seller_categories sc 
                JOIN categories c ON c.categoryID = sc.category_id 
                WHERE sc.seller_id = %s
                ORDER BY c.name ASC
            """, (user_id,))
            categories = cur.fetchall()
        except Exception as e:
            # Table might not exist or be named differently, fetch all categories as fallback
            try:
                cur.execute("SELECT categoryID as id, name, slug FROM categories ORDER BY name ASC")
                categories = cur.fetchall()
            except Exception:
                categories = [
                    {'id': 11, 'name': 'Baby Clothes', 'slug': 'baby-clothes'},
                    {'id': 15, 'name': 'Comfort Toys', 'slug': 'comfort-toys'},
                    {'id': 16, 'name': 'Educational Toys', 'slug': 'educational-toys'},
                    {'id': 17, 'name': 'Stollers & Gears', 'slug': 'stollers-gears'},
                    {'id': 19, 'name': 'Safety and Health', 'slug': 'safety-and-health'},
                    {'id': 20, 'name': 'Nursery Furniture', 'slug': 'nursery-furniture'},
                ]
        
        return _api_success("Categories fetched", {"categories": categories})
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if 'cur' in locals() and cur:
                cur.close()
            if 'conn' in locals() and conn:
                conn.close()
        except Exception:
            pass



@api_bp.post("/seller/login")
def api_seller_login():
    payload, err = _require_json()
    if err:
        return err

    identifier = (payload.get("email") or payload.get("selleremail") or payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not identifier or not password:
        return _api_error("Missing email or password", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM sellers WHERE selleremail = %s LIMIT 1", (identifier,))
        seller = cur.fetchone()
        if not seller:
            return _api_error("Invalid credentials", None, 401)

        pw_col = _select_password_column(cur, "sellers", ("password", "sellerpassword", "passwd"))
        if not pw_col:
            return _api_error("Server configuration error (password column)", None, 500)

        stored_hash = seller.get(pw_col) or ""
        if not check_password_hash(stored_hash, password):
            return _api_error("Invalid credentials", None, 401)

        status = (seller.get("status") or "").lower()
        # Mirror rider login: accept both 'approved' and 'active' as approved.
        if status and status not in ("approved", "active"):
            return _api_error(
                "Your seller account is not yet approved.",
                {"status": status or "pending"},
                403,
            )

        seller_id = int(seller.get("sellerID"))
        email = seller.get("selleremail") or identifier
        additional_claims = {
            "roles": ["seller"],
            "email": email,
            "seller": {
                "sellerID": seller_id,
                "email": email,
                "sellername": seller.get("sellername"),
                "storename": seller.get("storename"),
            },
        }
        access_token = create_access_token(
            identity=str(seller_id),
            additional_claims=additional_claims,
        )
        refresh_token = create_refresh_token(
            identity=str(seller_id),
            additional_claims=additional_claims,
        )
        return _api_success(
            "Seller login successful",
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": seller_id,
                    "username": seller.get("sellername") or email,
                    "email": email,
                    "role": "seller",
                    "storename": seller.get("storename"),
                },
            },
        )
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
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


@api_bp.post("/rider/login")
def api_rider_login():
    payload, err = _require_json()
    if err:
        return err

    identifier = (payload.get("email") or payload.get("rideremail") or payload.get("username") or "").strip()
    password = payload.get("password") or payload.get("riderpass") or ""

    if not identifier or not password:
        return _api_error("Missing email or password", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM riders WHERE rideremail = %s LIMIT 1", (identifier,))
        rider = cur.fetchone()
        if not rider:
            return _api_error("Invalid credentials", None, 401)

        pw_col = _select_password_column(cur, "riders", ("riderpass", "password", "passwd"))
        if not pw_col:
            return _api_error("Server configuration error (password column)", None, 500)

        stored_hash = rider.get(pw_col) or ""
        if not check_password_hash(stored_hash, password):
            return _api_error("Invalid credentials", None, 401)

        status = (rider.get("status") or "").lower()
        # Admin approval writes status='active'; legacy records may use 'approved'.
        if status and status not in ("approved", "active"):
            return _api_error(
                "Your rider account is not yet approved.",
                {"status": status or "pending"},
                403,
            )

        rider_id = int(rider.get("riderID"))
        email = rider.get("rideremail") or identifier
        additional_claims = {
            "roles": ["rider"],
            "email": email,
            "rider": {
                "riderID": rider_id,
                "email": email,
                "ridername": rider.get("ridername"),
            },
        }
        access_token = create_access_token(
            identity=str(rider_id),
            additional_claims=additional_claims,
        )
        refresh_token = create_refresh_token(
            identity=str(rider_id),
            additional_claims=additional_claims,
        )
        return _api_success(
            "Rider login successful",
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": rider_id,
                    "username": rider.get("ridername") or email,
                    "email": email,
                    "role": "rider",
                },
            },
        )
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
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
# Token refresh — mobile clients call this when access token expires
# ---------------------------------------------------------------------------

@api_bp.post("/refresh")
@jwt_required(refresh=True)
def api_refresh_token():
    identity = get_jwt_identity()
    # Restore role-specific claims (seller / rider) stored in the refresh token
    refresh_claims = get_jwt()
    additional: Dict[str, Any] = {}
    for key in ("seller", "rider", "roles", "email"):
        if key in refresh_claims:
            additional[key] = refresh_claims[key]
    new_access_token = create_access_token(
        identity=identity,
        additional_claims=additional if additional else None,
    )
    return _api_success("Token refreshed", {"access_token": new_access_token})


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@api_bp.get("/products")
def api_products_list():
    page = _safe_int(request.args.get("page", 1), 1)
    page_size = _safe_int(request.args.get("page_size", 20), 20)
    category = request.args.get("category")
    search = request.args.get("search") or request.args.get("q")
    offset = (page - 1) * page_size

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        where_clauses = []
        params: list = []

        if category:
            where_clauses.append("category = %s")
            params.append(category)
        if search:
            where_clauses.append("(name LIKE %s OR description LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        cur.execute(
            f"SELECT * FROM products {where_sql} ORDER BY productID DESC LIMIT %s OFFSET %s",
            (*params, page_size, offset),
        )
        rows = cur.fetchall()
        products = [_product_to_api(r) for r in rows]
        products = [p for p in products if p.get("id") is not None]
        return _api_success(
            "Products fetched",
            {"items": products, "page": page, "page_size": page_size},
        )
    except Exception as e:
        return _api_error("Server error fetching products", {"error": str(e)}, 500)
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


@api_bp.get("/products/featured")
def api_products_featured():
    """Mobile alias for /api/featured-products. Returns the same envelope shape."""
    from app import authentication as auth_module
    page = max(1, _safe_int(request.args.get("page", 1), 1))
    per_page = _safe_int(request.args.get("per_page"), getattr(auth_module, "FEATURED_PAGE_SIZE", 12))
    per_page = max(1, min(per_page, 100))

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        payload = auth_module._load_featured_products(cur, conn, page, per_page)
        rows = payload.get("products") or []

        items = []
        for row in rows:
            product_id = (
                row.get("productID")
                or row.get("product_id")
                or row.get("id")
                or row.get("productId")
            )
            if not product_id:
                continue

            image_name = None
            try:
                image_list = auth_module._extract_product_image_list(row)
                image_name = image_list[0] if image_list else None
            except Exception:
                image_name = row.get("image_path") or row.get("image") or row.get("imageurl")

            try:
                if image_name:
                    image_url = url_for("uploaded_file", filename=image_name)
                else:
                    image_url = url_for("static", filename="images/default.png")
            except Exception:
                image_url = ""

            price = row.get("price")
            try:
                price_value = float(price) if price is not None else 0.0
            except Exception:
                price_value = 0.0

            items.append({
                "id": int(product_id) if product_id else None,
                "name": row.get("name") or row.get("title") or f"Product {product_id}",
                "price": price_value,
                "image_url": image_url,
                "image_path": image_name,
                "description": row.get("description") or row.get("desc") or "",
                "stock": _coerce_stock(row.get("stock")),
                "category": row.get("category"),
            })

        return _api_success(
            "Featured products fetched",
            {
                "items": items,
                "page": payload.get("page", page),
                "per_page": per_page,
                "total_pages": payload.get("total_pages", 1),
                "total_products": payload.get("total_products", len(items)),
            },
        )
    except Exception as e:
        return _api_error("Server error fetching featured products", {"error": str(e)}, 500)
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


@api_bp.get("/products/<int:product_id>")
def api_products_get(product_id: int):
    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM products WHERE productID = %s LIMIT 1", (product_id,))
        row = cur.fetchone()
        if not row:
            return _api_error("Product not found", None, 404)
        return _api_success("Product fetched", _product_to_api(row), 200)
    except Exception as e:
        return _api_error("Server error fetching product", {"error": str(e)}, 500)
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
# Categories (mobile)
# ---------------------------------------------------------------------------

@api_bp.get("/categories")
def api_categories_list():
    """Return the full category-page payload (categories + featured products + pagination)."""
    from app import authentication as auth_module

    page = max(1, _safe_int(request.args.get("page", 1), 1))
    per_page = _safe_int(
        request.args.get("per_page"),
        getattr(auth_module, "CATEGORY_PAGE_SIZE", 12),
    )
    per_page_max = getattr(auth_module, "CATEGORY_PAGE_MAX", 60)
    per_page = max(1, min(per_page, per_page_max))

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        try:
            cur.execute("SELECT * FROM categories ORDER BY name ASC")
            categories = cur.fetchall() or []
        except Exception:
            categories = [
                {"id": 1, "name": "Baby Clothes & Accessories", "slug": "baby-clothes"},
                {"id": 2, "name": "Comfort Toys", "slug": "comfort-toys"},
                {"id": 3, "name": "Educational Toys", "slug": "educational-toys"},
                {"id": 4, "name": "Nursery Furniture", "slug": "nursery-furniture"},
                {"id": 5, "name": "Safety and Health", "slug": "safety-and-health"},
                {"id": 6, "name": "Stroller Gear", "slug": "stroller-gear"},
            ]

        featured_payload = auth_module._load_featured_products(cur, conn, page, per_page)
        featured_rows = featured_payload.get("products") or []

        featured_products = []
        for row in featured_rows:
            pid = row.get("productID") or row.get("product_id") or row.get("id")
            if not pid:
                continue
            image_name = row.get("image_path") or row.get("image") or row.get("imageurl")
            try:
                if image_name:
                    image_url = url_for("uploaded_file", filename=image_name)
                else:
                    image_url = url_for("static", filename="images/default.png")
            except Exception:
                image_url = ""
            try:
                price_value = float(row.get("price") or 0)
            except Exception:
                price_value = 0.0
            featured_products.append({
                "id": int(pid),
                "name": row.get("name") or row.get("title") or f"Product {pid}",
                "price": price_value,
                "image_url": image_url,
                "image_path": image_name,
                "description": row.get("description") or row.get("desc") or "",
                "category": row.get("category"),
            })

        normalized_categories = []
        for c in categories:
            cid = c.get("categoryID") or c.get("id")
            normalized_categories.append({
                "id": int(cid) if cid is not None else None,
                "name": c.get("name") or "",
                "slug": c.get("slug") or "",
                "image_path": c.get("image_path") or c.get("image") or "",
            })

        pagination = {
            "page": featured_payload.get("page", page),
            "per_page": per_page,
            "total_pages": featured_payload.get("total_pages", 1),
            "total_products": featured_payload.get("total_products", len(featured_products)),
        }
        pagination["has_prev"] = pagination["page"] > 1
        pagination["has_next"] = pagination["page"] < pagination["total_pages"]
        pagination["prev_page"] = pagination["page"] - 1 if pagination["has_prev"] else None
        pagination["next_page"] = pagination["page"] + 1 if pagination["has_next"] else None

        return _api_success(
            "Categories fetched",
            {
                "categories": normalized_categories,
                "featured_products": featured_products,
                "pagination": pagination,
            },
        )
    except Exception as e:
        return _api_error("Server error fetching categories", {"error": str(e)}, 500)
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


@api_bp.get("/categories/<slug>")
def api_categories_detail(slug: str):
    """Return one category with its products + pagination, mirroring /api/categories/<slug> in authentication.py."""
    from app import authentication as auth_module

    page = max(1, _safe_int(request.args.get("page", 1), 1))
    per_page = _safe_int(
        request.args.get("per_page"),
        getattr(auth_module, "CATEGORY_PAGE_SIZE", 12),
    )
    per_page_max = getattr(auth_module, "CATEGORY_PAGE_MAX", 60)
    per_page = max(1, min(per_page, per_page_max))

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        try:
            categories = auth_module._fetch_all_categories(conn) or []
        except Exception:
            categories = []

        slug_lc = (slug or "").strip().lower()
        current_category = next((c for c in categories if (c.get("slug") or "").strip().lower() == slug_lc), None)
        if not current_category:
            slugify = getattr(auth_module, "_slugify_category_name", None)
            current_category = next(
                (
                    c
                    for c in categories
                    if callable(slugify) and slugify(c.get("name")) == slug_lc
                ),
                None,
            )
        if not current_category:
            cat_name = slug.replace("-", " ").title()
            current_category = next(
                (c for c in categories if (c.get("name") or "").strip().lower() == cat_name.lower()),
                None,
            )
        if not current_category:
            current_category = {"name": slug.replace("-", " ").title(), "slug": slug}

        try:
            cur.close()
        except Exception:
            pass
        cur = None

        data = auth_module._load_category_products(
            conn, slug, current_category, categories, page=page, per_page=per_page
        )
        products = data.get("products") or []

        pagination = {
            "page": data.get("page", page),
            "per_page": data.get("per_page", per_page),
            "total_pages": max(1, data.get("total_pages", 1) or 1),
            "total_products": data.get("total_products", len(products)),
        }
        pagination["has_prev"] = pagination["page"] > 1
        pagination["has_next"] = pagination["page"] < pagination["total_pages"]
        pagination["prev_page"] = pagination["page"] - 1 if pagination["has_prev"] else None
        pagination["next_page"] = pagination["page"] + 1 if pagination["has_next"] else None

        return _api_success(
            "Category fetched",
            {
                "current_category": current_category,
                "categories": categories,
                "products": products,
                "pagination": pagination,
            },
        )
    except Exception as e:
        return _api_error("Server error fetching category", {"error": str(e)}, 500)
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
# Cart
# ---------------------------------------------------------------------------

@api_bp.get("/cart")
@jwt_required()
def api_cart_get():
    identity = get_jwt_identity()

    # Cart is only for regular users — riders and sellers don't have carts.
    # Return empty cart gracefully instead of crashing with a 500.
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_success("Cart fetched", [])

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT c.*, p.name, p.price AS product_price, p.image_path,
                   p.description, p.stock, cat.name AS category
            FROM cart c
            JOIN products p ON p.productID = c.productID
            LEFT JOIN categories cat ON cat.categoryID = p.categoryID
            WHERE c.userID = %s
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        items = []
        for r in rows:
            items.append({
                "id": r.get("cartID") or r.get("id"),
                "quantity": r.get("quantity", 1),
                "unit_price": float(r.get("product_price") or r.get("price") or 0),
                "total_price": float(r.get("product_price") or 0) * int(r.get("quantity") or 1),
                "product": _product_to_api(r),
                "size": r.get("size"),
                "color": r.get("color"),
                "added_at": str(r.get("created_at") or ""),
            })
        return _api_success("Cart fetched", items)
    except Exception as e:
        return _api_error("Server error fetching cart", {"error": str(e)}, 500)
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


@api_bp.post("/cart")
@jwt_required()
def api_cart_add():
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Cart is only available for customer accounts", None, 403)
    payload, err = _require_json()
    if err:
        return err

    product_id = _safe_int(payload.get("product_id"), 0)
    quantity = _safe_int(payload.get("quantity", 1), 1)
    size = payload.get("size")
    color = payload.get("color")

    if not product_id:
        return _api_error("Missing product_id", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT p.price, p.name, p.image_path, p.description, p.stock,
                   cat.name AS category
            FROM products p
            LEFT JOIN categories cat ON cat.categoryID = p.categoryID
            WHERE p.productID = %s
            LIMIT 1
            """,
            (product_id,),
        )
        product_row = cur.fetchone()
        if not product_row:
            return _api_error("Product not found", None, 404)
        unit_price = float(product_row.get("price") or 0)
        available_stock = _coerce_stock(product_row.get("stock"))

        # Reject if the requested quantity exceeds remaining stock when combined
        # with any quantity already in the user's cart for this product.
        if quantity <= 0:
            return _api_error("Quantity must be at least 1", None, 400)
        if available_stock <= 0:
            return _api_error("Product is out of stock", None, 409)
        cur.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS qty FROM cart WHERE userID = %s AND productID = %s",
            (user_id, product_id),
        )
        existing_row = cur.fetchone() or {}
        existing_qty = int(existing_row.get("qty") or 0)
        if existing_qty + quantity > available_stock:
            remaining = max(0, available_stock - existing_qty)
            return _api_error(
                f"Only {remaining} more available (stock: {available_stock})",
                {"available": remaining, "stock": available_stock},
                409,
            )

        total_price = unit_price * quantity

        cur.execute(
            "INSERT INTO cart (userID, productID, quantity, price, total_price) VALUES (%s, %s, %s, %s, %s)",
            (user_id, product_id, quantity, unit_price, total_price),
        )
        conn.commit()
        cart_id = cur.lastrowid
        item = {
            "id": cart_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "product": {
                "id": product_id,
                "name": product_row.get("name") or "",
                "price": unit_price,
                "image_path": product_row.get("image_path") or "",
                "description": product_row.get("description") or "",
                "stock": int(product_row.get("stock") or 0),
                "category": product_row.get("category") or "",
            },
            "added_at": "",
        }
        return _api_success("Added to cart", item, 201)
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _api_error("Server error adding to cart", {"error": str(e)}, 500)
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


@api_bp.put("/cart/<int:cart_item_id>")
@jwt_required()
def api_cart_update(cart_item_id: int):
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Cart is only available for customer accounts", None, 403)
    payload, err = _require_json()
    if err:
        return err

    quantity = _safe_int(payload.get("quantity", 1), 1)
    if quantity <= 0:
        return _api_error("Quantity must be at least 1", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        # Look up the product backing this cart row so we can validate stock.
        cur.execute(
            """
            SELECT p.stock
              FROM cart c
              JOIN products p ON p.productID = c.productID
             WHERE c.cartID = %s AND c.userID = %s
             LIMIT 1
            """,
            (cart_item_id, user_id),
        )
        stock_row = cur.fetchone()
        if not stock_row:
            return _api_error("Cart item not found", None, 404)
        available_stock = _coerce_stock(stock_row.get("stock"))
        if quantity > available_stock:
            return _api_error(
                f"Only {available_stock} in stock",
                {"available": available_stock, "stock": available_stock},
                409,
            )
        cur.execute(
            "UPDATE cart SET quantity = %s WHERE cartID = %s AND userID = %s",
            (quantity, cart_item_id, user_id),
        )
        conn.commit()
        cur.execute(
            """
            SELECT c.*, p.name, p.price AS product_price, p.image_path,
                   p.description, p.stock, cat.name AS category
            FROM cart c
            JOIN products p ON p.productID = c.productID
            LEFT JOIN categories cat ON cat.categoryID = p.categoryID
            WHERE c.cartID = %s
            """,
            (cart_item_id,),
        )
        row = cur.fetchone()
        if row:
            item = {
                "id": row.get("cartID"),
                "quantity": row.get("quantity", 1),
                "unit_price": float(row.get("product_price") or 0),
                "total_price": float(row.get("product_price") or 0) * int(row.get("quantity") or 1),
                "product": _product_to_api(row),
                "size": row.get("size"),
                "color": row.get("color"),
                "added_at": str(row.get("created_at") or ""),
            }
            return _api_success("Cart updated", item)
        return _api_success("Cart updated", {"id": cart_item_id})
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _api_error("Server error updating cart", {"error": str(e)}, 500)
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


@api_bp.delete("/cart/<int:cart_item_id>")
@jwt_required()
def api_cart_delete(cart_item_id: int):
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Cart is only available for customer accounts", None, 403)
    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "DELETE FROM cart WHERE cartID = %s AND userID = %s",
            (cart_item_id, user_id),
        )
        conn.commit()
        return _api_success("Item removed from cart")
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _api_error("Server error removing from cart", {"error": str(e)}, 500)
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


@api_bp.delete("/cart")
@jwt_required()
def api_cart_clear():
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Cart is only available for customer accounts", None, 403)
    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("DELETE FROM cart WHERE userID = %s", (user_id,))
        conn.commit()
        return _api_success("Cart cleared")
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _api_error("Server error clearing cart", {"error": str(e)}, 500)
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
# Seller registration (mobile)
# ---------------------------------------------------------------------------

@api_bp.post("/seller/register")
def api_seller_register():
    """Mobile seller registration — accepts both JSON and multipart/form-data
    (multipart is used when a business permit file is attached)."""

    if not _check_reg_rate_limit():
        return _api_error("Too many registration attempts. Please wait 15 minutes.", None, 429)

    # Accept multipart/form-data OR application/json
    is_multipart = request.content_type and 'multipart/form-data' in request.content_type
    if is_multipart:
        payload = request.form.to_dict()
    else:
        if not request.is_json:
            return _api_error("Expected JSON or multipart/form-data", None, 400)
        payload = request.get_json(silent=True) or {}

    print(f"[seller_register] content_type={request.content_type} is_multipart={is_multipart} keys={list(payload.keys())}", flush=True)

    sellername      = (payload.get("sellername") or payload.get("ridername") or "").strip()
    selleremail     = (payload.get("selleremail") or payload.get("rideremail") or "").strip()
    contactnumber   = (payload.get("contactnumber") or payload.get("phone") or "").strip()
    storename       = (payload.get("storename") or "").strip()
    storedesc       = (payload.get("storedesc") or "").strip()
    region          = (payload.get("region") or "").strip()
    province        = (payload.get("province") or "").strip()
    city            = (payload.get("city") or "").strip()
    barangay        = (payload.get("barangay") or "").strip()
    exact_address   = (payload.get("exact_address") or "").strip()
    password        = payload.get("password") or payload.get("sellerpass") or ""
    confirmpassword = payload.get("confirmpassword") or payload.get("confirmsellerpass") or ""
    seller_category_ids = payload.get("seller_category_ids") or []

    print(f"[seller_register] name={sellername!r} email={selleremail!r} store={storename!r} pass_len={len(password)}", flush=True)

    if not all([sellername, selleremail, contactnumber, password, confirmpassword]):
        missing = [k for k,v in {'sellername':sellername,'selleremail':selleremail,'contactnumber':contactnumber,'password':password,'confirmpassword':confirmpassword}.items() if not v]
        print(f"[seller_register] missing fields: {missing}", flush=True)
        return _api_error(f"Please fill in all required fields (missing: {', '.join(missing)})", None, 400)

    if password != confirmpassword:
        return _api_error("Passwords do not match", None, 400)

    if len(password) < 6:
        return _api_error("Password must be at least 6 characters", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT sellerID FROM sellers WHERE selleremail = %s LIMIT 1", (selleremail,))
        if cur.fetchone():
            return _api_error("An account with this email already exists", None, 400)

        hashed = generate_password_hash(password)

        cur.execute("SHOW COLUMNS FROM sellers")
        column_rows = cur.fetchall()
        columns = [r["Field"].lower() for r in column_rows]
        # Map of `field_name (lowercased) → column metadata` for NOT NULL
        # columns that have no DB default and aren't auto_increment. We'll
        # auto-fill empty strings / 0 for any such column we don't already
        # supply, so an admin adding a new mandatory column to the table
        # doesn't break mobile registration.
        column_meta = {
            r["Field"].lower(): r
            for r in column_rows
            if (r.get("Null") or "").upper() == "NO"
            and r.get("Default") is None
            and "auto_increment" not in (r.get("Extra") or "").lower()
        }

        if "password" in columns:
            pw_col = "password"
        elif "sellerpassword" in columns:
            pw_col = "sellerpassword"
        elif "passwd" in columns:
            pw_col = "passwd"
        else:
            return _api_error("Server configuration error (password column)", None, 500)

        # `contactnumber` is INT(12) in the legacy schema but PH phone
        # numbers like 09xxxxxxxxx overflow signed INT (max 2147483647).
        # Coerce safely; fall back to 0 if the value can't be parsed.
        try:
            contactnumber_int = int(contactnumber.lstrip("+").replace(" ", "").replace("-", "")) if contactnumber else 0
        except ValueError:
            contactnumber_int = 0
        if contactnumber_int > 2147483647:
            contactnumber_int = 2147483647

        # `storename` is NOT NULL in the legacy sellers schema. The rider-style
        # mobile registration may not provide it — fall back to seller name.
        effective_storename = storename or sellername

        # Required columns we always insert.
        cols = ["sellername", "selleremail", "storename", pw_col]
        values = [sellername, selleremail, effective_storename, hashed]

        # Optional columns — only include when present in the table schema.
        optional = {
            "contactnumber": contactnumber_int,
            "storedesc": storedesc,
            "region": region,
            "province": province,
            "city": city,
            "barangay": barangay,
            "exact_address": exact_address,
        }
        for col_name, col_val in optional.items():
            if col_name in columns:
                cols.append(col_name)
                values.append(col_val)

        if "status" in columns:
            cols.append("status")
            values.append("pending")

        # Auto-fill any remaining NOT NULL column that has no DB default. This
        # covers known cases (storelogo_path, businesspermit_path) and any new
        # column an admin may have added to the sellers table since this code
        # was written (e.g. `category`). Strings get '', numerics get 0.
        already = {c.lower() for c in cols}
        for col_name, meta in column_meta.items():
            if col_name in already:
                continue
            col_type = (meta.get("Type") or "").lower()
            if any(t in col_type for t in ("int", "decimal", "double", "float", "bit")):
                fill = 0
            else:
                fill = ""
            cols.append(col_name)
            values.append(fill)

        seller_category = ""
        if seller_category_ids:
            try:
                placeholders = ",".join(["%s"] * len(seller_category_ids))
                cur.execute(
                    f"SELECT categoryID, name FROM categories WHERE categoryID IN ({placeholders})",
                    tuple(seller_category_ids),
                )
                rows = cur.fetchall()
                seller_category = ", ".join(r["name"] for r in rows if r.get("name"))
            except Exception:
                pass

        if "seller_category" in columns and seller_category:
            cols.append("seller_category")
            values.append(seller_category)

        # Handle business permit file upload — multipart OR base64 in JSON
        permit_path = ""
        if is_multipart:
            permit_path = _save_upload(
                request.files.get('businesspermit'),
                prefix='permit',
                allowed_exts=ALLOWED_DOC_EXT,
            )
        else:
            # Flutter Web sends base64-encoded file in JSON body
            b64 = payload.get('businesspermit_base64') or ''
            filename = payload.get('businesspermit_filename') or 'permit.pdf'
            if b64:
                permit_path = _save_base64(b64, filename, prefix='permit',
                                           allowed_exts=ALLOWED_DOC_EXT)

        if "businesspermit_path" in columns:
            try:
                idx = [c.lower() for c in cols].index("businesspermit_path")
                values[idx] = permit_path
            except ValueError:
                cols.append("businesspermit_path")
                values.append(permit_path)

        placeholders = ",".join(["%s"] * len(cols))
        sql = "INSERT INTO sellers ({}) VALUES ({})".format(",".join(cols), placeholders)
        cur.execute(sql, tuple(values))
        new_seller_id = cur.lastrowid
        conn.commit()

        return _api_success(
            "Registration submitted! We will review your application and contact you soon.",
            {"seller_id": new_seller_id, "selleremail": selleremail},
            201,
        )
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        import traceback
        print("=" * 60, flush=True)
        print("SELLER REGISTER FAILED:", repr(e), flush=True)
        traceback.print_exc()
        print("=" * 60, flush=True)
        return _api_error(
            "Server error during registration",
            {"error": str(e), "type": type(e).__name__},
            500,
        )
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


@api_bp.post("/rider/register")
def api_rider_register():
    """Mobile rider registration — accepts both JSON and multipart/form-data
    (multipart is used when a driver's license file is attached)."""

    if not _check_reg_rate_limit():
        return _api_error("Too many registration attempts. Please wait 15 minutes.", None, 429)

    is_multipart = request.content_type and 'multipart/form-data' in request.content_type
    if is_multipart:
        payload = request.form.to_dict()
    else:
        if not request.is_json:
            return _api_error("Expected JSON or multipart/form-data", None, 400)
        payload = request.get_json(silent=True) or {}

    ridername     = (payload.get("ridername") or "").strip()
    rideremail    = (payload.get("rideremail") or "").strip()
    phone         = (payload.get("phone") or "").strip()
    region        = (payload.get("region") or "").strip()
    province      = (payload.get("province") or "").strip()
    city          = (payload.get("city") or "").strip()
    barangay      = (payload.get("barangay") or "").strip()
    vehicle_type  = (payload.get("vehicle_type") or "").strip()
    riderpass     = payload.get("riderpass") or ""
    confirmpass   = payload.get("confirmriderpass") or ""

    if not all([ridername, rideremail, phone, riderpass, confirmpass]):
        return _api_error("Please fill in all required fields", None, 400)

    if riderpass != confirmpass:
        return _api_error("Passwords do not match", None, 400)

    if len(riderpass) < 6:
        return _api_error("Password must be at least 6 characters", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT riderID FROM riders WHERE rideremail = %s LIMIT 1", (rideremail,))
        if cur.fetchone():
            return _api_error("An account with this email already exists", None, 400)

        hashed = generate_password_hash(riderpass)

        cur.execute("SHOW COLUMNS FROM riders")
        column_rows = cur.fetchall()
        columns = [r["Field"].lower() for r in column_rows]
        column_meta = {
            r["Field"].lower(): r
            for r in column_rows
            if (r.get("Null") or "").upper() == "NO"
            and r.get("Default") is None
            and "auto_increment" not in (r.get("Extra") or "").lower()
        }

        if "riderpass" in columns:
            pw_col = "riderpass"
        elif "password" in columns:
            pw_col = "password"
        else:
            pw_col = "riderpass"

        # Best-effort: try to add optional location/vehicle columns. If the
        # ALTER fails (locked table, insufficient privileges, etc.), skip the
        # column rather than failing the whole registration.
        for loc_col in ["region", "province", "city", "barangay", "vehicle_type"]:
            if loc_col not in columns:
                try:
                    cur.execute(f"ALTER TABLE riders ADD COLUMN {loc_col} VARCHAR(100) NULL")
                    columns.append(loc_col)
                except Exception:
                    pass

        cols = ["ridername", "rideremail", pw_col, "phone", "status"]
        values = [ridername, rideremail, hashed, phone, "pending"]

        optional = {
            "region": region,
            "province": province,
            "city": city,
            "barangay": barangay,
            "vehicle_type": vehicle_type,
        }
        for col_name, col_val in optional.items():
            if col_name in columns:
                cols.append(col_name)
                values.append(col_val)

        # Auto-fill any remaining NOT NULL column that has no DB default, so
        # an admin adding a new mandatory column to the riders table doesn't
        # break mobile registration. Strings get '', numerics get 0.
        already = {c.lower() for c in cols}
        for col_name, meta in column_meta.items():
            if col_name in already:
                continue
            col_type = (meta.get("Type") or "").lower()
            if any(t in col_type for t in ("int", "decimal", "double", "float", "bit")):
                fill = 0
            else:
                fill = ""
            cols.append(col_name)
            values.append(fill)

        # Handle driver's license file upload — multipart OR base64 in JSON
        license_path = ""
        if is_multipart:
            license_path = _save_upload(
                request.files.get('driverlicense'),
                prefix='license',
                allowed_exts=ALLOWED_IMAGE_EXT,
            )
        else:
            b64 = payload.get('driverlicense_base64') or ''
            filename = payload.get('driverlicense_filename') or 'license.jpg'
            if b64:
                license_path = _save_base64(b64, filename, prefix='license',
                                            allowed_exts=ALLOWED_IMAGE_EXT)

        if license_path:
            # image_path is the existing column in the riders table
            for img_col in ("image_path", "driverlicense_path"):
                if img_col in columns:
                    try:
                        idx = [c.lower() for c in cols].index(img_col)
                        values[idx] = license_path
                    except ValueError:
                        cols.append(img_col)
                        values.append(license_path)
                    break

        placeholders = ",".join(["%s"] * len(cols))
        sql = "INSERT INTO riders ({}) VALUES ({})".format(",".join(cols), placeholders)
        cur.execute(sql, tuple(values))
        new_rider_id = cur.lastrowid
        conn.commit()

        return _api_success(
            "Application submitted! Please wait for admin approval.",
            {"rider_id": new_rider_id, "rideremail": rideremail},
            201,
        )
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        import traceback
        print("=" * 60, flush=True)
        print("RIDER REGISTER FAILED:", repr(e), flush=True)
        traceback.print_exc()
        print("=" * 60, flush=True)
        return _api_error(
            "Server error during registration",
            {"error": str(e), "type": type(e).__name__},
            500,
        )
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


# Seller stats (/api/seller/stats/*) and rider orders (/api/rider/orders)
# are intentionally NOT defined here. The real handlers live in
# app/authentication.py and already support JWT (via _get_authenticated_seller_id
# and _get_rider_id_from_session) in addition to the web session, so mobile
# clients holding a token from /api/seller/login or /api/rider/login can call
# them directly.


# ---------------------------------------------------------------------------
# Seller — Products CRUD (mobile)
# ---------------------------------------------------------------------------
# These are JSON+multipart equivalents of the web routes:
#   /seller/manage-product           (HTML list)
#   /seller/manage/product (POST)    (HTML create/update via form)
#   /seller/remove/product/<id>      (HTML delete)
# Authentication is via the seller JWT issued by /api/seller/login.

ALLOWED_PRODUCT_IMG_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed_product_image(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_PRODUCT_IMG_EXT


def _seller_id_from_jwt() -> Optional[int]:
    """Resolve the seller's numeric ID from the current JWT.
    Mobile login puts the seller dict under additional_claims['seller'],
    and the JWT identity is the str(sellerID). Try the structured claim
    first, then the fallback identity."""
    try:
        claims = get_jwt() or {}
    except Exception:
        claims = {}
    seller_claim = claims.get("seller")
    if isinstance(seller_claim, dict):
        for k in ("sellerID", "sellerId", "id"):
            v = seller_claim.get(k)
            if v is not None:
                try:
                    return int(v)
                except (TypeError, ValueError):
                    pass

    identity = get_jwt_identity()
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def _resolve_upload_folder() -> str:
    """Mirror the path used by the web routes so mobile + web write to the
    same folder. Falls back to a project-relative `uploads/` if the Flask app
    config is not exposed."""
    # Prefer the live Flask app's configured UPLOAD_FOLDER.
    try:
        from flask import current_app
        configured = current_app.config.get("UPLOAD_FOLDER")
        if configured:
            return configured
    except Exception:
        pass
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "uploads")


def _serialize_product_row(row: Dict[str, Any]) -> Dict[str, Any]:
    image_path = row.get("image_path")
    image_url = None
    if image_path:
        try:
            image_url = url_for("static", filename=f"uploads/{image_path}", _external=False)
        except Exception:
            image_url = None
    return {
        "id":          row.get("productID"),
        "name":        row.get("name") or "",
        "price":       float(row.get("price") or 0),
        "description": row.get("description") or "",
        "category_id": row.get("categoryID"),
        "stock":       _coerce_stock(row.get("stock")),
        "image_path":  image_path,
        "image_url":   image_url,
    }


@api_bp.get("/seller/products")
@jwt_required()
def api_seller_products_list():
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM products WHERE sellerID = %s ORDER BY productID DESC",
            (seller_id,),
        )
        rows = cur.fetchall() or []
        return _api_success(
            "Products fetched",
            [_serialize_product_row(r) for r in rows],
        )
    except Exception as e:
        return _api_error("Server error fetching products", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/seller/products")
@jwt_required()
def api_seller_products_create():
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    # Accept multipart (with `image` file) OR plain JSON.
    if request.content_type and request.content_type.startswith("multipart/"):
        data = request.form or {}
    else:
        data = request.get_json(silent=True) or {}

    name        = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    price_raw   = data.get("price")
    stock_raw   = data.get("stock")
    category_id = data.get("category_id") or data.get("categoryID")

    if not name:
        return _api_error("Name is required", None, 400)

    try:
        price = float(price_raw) if price_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        return _api_error("Invalid price", None, 400)

    stock = _coerce_stock(stock_raw)
    category_id_int: Optional[int] = None
    if category_id not in (None, ""):
        try:
            category_id_int = int(category_id)
        except (TypeError, ValueError):
            return _api_error("Invalid category_id", None, 400)

    saved_image_name: Optional[str] = None
    file = request.files.get("image") if request.files else None
    if file and file.filename:
        if not _allowed_product_image(file.filename):
            return _api_error(
                "Invalid image file type (use png/jpg/jpeg/gif/webp)",
                None,
                400,
            )
        upload_folder = _resolve_upload_folder()
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except Exception:
            pass
        unique = f"prod_{seller_id}_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        try:
            file.save(os.path.join(upload_folder, unique))
            saved_image_name = unique
        except Exception as e:
            return _api_error("Failed to save image", {"error": str(e)}, 500)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            INSERT INTO products (name, price, description, categoryID, sellerID, stock, image_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (name, price, description, category_id_int, seller_id, str(stock), saved_image_name),
        )
        new_id = cur.lastrowid
        conn.commit()

        cur.execute("SELECT * FROM products WHERE productID = %s", (new_id,))
        row = cur.fetchone() or {}
        return _api_success("Product created", _serialize_product_row(row), 201)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error creating product", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.put("/seller/products/<int:product_id>")
@jwt_required()
def api_seller_products_update(product_id: int):
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    if request.content_type and request.content_type.startswith("multipart/"):
        data = request.form or {}
    else:
        data = request.get_json(silent=True) or {}

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        # Ownership check.
        cur.execute(
            "SELECT * FROM products WHERE productID = %s AND sellerID = %s",
            (product_id, seller_id),
        )
        existing = cur.fetchone()
        if not existing:
            return _api_error("Product not found or not yours", None, 404)

        # Build a partial update from whatever fields the client sent.
        updates: list = []
        params: list = []

        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return _api_error("Name cannot be blank", None, 400)
            updates.append("name = %s"); params.append(name)

        if "description" in data:
            updates.append("description = %s")
            params.append((data.get("description") or "").strip())

        if "price" in data:
            try:
                updates.append("price = %s"); params.append(float(data.get("price")))
            except (TypeError, ValueError):
                return _api_error("Invalid price", None, 400)

        if "stock" in data:
            updates.append("stock = %s"); params.append(str(_coerce_stock(data.get("stock"))))

        if "category_id" in data or "categoryID" in data:
            cid = data.get("category_id") or data.get("categoryID")
            if cid in (None, "", "null"):
                updates.append("categoryID = NULL")
            else:
                try:
                    updates.append("categoryID = %s"); params.append(int(cid))
                except (TypeError, ValueError):
                    return _api_error("Invalid category_id", None, 400)

        # Optional new image upload — replace stored path.
        file = request.files.get("image") if request.files else None
        if file and file.filename:
            if not _allowed_product_image(file.filename):
                return _api_error("Invalid image file type", None, 400)
            upload_folder = _resolve_upload_folder()
            try:
                os.makedirs(upload_folder, exist_ok=True)
            except Exception:
                pass
            unique = f"prod_{seller_id}_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            try:
                file.save(os.path.join(upload_folder, unique))
            except Exception as e:
                return _api_error("Failed to save image", {"error": str(e)}, 500)
            updates.append("image_path = %s"); params.append(unique)

        if not updates:
            return _api_error("No fields to update", None, 400)

        params.append(product_id)
        sql = f"UPDATE products SET {', '.join(updates)} WHERE productID = %s"
        cur.execute(sql, tuple(params))
        conn.commit()

        cur.execute("SELECT * FROM products WHERE productID = %s", (product_id,))
        row = cur.fetchone() or {}
        return _api_success("Product updated", _serialize_product_row(row))
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error updating product", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


# ---------------------------------------------------------------------------
# Seller — Chat (read-only, mobile)
# ---------------------------------------------------------------------------
# Conversation listing reuses /api/seller/chat/conversations on the main app
# (now header-aware). This endpoint returns the message history between the
# authenticated seller and a given user, in chronological order.

@api_bp.get("/seller/chat/messages")
@jwt_required()
def api_seller_chat_messages():
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    user_id_raw = request.args.get("user_id") or request.args.get("userID")
    if not user_id_raw:
        return _api_error("user_id is required", None, 400)
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return _api_error("Invalid user_id", None, 400)

    try:
        limit = int(request.args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 500))

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT chatID, userID, sellerID, messages, messages_image,
                   sender_role, is_read, created_at
              FROM chats
             WHERE sellerID = %s AND userID = %s
             ORDER BY chatID ASC
             LIMIT %s
            """,
            (seller_id, user_id, limit),
        )
        rows = cur.fetchall() or []
        items = [
            {
                "id":            r.get("chatID"),
                "user_id":       r.get("userID"),
                "seller_id":     r.get("sellerID"),
                "text":          r.get("messages") or "",
                "image":         r.get("messages_image") or "",
                "sender_role":   r.get("sender_role") or "user",
                "is_read":       bool(r.get("is_read")),
                "created_at":    str(r.get("created_at")) if r.get("created_at") else None,
                "from_seller":   (r.get("sender_role") or "").lower() == "seller",
            }
            for r in rows
        ]
        return _api_success("Messages fetched", items)
    except Exception as e:
        return _api_error("Server error fetching messages", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/seller/chat/messages")
@jwt_required()
def api_seller_send_message():
    """Seller sends a text message to a user."""
    from app.chat_controller import save_message
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)
    payload, err = _require_json()
    if err:
        return err
    user_id_raw = payload.get("user_id") or payload.get("userID")
    message = (payload.get("message") or payload.get("text") or "").strip()
    if not user_id_raw or not message:
        return _api_error("user_id and message are required", None, 400)
    try:
        msg = save_message("seller", int(seller_id), "user", int(user_id_raw), message)
        return _api_success("Message sent", {"message": msg})
    except Exception as e:
        return _api_error("Failed to send message", {"error": str(e)}, 500)


@api_bp.post("/user/messages")
@jwt_required()
def api_user_send_message():
    """User sends a text message to a seller."""
    from app.chat_controller import save_message
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)
    payload, err = _require_json()
    if err:
        return err
    seller_id_raw = payload.get("seller_id") or payload.get("sellerID")
    message = (payload.get("message") or payload.get("text") or "").strip()
    if not seller_id_raw or not message:
        return _api_error("seller_id and message are required", None, 400)
    try:
        msg = save_message("user", int(user_id), "seller", int(seller_id_raw), message)
        return _api_success("Message sent", {"message": msg})
    except Exception as e:
        return _api_error("Failed to send message", {"error": str(e)}, 500)


@api_bp.get("/rider/chat/messages")
@jwt_required()
def api_rider_chat_messages():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    partner_id_raw = request.args.get("partner_id") or request.args.get("id")
    partner_type = request.args.get("type", "user")

    if not partner_id_raw:
        return _api_error("partner_id is required", None, 400)
    try:
        partner_id = int(partner_id_raw)
    except (TypeError, ValueError):
        return _api_error("Invalid partner_id", None, 400)

    try:
        limit = int(request.args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 500))

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        if partner_type == 'seller':
            cur.execute(
                """
                SELECT chatID, userID, sellerID, riderID, messages, messages_image,
                       sender_role, is_read, created_at
                  FROM chats
                 WHERE riderID = %s AND sellerID = %s AND (userID IS NULL OR userID = 0)
                 ORDER BY chatID ASC
                 LIMIT %s
                """,
                (rider_id, partner_id, limit),
            )
        else:
            cur.execute(
                """
                SELECT chatID, userID, sellerID, riderID, messages, messages_image,
                       sender_role, is_read, created_at
                  FROM chats
                 WHERE riderID = %s AND userID = %s AND (sellerID IS NULL OR sellerID = 0)
                 ORDER BY chatID ASC
                 LIMIT %s
                """,
                (rider_id, partner_id, limit),
            )
        
        if not cur.rowcount:
             if partner_type == 'seller':
                 cur.execute(
                     "SELECT chatID, userID, sellerID, riderID, messages, messages_image, sender_role, is_read, created_at FROM chats WHERE riderID = %s AND sellerID = %s ORDER BY chatID ASC LIMIT %s",
                     (rider_id, partner_id, limit)
                 )
             else:
                 cur.execute(
                     "SELECT chatID, userID, sellerID, riderID, messages, messages_image, sender_role, is_read, created_at FROM chats WHERE riderID = %s AND userID = %s ORDER BY chatID ASC LIMIT %s",
                     (rider_id, partner_id, limit)
                 )

        rows = cur.fetchall() or []
        items = [
            {
                "id":            r.get("chatID"),
                "user_id":       r.get("userID"),
                "seller_id":     r.get("sellerID"),
                "rider_id":      r.get("riderID"),
                "text":          r.get("messages") or "",
                "image":         r.get("messages_image") or "",
                "sender_role":   r.get("sender_role") or "user",
                "is_read":       bool(r.get("is_read")),
                "created_at":    str(r.get("created_at")) if r.get("created_at") else None,
                "from_me":       (r.get("sender_role") or "").lower() == "rider",
            }
            for r in rows
        ]
        return _api_success("Messages fetched", items)
    except Exception as e:
        return _api_error("Server error fetching messages", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


# ---------------------------------------------------------------------------
# Seller — Profile (mobile)
# ---------------------------------------------------------------------------
# JSON+multipart equivalents of /seller/profile (web) and the password-change
# route. The mobile UI uses these to view + edit the logged-in seller.

PROFILE_ALLOWED_FIELDS = {
    "sellername", "selleremail", "contactnumber", "storename",
    "storedesc", "region", "province", "city", "barangay", "exact_address",
}


def _serialize_seller_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    """Mirrors the camelCase shape the mobile SellerProfile.fromJson reads,
    while still returning the raw snake_case fields for richer UIs."""
    image_path = row.get("storelogo_path") or None
    image_url = None
    if image_path:
        try:
            image_url = url_for("static", filename=f"uploads/{image_path}", _external=False)
        except Exception:
            image_url = None
    return {
        # camelCase keys read by the existing SellerProfile.fromJson
        "id":              row.get("sellerID"),
        "sellerID":        row.get("sellerID"),
        "name":            row.get("sellername") or "",
        "email":           row.get("selleremail") or "",
        "phone":           str(row.get("contactnumber") or ""),
        "businessName":    row.get("storename") or "",
        "businessAddress": row.get("exact_address") or "",
        # snake_case extras
        "sellername":     row.get("sellername"),
        "selleremail":    row.get("selleremail"),
        "contactnumber":  row.get("contactnumber"),
        "storename":      row.get("storename"),
        "storedesc":      row.get("storedesc"),
        "region":         row.get("region"),
        "province":       row.get("province"),
        "city":           row.get("city"),
        "barangay":       row.get("barangay"),
        "exact_address":  row.get("exact_address"),
        "status":         row.get("status"),
        "storelogo_path": image_path,
        "storelogo_url":  image_url,
    }


@api_bp.get("/seller/profile")
@jwt_required()
def api_seller_profile_get():
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM sellers WHERE sellerID = %s LIMIT 1", (seller_id,))
        row = cur.fetchone()
        if not row:
            return _api_error("Seller not found", None, 404)
        return _api_success("Profile fetched", _serialize_seller_profile(row))
    except Exception as e:
        return _api_error("Server error fetching profile", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.put("/seller/profile")
@jwt_required()
def api_seller_profile_update():
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    # Multipart (with optional `storelogo` image) OR JSON.
    if request.content_type and request.content_type.startswith("multipart/"):
        data = request.form or {}
    else:
        data = request.get_json(silent=True) or {}

    # Accept the mobile camelCase aliases too.
    alias_map = {
        "name":            "sellername",
        "email":           "selleremail",
        "phone":           "contactnumber",
        "businessName":    "storename",
        "businessAddress": "exact_address",
    }

    updates: list = []
    params: list = []

    # Resolve the field names the client sent into the actual columns.
    for raw_key, value in data.items():
        col = alias_map.get(raw_key, raw_key)
        if col not in PROFILE_ALLOWED_FIELDS:
            continue
        if col == "contactnumber":
            # INT column; coerce a phone string safely.
            try:
                num = int(str(value).lstrip("+").replace(" ", "").replace("-", "")) if value not in (None, "") else 0
            except ValueError:
                return _api_error("Invalid contact number", None, 400)
            if num > 2147483647:
                num = 2147483647
            updates.append("contactnumber = %s"); params.append(num)
        else:
            updates.append(f"{col} = %s")
            params.append(("" if value is None else str(value)).strip())

    # Optional logo upload.
    file = request.files.get("storelogo") if request.files else None
    if file and file.filename:
        if not _allowed_product_image(file.filename):
            return _api_error("Invalid logo file type", None, 400)
        upload_folder = _resolve_upload_folder()
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except Exception:
            pass
        unique = f"logo_{seller_id}_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        try:
            file.save(os.path.join(upload_folder, unique))
            updates.append("storelogo_path = %s"); params.append(unique)
        except Exception as e:
            return _api_error("Failed to save logo", {"error": str(e)}, 500)

    if not updates:
        return _api_error("No fields to update", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        params.append(seller_id)
        cur.execute(
            f"UPDATE sellers SET {', '.join(updates)} WHERE sellerID = %s",
            tuple(params),
        )
        conn.commit()

        cur.execute("SELECT * FROM sellers WHERE sellerID = %s", (seller_id,))
        row = cur.fetchone() or {}
        return _api_success("Profile updated", _serialize_seller_profile(row))
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error updating profile", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/seller/profile/change-password")
@jwt_required()
def api_seller_change_password():
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    payload, err = _require_json()
    if err:
        return err

    current = payload.get("current_password") or ""
    new_pw  = payload.get("new_password") or ""

    if not current or not new_pw:
        return _api_error("Both current and new password are required", None, 400)
    if len(new_pw) < 6:
        return _api_error("New password must be at least 6 characters", None, 400)
    if current == new_pw:
        return _api_error("New password must differ from the current one", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        pw_col = _select_password_column(cur, "sellers", ("password", "sellerpassword", "passwd"))
        if not pw_col:
            return _api_error("Server configuration error (password column)", None, 500)

        cur.execute(f"SELECT {pw_col} FROM sellers WHERE sellerID = %s", (seller_id,))
        row = cur.fetchone()
        if not row:
            return _api_error("Seller not found", None, 404)
        if not check_password_hash(row.get(pw_col) or "", current):
            return _api_error("Current password is incorrect", None, 400)

        cur.execute(
            f"UPDATE sellers SET {pw_col} = %s WHERE sellerID = %s",
            (generate_password_hash(new_pw), seller_id),
        )
        conn.commit()
        return _api_success("Password changed", None)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error changing password", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.delete("/seller/products/<int:product_id>")
@jwt_required()
def api_seller_products_delete(product_id: int):
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return _api_error("Not authenticated as a seller", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "DELETE FROM products WHERE productID = %s AND sellerID = %s",
            (product_id, seller_id),
        )
        if cur.rowcount == 0:
            return _api_error("Product not found or not yours", None, 404)
        conn.commit()
        return _api_success("Product deleted", {"id": product_id})
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error deleting product", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


# ---------------------------------------------------------------------------
# Rider — Mobile endpoints (JWT-based)
# ---------------------------------------------------------------------------

def _rider_id_from_jwt() -> Optional[int]:
    """Resolve the rider's numeric ID from the current JWT (mobile login)."""
    try:
        claims = get_jwt() or {}
    except Exception:
        claims = {}
    rider_claim = claims.get("rider")
    if isinstance(rider_claim, dict):
        for key in ("riderID", "riderId", "rider_id", "id"):
            val = rider_claim.get(key)
            if val is not None:
                try:
                    return int(val)
                except Exception:
                    pass
    try:
        identity = get_jwt_identity()
        return int(identity)
    except Exception:
        return None


@api_bp.get("/rider/stats/summary")
@jwt_required()
def api_rider_stats_summary():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT
                SUM(CASE WHEN LOWER(IFNULL(status,'')) = 'delivered' THEN 1 ELSE 0 END) AS total_deliveries,
                SUM(CASE WHEN LOWER(IFNULL(status,'')) IN ('pending','on_the_way','assigned_to_rider') THEN 1 ELSE 0 END) AS active_orders,
                SUM(CASE WHEN LOWER(IFNULL(status,'')) = 'delivered'
                         AND DATE(COALESCE(updated_at, created_at)) = CURDATE() THEN 1 ELSE 0 END) AS completed_today
            FROM seller_orders
            WHERE riderID = %s
        """, (rider_id,))
        row = cur.fetchone() or {}

        cur.execute("""
            SELECT
                SUM(CASE WHEN ft.rider_commission IS NOT NULL THEN ft.rider_commission ELSE 30.00 END) AS total_earnings,
                SUM(CASE
                    WHEN DATE(COALESCE(so.revenue_released_at, so.updated_at))
                         BETWEEN (CURDATE() - INTERVAL 6 DAY) AND CURDATE()
                    THEN CASE WHEN ft.rider_commission IS NOT NULL THEN ft.rider_commission ELSE 30.00 END
                    ELSE 0 END) AS earnings_week,
                SUM(CASE
                    WHEN YEAR(DATE(COALESCE(so.revenue_released_at, so.updated_at))) = YEAR(CURDATE())
                         AND MONTH(DATE(COALESCE(so.revenue_released_at, so.updated_at))) = MONTH(CURDATE())
                    THEN CASE WHEN ft.rider_commission IS NOT NULL THEN ft.rider_commission ELSE 30.00 END
                    ELSE 0 END) AS earnings_month
            FROM seller_orders so
            LEFT JOIN financial_transactions ft ON so.sellerOrderID = ft.order_id
            WHERE so.riderID = %s AND so.revenue_released = 1
        """, (rider_id,))
        fin = cur.fetchone() or {}

        return _api_success("ok", {
            "total_deliveries": int(row.get("total_deliveries") or 0),
            "active_orders":    int(row.get("active_orders") or 0),
            "completed_today":  int(row.get("completed_today") or 0),
            "total_earnings":   float(fin.get("total_earnings") or 0.0),
            "earnings_week":    float(fin.get("earnings_week") or 0.0),
            "earnings_month":   float(fin.get("earnings_month") or 0.0),
        })
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.get("/rider/orders/active")
@jwt_required()
def api_rider_orders_active():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT so.sellerOrderID, so.order_number, so.status, so.total_amount,
                   so.shipping_address, so.created_at,
                   s.storename, s.sellername,
                   s.exact_address, s.barangay, s.city, s.province, s.region,
                   u.username AS user_name
            FROM seller_orders so
            LEFT JOIN sellers s ON so.sellerID = s.sellerID
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.riderID = %s
              AND LOWER(IFNULL(so.status,'')) NOT IN ('delivered','cancelled')
            ORDER BY so.created_at DESC
        """, (rider_id,))
        rows = cur.fetchall() or []
        items = []
        for r in rows:
            items.append({
                "sellerOrderID":    r.get("sellerOrderID"),
                "order_number":     r.get("order_number") or "",
                "status":           r.get("status") or "pending",
                "total_amount":     float(r.get("total_amount") or 0.0),
                "shop_name":        r.get("storename") or r.get("sellername") or "Shop",
                "user_name":        r.get("user_name") or "Customer",
                "pickup_address":   ", ".join(filter(None, [
                    r.get("exact_address"), r.get("barangay"),
                    r.get("city"), r.get("province"), r.get("region"),
                ])),
                "delivery_address": r.get("shipping_address") or "",
                "created_at":       str(r.get("created_at") or ""),
            })
        return _api_success("ok", {"orders": items})
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.get("/rider/orders/delivered")
@jwt_required()
def api_rider_orders_delivered():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT so.sellerOrderID, so.order_number, so.status, so.total_amount,
                   so.shipping_address, so.created_at,
                   s.storename, s.sellername,
                   s.exact_address, s.barangay, s.city, s.province, s.region,
                   u.username AS user_name
            FROM seller_orders so
            LEFT JOIN sellers s ON so.sellerID = s.sellerID
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.riderID = %s
              AND LOWER(IFNULL(so.status,'')) = 'delivered'
            ORDER BY so.created_at DESC
        """, (rider_id,))
        rows = cur.fetchall() or []
        items = []
        for r in rows:
            items.append({
                "sellerOrderID":    r.get("sellerOrderID"),
                "order_number":     r.get("order_number") or "",
                "status":           r.get("status") or "delivered",
                "total_amount":     float(r.get("total_amount") or 0.0),
                "shop_name":        r.get("storename") or r.get("sellername") or "Shop",
                "user_name":        r.get("user_name") or "Customer",
                "pickup_address":   ", ".join(filter(None, [
                    r.get("exact_address"), r.get("barangay"),
                    r.get("city"), r.get("province"), r.get("region"),
                ])),
                "delivery_address": r.get("shipping_address") or "",
                "created_at":       str(r.get("created_at") or ""),
            })
        return _api_success("ok", {"orders": items})
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


# ── Proof of Delivery ─────────────────────────────────────────────────────

ALLOWED_POD_EXTENSIONS = {'jpg', 'jpeg', 'png'}
ALLOWED_POD_MIMES = {'image/jpeg', 'image/png'}
MAX_POD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _allowed_pod_file(filename: str, mime: str) -> bool:
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_POD_EXTENSIONS:
        return False
    # If the client sends a generic MIME (common from Flutter Web multipart),
    # trust the extension instead of rejecting.
    generic_mimes = {'application/octet-stream', 'binary/octet-stream', ''}
    if mime in generic_mimes:
        return True
    return mime in ALLOWED_POD_MIMES


@api_bp.post("/rider/orders/<int:order_id>/pod")
@jwt_required()
def api_rider_upload_pod(order_id: int):
    """Upload a Proof of Delivery image for a delivered order."""
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    if 'image' not in request.files:
        return _api_error("No image file provided", {"error": "Missing image field"}, 400)

    file = request.files['image']
    if not file or file.filename == '':
        return _api_error("No image selected", {"error": "Empty filename"}, 400)

    # Validate file size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_POD_SIZE_BYTES:
        return _api_error("File too large", {"error": "File exceeds 10 MB limit"}, 400)

    # Validate MIME type and extension
    mime = file.content_type or ''
    filename = secure_filename(file.filename)
    if not _allowed_pod_file(filename, mime):
        return _api_error(
            "Invalid file type",
            {"error": "Only JPG, JPEG, and PNG files are accepted"},
            400,
        )

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        # Verify the order belongs to this rider and is delivered
        cur.execute(
            "SELECT sellerOrderID, status, riderID FROM seller_orders WHERE sellerOrderID = %s LIMIT 1",
            (order_id,),
        )
        order = cur.fetchone()
        if not order:
            return _api_error("Order not found", None, 404)
        if int(order.get('riderID') or 0) != rider_id:
            return _api_error("Forbidden", {"error": "Order not assigned to you"}, 403)
        if (order.get('status') or '').lower() != 'delivered':
            return _api_error(
                "Order not delivered",
                {"error": "POD can only be uploaded for delivered orders"},
                400,
            )

        # Save file to uploads directory
        ext = filename.rsplit('.', 1)[-1].lower()
        unique_name = f"pod_{order_id}_{uuid.uuid4().hex}.{ext}"
        uploads_dir = os.path.join(PROJECT_ROOT, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, unique_name)
        file.save(save_path)

        # Build the public URL
        pod_url = f"/uploads/{unique_name}"

        # Upsert into proof_of_delivery (INSERT or UPDATE on duplicate seller_order_id)
        cur.execute(
            """
            INSERT INTO proof_of_delivery (seller_order_id, rider_id, image_path, upload_timestamp, file_type)
            VALUES (%s, %s, %s, NOW(), %s)
            ON DUPLICATE KEY UPDATE
                image_path       = VALUES(image_path),
                upload_timestamp = NOW(),
                file_type        = VALUES(file_type),
                updated_at       = NOW()
            """,
            (order_id, rider_id, pod_url, ext),
        )
        conn.commit()

        # Fetch the saved record to return upload_timestamp
        cur.execute(
            "SELECT image_path, upload_timestamp FROM proof_of_delivery WHERE seller_order_id = %s LIMIT 1",
            (order_id,),
        )
        row = cur.fetchone() or {}
        return _api_success("Proof of delivery uploaded", {
            "pod_image_url": row.get("image_path") or pod_url,
            "uploaded_at":   str(row.get("upload_timestamp") or ""),
        })
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.get("/orders/<int:order_id>/pod")
@jwt_required()
def api_get_pod(order_id: int):
    """Fetch the POD image for an order. Accessible by the owning customer, any rider, or admin."""
    claims = get_jwt()
    role = (claims.get('role') or claims.get('sub_role') or '').lower()
    identity = get_jwt_identity()

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        # Fetch order status
        cur.execute(
            "SELECT sellerOrderID, userID, status FROM seller_orders WHERE sellerOrderID = %s LIMIT 1",
            (order_id,),
        )
        order = cur.fetchone()
        if not order:
            return _api_success("ok", {"pod_image_url": None, "uploaded_at": None, "order_status": None})

        order_status = (order.get('status') or '').lower()

        # Customer role: verify ownership (return null silently if not owner)
        if role == 'user':
            user_id = None
            try:
                user_id = int(identity)
            except Exception:
                pass
            if user_id != int(order.get('userID') or -1):
                return _api_success("ok", {"pod_image_url": None, "uploaded_at": None, "order_status": None})

        # Only return POD if order is delivered
        if order_status != 'delivered':
            return _api_success("ok", {
                "pod_image_url": None,
                "uploaded_at":   None,
                "order_status":  order_status,
            })

        # Fetch POD record
        cur.execute(
            "SELECT image_path, upload_timestamp FROM proof_of_delivery WHERE seller_order_id = %s LIMIT 1",
            (order_id,),
        )
        pod = cur.fetchone()
        if not pod:
            return _api_success("ok", {
                "pod_image_url": None,
                "uploaded_at":   None,
                "order_status":  order_status,
            })

        return _api_success("ok", {
            "pod_image_url": pod.get("image_path"),
            "uploaded_at":   str(pod.get("upload_timestamp") or ""),
            "order_status":  order_status,
        })
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/rider/orders/<int:order_id>/respond")
@jwt_required()
def api_rider_order_respond(order_id: int):
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    payload, err = _require_json()
    if err:
        return err
    action = (payload.get("action") or "").lower()
    if action not in ("accept", "decline"):
        return _api_error("action must be 'accept' or 'decline'", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT sellerID, userID, order_number FROM seller_orders "
            "WHERE sellerOrderID = %s AND riderID = %s LIMIT 1",
            (order_id, rider_id),
        )
        row = cur.fetchone()
        if not row:
            return _api_error("Order not found or not assigned to you", None, 404)

        if action == "accept":
            try:
                cur.execute(
                    "UPDATE seller_orders SET status='picked_up', updated_at=NOW() "
                    "WHERE sellerOrderID=%s", (order_id,)
                )
            except Exception:
                pass
            try:
                cur.execute(
                    "INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s,%s,%s)",
                    (order_id, "picked_up", "Rider accepted assignment"),
                )
            except Exception:
                pass
        else:
            try:
                cur.execute(
                    "UPDATE seller_orders SET status='packed', riderID=NULL, updated_at=NOW() "
                    "WHERE sellerOrderID=%s", (order_id,)
                )
            except Exception:
                pass
            try:
                cur.execute(
                    "INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s,%s,%s)",
                    (order_id, "packed", "Rider declined assignment"),
                )
            except Exception:
                pass

        conn.commit()
        return _api_success(f"Order {action}ed", None)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/rider/orders/<int:order_id>/status")
@jwt_required()
def api_rider_order_status(order_id: int):
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    payload, err = _require_json()
    if err:
        return err
    status = (payload.get("status") or "").strip()
    if status not in ("on_the_way", "delivered"):
        return _api_error("status must be 'on_the_way' or 'delivered'", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT sellerID, userID FROM seller_orders "
            "WHERE sellerOrderID=%s AND riderID=%s LIMIT 1",
            (order_id, rider_id),
        )
        if not cur.fetchone():
            return _api_error("Order not found or not assigned to you", None, 404)
        cur.execute(
            "UPDATE seller_orders SET status=%s, updated_at=NOW() WHERE sellerOrderID=%s",
            (status, order_id),
        )
        label = "Order is on the way" if status == "on_the_way" else "Order delivered"
        try:
            cur.execute(
                "INSERT INTO order_status_history (sellerOrderID, status, message) VALUES (%s,%s,%s)",
                (order_id, status, label),
            )
        except Exception:
            pass
        conn.commit()
        return _api_success("Status updated", None)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/rider/orders/<int:order_id>/location")
@jwt_required()
def api_rider_update_location(order_id: int):
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    payload, err = _require_json()
    if err:
        return err
    lat = payload.get("lat")
    lng = payload.get("lng")
    if lat is None or lng is None:
        return _api_error("lat and lng are required", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE seller_orders SET rider_lat=%s, rider_lng=%s, rider_updated_at=NOW() "
            "WHERE sellerOrderID=%s AND riderID=%s",
            (lat, lng, order_id, rider_id),
        )
        conn.commit()
        return _api_success("Location updated")
    except Exception as e:
        return _api_error(f"Failed to update location: {e}", None, 500)
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.get("/orders/<int:order_id>/rider-location")
@jwt_required()
def api_get_rider_location(order_id: int):
    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT rider_lat, rider_lng, rider_updated_at, status "
            "FROM seller_orders WHERE sellerOrderID=%s LIMIT 1",
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            return _api_error("Order not found", None, 404)
        return _api_success("ok", {
            "lat":        float(row["rider_lat"]) if row.get("rider_lat") is not None else None,
            "lng":        float(row["rider_lng"]) if row.get("rider_lng") is not None else None,
            "updated_at": str(row["rider_updated_at"]) if row.get("rider_updated_at") else None,
            "status":     row.get("status"),
        })
    except Exception as e:
        return _api_error(f"Failed to fetch location: {e}", None, 500)
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.get("/rider/profile/me")
@jwt_required()
def api_rider_profile_get():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT riderID, ridername, rideremail, phone, vehicle_type, profile_path, status "
            "FROM riders WHERE riderID=%s LIMIT 1",
            (rider_id,),
        )
        row = cur.fetchone()
        if not row:
            return _api_error("Rider not found", None, 404)
        return _api_success("ok", {
            "riderID":      int(row.get("riderID") or rider_id),
            "name":         row.get("ridername") or "",
            "email":        row.get("rideremail") or "",
            "phone":        row.get("phone") or "",
            "vehicle_type": row.get("vehicle_type") or "",
            "profile_path": row.get("profile_path") or "",
            "status":       row.get("status") or "",
        })
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.put("/rider/profile/me")
@jwt_required()
def api_rider_profile_update():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    if request.content_type and request.content_type.startswith("multipart/"):
        data = request.form or {}
    else:
        data = request.get_json(silent=True) or {}

    name         = (data.get("ridername") or data.get("name") or "").strip()
    phone        = (data.get("phone") or "").strip()
    vehicle_type = (data.get("vehicle_type") or "").strip()

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        fields, values = [], []
        if name:
            fields.append("ridername = %s"); values.append(name)
        if phone:
            fields.append("phone = %s"); values.append(phone)
        if vehicle_type:
            fields.append("vehicle_type = %s"); values.append(vehicle_type)
        if fields:
            values.append(rider_id)
            cur.execute(
                f"UPDATE riders SET {', '.join(fields)} WHERE riderID=%s",
                tuple(values),
            )
            conn.commit()
        return _api_success("Profile updated", None)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/rider/profile/change-password")
@jwt_required()
def api_rider_change_password():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return _api_error("Not authenticated as a rider", None, 401)

    payload, err = _require_json()
    if err:
        return err

    current  = payload.get("current_password") or ""
    new_pass = payload.get("new_password") or ""
    confirm  = payload.get("confirm_password") or ""

    if not current or not new_pass:
        return _api_error("current_password and new_password are required", None, 400)
    if new_pass != confirm:
        return _api_error("Passwords do not match", None, 400)
    if len(new_pass) < 6:
        return _api_error("Password must be at least 6 characters", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        pw_col = _select_password_column(cur, "riders", ("riderpass", "password", "passwd"))
        if not pw_col:
            return _api_error("Server configuration error", None, 500)
        cur.execute(f"SELECT {pw_col} FROM riders WHERE riderID=%s LIMIT 1", (rider_id,))
        row = cur.fetchone()
        if not row or not check_password_hash(row.get(pw_col) or "", current):
            return _api_error("Current password is incorrect", None, 400)
        cur.execute(
            f"UPDATE riders SET {pw_col}=%s WHERE riderID=%s",
            (generate_password_hash(new_pass), rider_id),
        )
        conn.commit()
        return _api_success("Password updated", None)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

# ---------------------------------------------------------------------------
# User â€” Saved Address
# ---------------------------------------------------------------------------

def _user_id_from_jwt() -> Optional[int]:
    try:
        # JWT identity IS the user_id (set as str(user_id) in /api/login and /api/register).
        uid = get_jwt_identity()
        if uid is not None:
            return int(uid)
        # Fallback: check extra claims in case of future token shape changes.
        claims = get_jwt() or {}
        extra = claims.get("user_id") or claims.get("sub")
        return int(extra) if extra is not None else None
    except Exception:
        return None



# ---------------------------------------------------------------------------
# User — Orders (mobile)
# ---------------------------------------------------------------------------

@api_bp.get("/user/orders")
@jwt_required()
def api_user_orders_list():
    """Return the authenticated user's order history (seller_orders) with product items and POD."""
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)

    page = _safe_int(request.args.get("page", 1), 1)
    page_size = _safe_int(request.args.get("page_size", 20), 20)
    offset = (page - 1) * page_size

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        # Fetch confirmed orders from seller_orders (matches web behaviour)
        cur.execute(
            """
            SELECT so.sellerOrderID, so.order_number, so.total_amount,
                   so.shipping_address, so.contact_number, so.payment_method,
                   so.status, so.created_at, so.updated_at,
                   so.buyer_received, so.buyer_received_at,
                   s.storename, s.sellername
              FROM seller_orders so
              LEFT JOIN sellers s ON so.sellerID = s.sellerID
             WHERE so.userID = %s AND (so.status IS NULL OR so.status != 'cancelled')
             ORDER BY so.created_at DESC
             LIMIT %s OFFSET %s
            """,
            (user_id, page_size, offset),
        )
        orders_raw = cur.fetchall() or []

        orders = []
        for o in orders_raw:
            seller_order_id = o.get("sellerOrderID")

            # Fetch line items
            cur.execute(
                """
                SELECT soi.productID, soi.quantity, soi.price,
                       p.name, p.image_path
                  FROM seller_order_items soi
                  LEFT JOIN products p ON p.productID = soi.productID
                 WHERE soi.sellerOrderID = %s
                """,
                (seller_order_id,),
            )
            items_raw = cur.fetchall() or []
            items = [
                {
                    "product_id":  r.get("productID"),
                    "name":        r.get("name") or "",
                    "quantity":    int(r.get("quantity") or 0),
                    "price":       float(r.get("price") or 0),
                    "total_price": float(r.get("price") or 0) * int(r.get("quantity") or 0),
                    "image_path":  r.get("image_path") or "",
                }
                for r in items_raw
            ]

            # Fetch POD if delivered
            pod_image_url = None
            pod_uploaded_at = None
            if (o.get("status") or "").lower() == "delivered":
                cur.execute(
                    "SELECT image_path, upload_timestamp FROM proof_of_delivery WHERE seller_order_id = %s LIMIT 1",
                    (seller_order_id,),
                )
                pod = cur.fetchone()
                if pod:
                    pod_image_url = pod.get("image_path")
                    pod_uploaded_at = str(pod.get("upload_timestamp") or "")

            orders.append({
                "id":               seller_order_id,
                "sellerOrderID":    seller_order_id,
                "order_number":     o.get("order_number") or f"#{seller_order_id}",
                "status":           o.get("status") or "pending",
                "totalAmount":      float(o.get("total_amount") or 0),
                "total":            float(o.get("total_amount") or 0),
                "shipping_address": o.get("shipping_address") or "",
                "contact_number":   o.get("contact_number") or "",
                "payment_method":   o.get("payment_method") or "",
                "shop_name":        o.get("storename") or o.get("sellername") or "",
                "orderDate":        str(o.get("created_at") or ""),
                "created_at":       str(o.get("created_at") or ""),
                "buyer_received":   bool(o.get("buyer_received")),
                "buyer_received_at": str(o.get("buyer_received_at") or ""),
                "pod_image_url":    pod_image_url,
                "pod_uploaded_at":  pod_uploaded_at,
                "items":            items,
            })

        return _api_success("Orders fetched", {"orders": orders, "page": page, "page_size": page_size})
    except Exception as e:
        return _api_error("Server error fetching orders", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/user/orders/<int:order_id>/confirm-received")
@jwt_required()
def api_user_confirm_received(order_id: int):
    """Mark an order as received by the buyer."""
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT sellerOrderID, userID, status, buyer_received FROM seller_orders WHERE sellerOrderID = %s LIMIT 1",
            (order_id,),
        )
        order = cur.fetchone()
        if not order:
            return _api_error("Order not found", None, 404)
        if int(order.get("userID") or 0) != user_id:
            return _api_error("Forbidden", None, 403)
        if (order.get("status") or "").lower() != "delivered":
            return _api_error("Order is not delivered yet", {"error": "Only delivered orders can be confirmed"}, 400)
        if order.get("buyer_received"):
            return _api_success("Already confirmed", {"buyer_received": True})

        cur.execute(
            "UPDATE seller_orders SET buyer_received = 1, buyer_received_at = NOW() WHERE sellerOrderID = %s",
            (order_id,),
        )
        conn.commit()
        return _api_success("Order confirmed as received", {"buyer_received": True})
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.get("/user/orders/<int:order_id>")
@jwt_required()
def api_user_order_detail(order_id: int):
    """Return full details for a single user order."""
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT pendingID, order_number, total_amount, shipping_address,
                   contact_number, payment_method, status, created_at
              FROM user_pending_orders
             WHERE pendingID = %s AND userID = %s
             LIMIT 1
            """,
            (order_id, user_id),
        )
        o = cur.fetchone()
        if not o:
            return _api_error("Order not found", None, 404)

        cur.execute(
            """
            SELECT i.productID, i.quantity, i.price, i.total_price,
                   p.name, p.image_path, p.description
              FROM user_pending_order_items i
              LEFT JOIN products p ON p.productID = i.productID
             WHERE i.pendingID = %s
            """,
            (order_id,),
        )
        items_raw = cur.fetchall() or []
        items = [
            {
                "product_id":   r.get("productID"),
                "name":         r.get("name") or "",
                "quantity":     int(r.get("quantity") or 0),
                "price":        float(r.get("price") or 0),
                "total_price":  float(r.get("total_price") or 0),
                "image_path":   r.get("image_path") or "",
                "description":  r.get("description") or "",
            }
            for r in items_raw
        ]
        order = {
            "id":               o.get("pendingID"),
            "order_number":     o.get("order_number") or f"#{o.get('pendingID')}",
            "status":           o.get("status") or "pending",
            "totalAmount":      float(o.get("total_amount") or 0),
            "total":            float(o.get("total_amount") or 0),
            "shipping_address": o.get("shipping_address") or "",
            "contact_number":   o.get("contact_number") or "",
            "payment_method":   o.get("payment_method") or "",
            "orderDate":        str(o.get("created_at") or ""),
            "created_at":       str(o.get("created_at") or ""),
            "items":            items,
        }
        return _api_success("Order fetched", {"order": order})
    except Exception as e:
        return _api_error("Server error fetching order", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.get("/user/address")
@jwt_required()
def api_user_address_get():
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)
    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SHOW TABLES LIKE 'user_saved_addresses'")
            if cur.fetchone():
                cur.execute("SELECT * FROM user_saved_addresses WHERE userID = %s LIMIT 1", (user_id,))
                row = cur.fetchone()
                if row:
                    return _api_success("Address fetched", {
                        "region": row.get("region") or "",
                        "province": row.get("province") or "",
                        "city": row.get("city") or "",
                        "barangay": row.get("barangay") or "",
                        "home_address": row.get("home_address") or "",
                        "contact_number": row.get("contact_number") or "",
                    })
        except Exception:
            pass
        return _api_success("No saved address", None)
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


@api_bp.post("/user/address")
@jwt_required()
def api_user_address_save():
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)
    payload, err = _require_json()
    if err:
        return err
    region = (payload.get("region") or "").strip()
    province = (payload.get("province") or "").strip()
    city = (payload.get("city") or "").strip()
    barangay = (payload.get("barangay") or "").strip()
    home_address = (payload.get("home_address") or "").strip()
    contact_number = (payload.get("contact_number") or "").strip()
    if not all([region, province, city, barangay, home_address, contact_number]):
        return _api_error("Missing address fields", None, 400)
    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_saved_addresses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    userID INT NOT NULL UNIQUE,
                    region VARCHAR(255), province VARCHAR(255), city VARCHAR(255),
                    barangay VARCHAR(255), home_address TEXT, contact_number VARCHAR(64),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        except Exception:
            pass
        cur.execute("SELECT userID FROM user_saved_addresses WHERE userID = %s LIMIT 1", (user_id,))
        if cur.fetchone():
            cur.execute(
                "UPDATE user_saved_addresses SET region=%s,province=%s,city=%s,barangay=%s,home_address=%s,contact_number=%s WHERE userID=%s",
                (region, province, city, barangay, home_address, contact_number, user_id)
            )
        else:
            cur.execute(
                "INSERT INTO user_saved_addresses (userID,region,province,city,barangay,home_address,contact_number) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (user_id, region, province, city, barangay, home_address, contact_number)
            )
        conn.commit()
        return _api_success("Address saved")
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return _api_error("Server error", {"error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass


# ---------------------------------------------------------------------------
# User â€” Checkout (mobile)
# ---------------------------------------------------------------------------


@api_bp.post("/shipping/estimate")
@jwt_required()
def api_shipping_estimate():
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)

    payload, err = _require_json()
    if err:
        return err

    region = (payload.get("region") or "").strip()
    province = (payload.get("province") or "").strip()
    city = (payload.get("city") or "").strip()
    barangay = (payload.get("barangay") or "").strip()
    if not all([region, province, city, barangay]):
        return _api_error("Missing delivery address fields", None, 400)

    product_ids = []
    raw_items = payload.get("items")
    raw_product_id = payload.get("product_id") or payload.get("direct_product_id")
    if isinstance(raw_items, list):
        for value in raw_items:
            try:
                product_ids.append(int(value))
            except (TypeError, ValueError):
                pass
    elif raw_product_id is not None:
        try:
            product_ids.append(int(raw_product_id))
        except (TypeError, ValueError):
            pass

    if not product_ids:
        return _api_error("Missing product selection", None, 400)

    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)

    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        placeholders = ','.join(['%s'] * len(product_ids))
        cur.execute(
            f"SELECT productID, sellerID FROM products WHERE productID IN ({placeholders})",
            tuple(product_ids),
        )
        rows = cur.fetchall() or []
        seen_sellers = set()
        shipping_fee = 0.0
        for row in rows:
            seller_id = row.get('sellerID')
            if seller_id in seen_sellers:
                continue
            seen_sellers.add(seller_id)
            shipping_fee += estimate_shipping_fee(
                _get_seller_pickup_location(cur, seller_id) if seller_id else {},
                {'region': region, 'province': province, 'city': city, 'barangay': barangay},
            )

        return _api_success("Shipping estimate calculated", {
            'shipping_fee': round(float(max(shipping_fee, DEFAULT_SHIPPING_FEE)), 2),
        })
    except Exception as e:
        return _api_error("Server error", {"error": str(e)}, 500)
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

@api_bp.post("/checkout")
@jwt_required()
def api_checkout():
    import datetime, random
    user_id = _user_id_from_jwt()
    if not user_id:
        return _api_error("Not authenticated as a user", None, 401)
    payload, err = _require_json()
    if err:
        return err
    region = (payload.get("region") or "").strip()
    province = (payload.get("province") or "").strip()
    city = (payload.get("city") or "").strip()
    barangay = (payload.get("barangay") or "").strip()
    home_address = (payload.get("home_address") or "").strip()
    contact_number = (payload.get("contact_number") or "").strip()
    payment_method = (payload.get("payment_method") or "cash_on_delivery").strip()
    selected_ids_raw = payload.get("items")
    if not all([region, province, city, barangay, home_address, contact_number]):
        return _api_error("Please fill in all required address fields", None, 400)
    try:
        conn = _get_db_connection()
    except Exception:
        return _api_error("Database unavailable", None, 500)
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.cartID, c.productID, c.quantity,
                   p.name, p.price, p.stock, p.sellerID, p.image_path
              FROM cart c JOIN products p ON c.productID = p.productID
             WHERE c.userID = %s
        """, (user_id,))
        all_items = cur.fetchall() or []
        if selected_ids_raw and isinstance(selected_ids_raw, list):
            try:
                sel_set = set(int(x) for x in selected_ids_raw)
                cart_items = [i for i in all_items if i["productID"] in sel_set]
            except (TypeError, ValueError):
                cart_items = all_items
        else:
            cart_items = all_items
        if not cart_items:
            return _api_error("Cart is empty or no items selected", None, 400)
        shipping_address = f"{home_address}, {barangay}, {city}, {province}, {region}"
        delivery_location = {
            'region': region,
            'province': province,
            'city': city,
            'barangay': barangay,
        }
        has_shipping_fee_col = False
        try:
            cur.execute("SHOW COLUMNS FROM user_pending_orders LIKE 'shipping_fee'")
            has_shipping_fee_col = cur.fetchone() is not None
        except Exception:
            pass
        generated_order_numbers = []
        generated_pending_ids = []

        seller_groups = _group_checkout_items_by_seller(cart_items)
        for index, seller_group in enumerate(seller_groups):
            group_items = seller_group['items']
            seller_id = seller_group.get('seller_id')
            shipping_fee = estimate_shipping_fee(
                _get_seller_pickup_location(cur, seller_id) if seller_id else {},
                delivery_location,
            )

            normalized_items = []
            order_subtotal = 0.0
            for item in group_items:
                req_qty = int(item.get("quantity") or 0)
                prod_id = item["productID"]
                if req_qty <= 0:
                    conn.rollback()
                    return _api_error(f"Invalid quantity for product {prod_id}", None, 400)
                cur.execute(
                    "UPDATE products SET stock=stock-%s WHERE productID=%s AND stock>=%s",
                    (req_qty, prod_id, req_qty)
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    return _api_error(
                        f'Insufficient stock for "{item.get("name") or prod_id}"',
                        {"product_id": prod_id, "available_stock": int(item.get("stock") or 0)}, 400
                    )
                item_price = float(item["price"])
                item_total = item_price * req_qty
                order_subtotal += item_total
                normalized_items.append((item, prod_id, req_qty, item_price, item_total))

            now = datetime.datetime.now()
            order_number = (
                f"BB{now.strftime('%Y%m%d%H%M%S')}"
                f"{now.microsecond:06d}"
                f"{random.randint(10000, 99999)}{index}{user_id}"
            )
            order_total = order_subtotal + shipping_fee

            if has_shipping_fee_col:
                cur.execute("""
                    INSERT INTO user_pending_orders
                        (userID,order_number,total_amount,shipping_fee,shipping_address,contact_number,payment_method,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'confirmed')
                """, (user_id, order_number, order_total, shipping_fee,
                      shipping_address, contact_number, payment_method))
            else:
                cur.execute("""
                    INSERT INTO user_pending_orders
                        (userID,order_number,total_amount,shipping_address,contact_number,payment_method,status)
                    VALUES (%s,%s,%s,%s,%s,%s,'confirmed')
                """, (user_id, order_number, order_total,
                      shipping_address, contact_number, payment_method))
            pending_id = cur.lastrowid
            generated_pending_ids.append(pending_id)
            generated_order_numbers.append(order_number)

            for item, prod_id, req_qty, item_price, item_total in normalized_items:
                cur.execute(
                    "INSERT INTO user_pending_order_items (pendingID,productID,quantity,price,total_price) VALUES (%s,%s,%s,%s,%s)",
                    (pending_id, prod_id, req_qty, item_price, item_total)
                )

            if seller_id:
                cur.execute("""
                    INSERT INTO seller_orders
                        (originalPendingID,userID,sellerID,order_number,total_amount,
                         shipping_fee,shipping_address,contact_number,payment_method,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
                """, (pending_id, user_id, seller_id, order_number, order_total,
                      shipping_fee, shipping_address, contact_number, payment_method))
                seller_order_id = cur.lastrowid
                for item, prod_id, req_qty, item_price, item_total in normalized_items:
                    cur.execute(
                        "INSERT INTO seller_order_items (sellerOrderID,productID,quantity,price,total_price) VALUES (%s,%s,%s,%s,%s)",
                        (seller_order_id, prod_id, req_qty, item_price, item_total)
                    )
                cur.execute(
                    "INSERT INTO order_status_history (sellerOrderID,status,message) VALUES (%s,'pending','Order confirmed and received by seller')",
                    (seller_order_id,)
                )

            for _, prod_id, _, _, _ in normalized_items:
                cur.execute(
                    "DELETE FROM cart WHERE userID=%s AND productID=%s",
                    (user_id, prod_id)
                )
        # Silently persist address for next checkout
        try:
            cur.execute("SHOW TABLES LIKE 'user_saved_addresses'")
            if cur.fetchone():
                cur.execute("SELECT userID FROM user_saved_addresses WHERE userID=%s LIMIT 1", (user_id,))
                if cur.fetchone():
                    cur.execute(
                        "UPDATE user_saved_addresses SET region=%s,province=%s,city=%s,barangay=%s,home_address=%s,contact_number=%s WHERE userID=%s",
                        (region, province, city, barangay, home_address, contact_number, user_id)
                    )
                else:
                    cur.execute(
                        "INSERT INTO user_saved_addresses (userID,region,province,city,barangay,home_address,contact_number) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (user_id, region, province, city, barangay, home_address, contact_number)
                    )
        except Exception:
            pass
        conn.commit()
        return _api_success("Orders placed successfully", {
            "order_numbers": generated_order_numbers,
            "pending_ids": generated_pending_ids,
        })
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        msg = str(e)
        if "Duplicate entry" in msg and "order_number" in msg:
            msg = "Duplicate order number, please try again."
        return _api_error(f"Error processing order: {msg}", None, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass
