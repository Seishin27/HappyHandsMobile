"""
Seller API endpoints for mobile app integration.

INSTALLATION INSTRUCTIONS:
1. Copy this file to: ../app/seller_api.py
2. Register the blueprint in run.py or __init__.py:
   
   from app.seller_api import seller_api_bp
   app.register_blueprint(seller_api_bp)

3. Restart Flask server

This module provides REST API endpoints for seller product and order management,
enabling bidirectional sync between the web e-commerce platform and Flutter mobile app.

Endpoints:
- GET    /api/seller/products              - List seller's products (paginated)
- POST   /api/seller/products              - Create new product
- PUT    /api/seller/products/<id>         - Update product
- DELETE /api/seller/products/<id>         - Delete product
- POST   /api/seller/products/upload-images - Upload product images
- GET    /api/seller/orders                - List seller's orders (paginated)
- GET    /api/seller/orders/<id>           - Get order details
- PUT    /api/seller/orders/<id>/status    - Update order status
"""

import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from werkzeug.utils import secure_filename

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
except Exception:
    pass

from app.db import get_db as _get_db_connection

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create blueprint
seller_api_bp = Blueprint("seller_api", __name__, url_prefix="/api/seller")


def _get_authenticated_seller_id() -> Optional[int]:
    """
    Extract seller ID from JWT token.
    
    Returns:
        Seller ID if authenticated as seller, None otherwise
    """
    try:
        claims = get_jwt()
        seller_data = claims.get("seller")
        if seller_data and isinstance(seller_data, dict):
            return seller_data.get("sellerID")
        return None
    except Exception:
        return None


def _api_success(data: Any = None, message: str = "Success") -> tuple:
    """Return success response."""
    return jsonify({"success": True, "message": message, "data": data}), 200


def _api_error(message: str, status_code: int = 400, errors: Any = None) -> tuple:
    """Return error response."""
    response = {"success": False, "message": message}
    if errors:
        response["errors"] = errors
    return jsonify(response), status_code


def _allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_decimal_to_float(item) for item in obj]
    return obj


# ============================================================================
# PRODUCT MANAGEMENT ENDPOINTS
# ============================================================================

@seller_api_bp.route('/products', methods=['GET'])
@jwt_required()
def get_seller_products():
    """
    Get paginated list of seller's products.
    
    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)
    
    Returns:
        JSON response with products list
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    # Get pagination parameters
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(100, max(1, int(request.args.get('page_size', 20))))
    offset = (page - 1) * page_size
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Fetch products for this seller
        query = """
            SELECT 
                productID as id,
                name as name,
                description as description,
                price as price,
                categoryID as category,
                stock as stock_quantity,
                image_path as images,
                created_at,
                updated_at
            FROM products
            WHERE sellerID = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (seller_id, page_size, offset))
        products = cur.fetchall()
        
        # Process products
        for product in products:
            # Convert image_path to list
            if product.get('images'):
                images_str = product['images']
                if isinstance(images_str, str):
                    product['images'] = [img.strip() for img in images_str.split(',') if img.strip()]
                else:
                    product['images'] = []
            else:
                product['images'] = []
            
            # Convert Decimal to float
            if product.get('price'):
                product['price'] = float(product['price'])
        
        # Get total count
        cur.execute("SELECT COUNT(*) as total FROM products WHERE sellerID = %s", (seller_id,))
        total = cur.fetchone()['total']
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "products": products,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching seller products: {e}")
        return _api_error(f"Failed to fetch products: {str(e)}", 500)


@seller_api_bp.route('/products', methods=['POST'])
@jwt_required()
def create_seller_product():
    """
    Create a new product.

    Accepts EITHER:
      - multipart/form-data  (Flutter — fields in request.form, optional file in request.files['image'])
      - application/json     (web / direct API calls)

    Form / JSON fields:
        name (str): Product name (required)
        description (str): Product description
        price (float): Product price (required)
        category_id / category (str): Category ID
        stock (int): Stock quantity (default: 0)
        image (file, multipart only): Product image to upload

    Returns:
        JSON response with created product
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)

    # ── Parse request body (multipart OR JSON) ───────────────────────────────
    is_multipart = request.content_type and 'multipart/form-data' in request.content_type
    if is_multipart:
        form = request.form
        name        = form.get('name', '').strip()
        price_raw   = form.get('price', '')
        description = form.get('description', '').strip()
        category    = (form.get('category_id') or form.get('category', '')).strip()
        stock_raw   = form.get('stock', '0')
    else:
        data = request.get_json(silent=True)
        if not data:
            return _api_error("Invalid request: JSON body or multipart/form-data required", 400)
        name        = data.get('name', '').strip()
        price_raw   = data.get('price', '')
        description = data.get('description', '').strip()
        category    = (data.get('category_id') or data.get('category', '')).strip()
        stock_raw   = data.get('stock', 0)

    # ── Validate required fields ─────────────────────────────────────────────
    if not name:
        return _api_error("Validation error: Product name is required", 400, {"name": "Required"})

    try:
        price = float(price_raw)
    except (TypeError, ValueError):
        return _api_error("Validation error: Valid price is required", 400, {"price": "Must be a number"})

    if price < 0:
        return _api_error("Validation error: Price must be >= 0", 400, {"price": "Must be >= 0"})

    try:
        stock_quantity = max(0, int(stock_raw))
    except (TypeError, ValueError):
        stock_quantity = 0

    # ── Handle uploaded images (multipart only, up to 4 slots: image0…image3) ──
    saved_images = []
    if is_multipart:
        for i in range(4):
            f = request.files.get(f'image{i}')
            if f and f.filename and _allowed_file(f.filename):
                try:
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    filename = secure_filename(f.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"prod_seller{seller_id}_{timestamp}_{i}_{filename}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    f.save(filepath)
                    saved_images.append(filename)
                except Exception as img_err:
                    print(f"Warning: could not save image{i}: {img_err}")
    image_path_str = ','.join(saved_images)

    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Insert product
        query = """
            INSERT INTO products
            (name, description, price, categoryID,
             stock, image_path, sellerID, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        cur.execute(query, (name, description, price, category, stock_quantity, image_path_str, seller_id))
        conn.commit()

        product_id = cur.lastrowid

        # Fetch the created product
        cur.execute("""
            SELECT
                productID as id,
                name as name,
                description as description,
                price as price,
                categoryID as category,
                stock as stock_quantity,
                image_path as images,
                created_at,
                updated_at
            FROM products
            WHERE productID = %s
        """, (product_id,))
        product = cur.fetchone()

        # Process images — split comma-separated filename(s) into a list
        if product.get('images'):
            product['images'] = [img.strip() for img in product['images'].split(',') if img.strip()]
        else:
            product['images'] = []

        # Convert Decimal to float
        if product.get('price'):
            product['price'] = float(product['price'])

        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Product created successfully",
            "product": product
        }), 201

    except Exception as e:
        print(f"Error creating product: {e}")
        return _api_error(f"Failed to create product: {str(e)}", 500)


@seller_api_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_seller_product(product_id):
    """
    Update an existing product.

    Accepts EITHER multipart/form-data (Flutter) or application/json.

    Path Parameters:
        product_id (int): Product ID

    Form / JSON fields (all optional except at least one must be present):
        name (str): Product name
        description (str): Product description
        price (float): Product price
        category_id / category (str): Category ID
        stock (int): Stock quantity
        image (file, multipart only): New product image to upload

    Returns:
        JSON response with updated product
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)

    # ── Parse request body (multipart OR JSON) ───────────────────────────────
    is_multipart = request.content_type and 'multipart/form-data' in request.content_type
    if is_multipart:
        data = dict(request.form)  # ImmutableMultiDict → plain dict of lists/values
    else:
        data = request.get_json(silent=True)
        if not data:
            return _api_error("Invalid request: JSON body or multipart/form-data required", 400)

    def _field(key, *aliases):
        """Return the first non-None value for key or any alias."""
        for k in (key, *aliases):
            v = data.get(k)
            if v is None:
                continue
            return v[0] if isinstance(v, list) else v
        return None

    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Check if product exists and belongs to seller
        cur.execute("SELECT sellerID FROM products WHERE productID = %s", (product_id,))
        product = cur.fetchone()

        if not product:
            cur.close()
            conn.close()
            return _api_error("Product not found", 404)

        if product['sellerID'] != seller_id:
            cur.close()
            conn.close()
            return _api_error("Unauthorized: You don't own this product", 403)

        # Build update query dynamically
        update_fields = []
        update_values = []

        name_val = _field('name')
        if name_val is not None:
            update_fields.append("name = %s")
            update_values.append(str(name_val).strip())

        desc_val = _field('description')
        if desc_val is not None:
            update_fields.append("description = %s")
            update_values.append(str(desc_val).strip())

        price_val = _field('price')
        if price_val is not None:
            try:
                price_f = float(price_val)
            except (TypeError, ValueError):
                cur.close(); conn.close()
                return _api_error("Validation error: Price must be a number", 400)
            if price_f < 0:
                cur.close(); conn.close()
                return _api_error("Validation error: Price must be >= 0", 400)
            update_fields.append("price = %s")
            update_values.append(price_f)

        cat_val = _field('category_id', 'category')
        if cat_val is not None:
            update_fields.append("categoryID = %s")
            update_values.append(str(cat_val).strip())

        stock_val = _field('stock', 'stock_quantity')
        if stock_val is not None:
            try:
                update_fields.append("stock = %s")
                update_values.append(max(0, int(stock_val)))
            except (TypeError, ValueError):
                pass

        # ── Handle uploaded images (multipart: keep existing + add new) ─────────
        if is_multipart:
            existing_raw = request.form.get('existing_images', '')
            existing = [p.strip().split('/')[-1] for p in existing_raw.split(',') if p.strip()]
            for i in range(4):
                f = request.files.get(f'image{i}')
                if f and f.filename and _allowed_file(f.filename):
                    try:
                        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                        filename = secure_filename(f.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"prod_seller{seller_id}_{timestamp}_{i}_{filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, filename)
                        f.save(filepath)
                        existing.append(filename)
                    except Exception as img_err:
                        print(f"Warning: could not save image{i}: {img_err}")
            merged = existing[:4]
            if merged:
                update_fields.append("image_path = %s")
                update_values.append(','.join(merged))
        elif 'images' in data:
            images = data['images']
            images_str = ','.join(images) if isinstance(images, list) else str(images)
            update_fields.append("image_path = %s")
            update_values.append(images_str)

        if not update_fields:
            cur.close()
            conn.close()
            return _api_error("No fields to update", 400)

        # Add updated_at
        update_fields.append("updated_at = NOW()")

        # Execute update
        query = f"UPDATE products SET {', '.join(update_fields)} WHERE productID = %s"
        update_values.append(product_id)
        cur.execute(query, tuple(update_values))
        conn.commit()

        # Fetch updated product
        cur.execute("""
            SELECT
                productID as id,
                name as name,
                description as description,
                price as price,
                categoryID as category,
                stock as stock_quantity,
                image_path as images,
                created_at,
                updated_at
            FROM products
            WHERE productID = %s
        """, (product_id,))
        updated_product = cur.fetchone()

        # Process images
        if updated_product.get('images'):
            updated_product['images'] = [img.strip() for img in updated_product['images'].split(',') if img.strip()]
        else:
            updated_product['images'] = []

        # Convert Decimal to float
        if updated_product.get('price'):
            updated_product['price'] = float(updated_product['price'])

        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Product updated successfully",
            "product": updated_product
        }), 200

    except Exception as e:
        print(f"Error updating product: {e}")
        return _api_error(f"Failed to update product: {str(e)}", 500)



@seller_api_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_seller_product(product_id):
    """
    Delete a product.
    
    Path Parameters:
        product_id (int): Product ID
    
    Returns:
        JSON response confirming deletion
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Check if product exists and belongs to seller
        cur.execute("SELECT sellerID FROM products WHERE productID = %s", (product_id,))
        product = cur.fetchone()
        
        if not product:
            cur.close()
            conn.close()
            return _api_error("Product not found", 404)
        
        if product['sellerID'] != seller_id:
            cur.close()
            conn.close()
            return _api_error("Unauthorized: You don't own this product", 403)
        
        # Delete product
        cur.execute("DELETE FROM products WHERE productID = %s", (product_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Product deleted successfully"
        }), 200
        
    except Exception as e:
        print(f"Error deleting product: {e}")
        return _api_error(f"Failed to delete product: {str(e)}", 500)


@seller_api_bp.route('/products/upload-images', methods=['POST'])
@jwt_required()
def upload_product_images():
    """
    Upload product images.
    
    Request:
        multipart/form-data with 'images' field containing files
    
    Returns:
        JSON response with uploaded image URLs
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    if 'images' not in request.files:
        return _api_error("No images provided", 400)
    
    files = request.files.getlist('images')
    if not files:
        return _api_error("No images provided", 400)
    
    uploaded_urls = []
    
    try:
        # Ensure upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        for file in files:
            if file and file.filename:
                # Validate file
                if not _allowed_file(file.filename):
                    continue
                
                # Generate secure filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"seller_{seller_id}_{timestamp}_{filename}"
                
                # Save file
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Generate URL
                url = f"/uploads/{filename}"
                uploaded_urls.append(url)
        
        if not uploaded_urls:
            return _api_error("No valid images uploaded", 400)
        
        return jsonify({
            "success": True,
            "message": f"{len(uploaded_urls)} image(s) uploaded successfully",
            "urls": uploaded_urls
        }), 200
        
    except Exception as e:
        print(f"Error uploading images: {e}")
        return _api_error(f"Failed to upload images: {str(e)}", 500)


# ============================================================================
# ORDER MANAGEMENT ENDPOINTS
# ============================================================================

@seller_api_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_seller_orders():
    """
    Get paginated list of seller's orders.
    
    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)
        status (str): Filter by status (optional)
    
    Returns:
        JSON response with orders list
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    # Get pagination parameters
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(100, max(1, int(request.args.get('page_size', 20))))
    offset = (page - 1) * page_size
    status_filter = request.args.get('status', '').strip()
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Schema is snake_case in MySQL — alias to camelCase for the JSON
        # response so the Flutter side keeps its existing field names.
        query = """
            SELECT
                so.sellerOrderID                                  AS id,
                so.order_number,
                COALESCE(u.email, 'Unknown Customer')             AS customerName,
                so.total_amount                                   AS totalAmount,
                so.status,
                so.created_at                                     AS orderDate
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.sellerID = %s
        """
        params = [seller_id]

        if status_filter:
            query += " AND so.status = %s"
            params.append(status_filter)

        query += " ORDER BY so.created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        cur.execute(query, tuple(params))
        orders = cur.fetchall()

        # Convert Decimal to float and format response
        formatted_orders = []
        for order in orders:
            formatted_order = {
                'id': order.get('id'),
                'order_number': order.get('order_number', ''),
                'customerName': order.get('customerName', 'Unknown Customer'),
                'totalAmount': float(order.get('totalAmount', 0)) if order.get('totalAmount') else 0.0,
                'status': order.get('status', 'pending'),
                'orderDate': order.get('orderDate').isoformat() if order.get('orderDate') else None,
            }
            formatted_orders.append(formatted_order)
        
        # Get total count
        count_query = "SELECT COUNT(*) as total FROM seller_orders WHERE sellerID = %s"
        count_params = [seller_id]
        if status_filter:
            count_query += " AND status = %s"
            count_params.append(status_filter)
        
        cur.execute(count_query, tuple(count_params))
        total = cur.fetchone()['total']
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "orders": formatted_orders,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching seller orders: {e}")
        return _api_error(f"Failed to fetch orders: {str(e)}", 500)


@seller_api_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_seller_order_details(order_id):
    """
    Get detailed information for a specific order.
    
    Path Parameters:
        order_id (int): Order ID
    
    Returns:
        JSON response with order details including line items
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Fetch order — alias snake_case columns to the camelCase fields the
        # mobile client already consumes.  Include shipping/contact/payment/rider.
        cur.execute("""
            SELECT
                so.sellerOrderID                       AS id,
                so.order_number,
                COALESCE(u.email, 'Unknown Customer')  AS customerName,
                so.total_amount                        AS totalAmount,
                so.status,
                so.created_at                          AS orderDate,
                so.shipping_address,
                so.contact_number,
                so.payment_method,
                so.riderID,
                r.ridername                             AS rider_name
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
            LEFT JOIN riders r ON so.riderID = r.riderID
            WHERE so.sellerOrderID = %s AND so.sellerID = %s
        """, (order_id, seller_id))
        order = cur.fetchone()
        
        if not order:
            cur.close()
            conn.close()
            return _api_error("Order not found", 404)
        
        # Format order response
        formatted_order = {
            'id': order.get('id'),
            'order_number': order.get('order_number', ''),
            'customerName': order.get('customerName', 'Unknown Customer'),
            'totalAmount': float(order.get('totalAmount', 0)) if order.get('totalAmount') else 0.0,
            'status': order.get('status', 'pending'),
            'orderDate': order.get('orderDate').isoformat() if order.get('orderDate') else None,
            'shipping_address': order.get('shipping_address') or '',
            'contact_number': order.get('contact_number') or '',
            'payment_method': order.get('payment_method') or '',
            'rider_id': order.get('riderID'),
            'rider_name': order.get('rider_name') or '',
            'lineItems': []
        }
        
        # Fetch line items. Real table is `seller_order_items`, and the item
        # row itself doesn't carry a name — JOIN to products for it.
        try:
            cur.execute("""
                SELECT
                    soi.productID  AS productId,
                    p.name         AS name,
                    soi.quantity,
                    soi.price
                FROM seller_order_items soi
                LEFT JOIN products p ON p.productID = soi.productID
                WHERE soi.sellerOrderID = %s
            """, (order_id,))
            line_items = cur.fetchall()
            
            # Format line items
            for item in line_items:
                formatted_item = {
                    'productId': item.get('productId'),
                    'name': item.get('name', ''),
                    'quantity': item.get('quantity', 0),
                    'price': float(item.get('price', 0)) if item.get('price') else 0.0,
                }
                formatted_order['lineItems'].append(formatted_item)
        except Exception as e:
            print(f"Note: Could not fetch line items: {e}")
            formatted_order['lineItems'] = []
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "order": formatted_order
        }), 200
        
    except Exception as e:
        print(f"Error fetching order details: {e}")
        return _api_error(f"Failed to fetch order details: {str(e)}", 500)


@seller_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_seller_order_status(order_id):
    """
    Update order status.
    
    Path Parameters:
        order_id (int): Order ID
    
    Request Body (JSON):
        status (str): New status (required)
            Valid values: pending, processing, shipped, delivered, cancelled
    
    Returns:
        JSON response with updated order
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    data = request.get_json()
    if not data:
        return _api_error("Invalid request: JSON body required", 400)
    
    new_status = data.get('status', '').strip().lower()
    # Match the actual ENUM on seller_orders.status.
    valid_statuses = [
        'pending', 'packing', 'packed', 'assigned_to_rider',
        'picked_up', 'on_the_way', 'delivered', 'cancelled',
    ]

    if new_status not in valid_statuses:
        return _api_error(
            f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            400,
            {"status": f"Must be one of: {', '.join(valid_statuses)}"}
        )
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Check if order exists and belongs to seller - using camelCase
        cur.execute("""
            SELECT status 
            FROM seller_orders 
            WHERE sellerOrderID = %s AND sellerID = %s
        """, (order_id, seller_id))
        order = cur.fetchone()
        
        if not order:
            cur.close()
            conn.close()
            return _api_error("Order not found", 404)
        
        # Validate status transition (basic validation)
        current_status = order['status'].lower() if order['status'] else 'pending'
        
        # Prevent invalid transitions
        if current_status == 'delivered' and new_status != 'delivered':
            cur.close()
            conn.close()
            return _api_error("Cannot change status of delivered order", 400)
        
        if current_status == 'cancelled' and new_status != 'cancelled':
            cur.close()
            conn.close()
            return _api_error("Cannot change status of cancelled order", 400)
        
        # `updated_at` has ON UPDATE current_timestamp() — MySQL refreshes it
        # automatically when status changes, so no explicit SET is needed.
        cur.execute("""
            UPDATE seller_orders
            SET status = %s
            WHERE sellerOrderID = %s
        """, (new_status, order_id))
        conn.commit()

        # Fetch updated order
        cur.execute("""
            SELECT
                so.sellerOrderID                       AS id,
                so.order_number,
                COALESCE(u.email, 'Unknown Customer')  AS customerName,
                so.total_amount                        AS totalAmount,
                so.status,
                so.created_at                          AS orderDate
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.sellerOrderID = %s
        """, (order_id,))
        updated_order = cur.fetchone()
        
        # Format response
        formatted_order = {
            'id': updated_order.get('id'),
            'order_number': updated_order.get('order_number', ''),
            'customerName': updated_order.get('customerName', 'Unknown Customer'),
            'totalAmount': float(updated_order.get('totalAmount', 0)) if updated_order.get('totalAmount') else 0.0,
            'status': updated_order.get('status', 'pending'),
            'orderDate': updated_order.get('orderDate').isoformat() if updated_order.get('orderDate') else None,
        }
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Order status updated successfully",
            "order": formatted_order
        }), 200
        
    except Exception as e:
        print(f"Error updating order status: {e}")
        return _api_error(f"Failed to update order status: {str(e)}", 500)


# ============================================================================
# RIDER MANAGEMENT ENDPOINTS (JWT-authenticated for mobile)
# ============================================================================

@seller_api_bp.route('/mobile/riders', methods=['GET'])
@jwt_required()
def get_available_riders():
    """
    Get list of available riders for order assignment.
    
    Returns:
        JSON response with list of active riders
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        cur.execute("""
            SELECT riderID, ridername, rideremail, phone, status
            FROM riders
            WHERE status = 'active'
              AND (is_available = 1 OR is_available IS NULL)
            ORDER BY ridername ASC
        """)
        riders = cur.fetchall() or []
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "riders": riders
        }), 200
        
    except Exception as e:
        print(f"Error fetching riders: {e}")
        return _api_error(f"Failed to fetch riders: {str(e)}", 500)


@seller_api_bp.route('/orders/<int:order_id>/mobile-assign-rider', methods=['POST'])
@jwt_required()
def assign_rider_to_order(order_id):
    """
    Assign a rider to a seller's order.
    
    Path Parameters:
        order_id (int): Order ID
    
    Request Body (JSON):
        riderID (int): Rider ID to assign
    
    Returns:
        JSON response confirming assignment with rider details
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    data = request.get_json()
    if not data:
        return _api_error("Invalid request: JSON body required", 400)
    
    rider_id = data.get('riderID') or data.get('rider_id')
    if not rider_id:
        return _api_error("Missing riderID", 400)
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Verify seller owns this order
        cur.execute("""
            SELECT sellerID, order_number, userID
            FROM seller_orders
            WHERE sellerOrderID = %s
            LIMIT 1
        """, (order_id,))
        row = cur.fetchone()
        if not row or int(row.get('sellerID')) != int(seller_id):
            cur.close()
            conn.close()
            return _api_error("Order not found or not owned by you", 404)
        
        order_number = row.get('order_number', str(order_id))
        
        # Verify rider exists and is active
        cur.execute("""
            SELECT riderID, ridername
            FROM riders
            WHERE riderID = %s AND status = 'active'
        """, (rider_id,))
        rider = cur.fetchone()
        if not rider:
            cur.close()
            conn.close()
            return _api_error("Rider not found or inactive", 400)
        
        rider_name = rider['ridername']
        
        # Assign rider to order
        cur.execute("""
            UPDATE seller_orders
            SET riderID = %s, status = 'assigned_to_rider', updated_at = NOW()
            WHERE sellerOrderID = %s
        """, (rider_id, order_id))
        
        # Add status history entry
        try:
            cur.execute("""
                INSERT INTO order_status_history (sellerOrderID, status, message)
                VALUES (%s, %s, %s)
            """, (order_id, 'assigned_to_rider',
                  f'Seller assigns order to {rider_name}'))
        except Exception:
            pass  # Non-fatal
        
        # Notify rider (best-effort)
        try:
            cur.execute("""
                INSERT INTO notifications (recipient_type, recipient_id, title, body)
                VALUES ('rider', %s, 'New Order Assignment', %s)
            """, (rider_id,
                  f'You have been assigned to deliver Order #{order_number}'))
        except Exception:
            pass
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Rider assigned successfully",
            "rider": {
                "riderID": rider['riderID'],
                "ridername": rider_name
            }
        }), 200
        
    except Exception as e:
        print(f"Error assigning rider: {e}")
        return _api_error(f"Failed to assign rider: {str(e)}", 500)
