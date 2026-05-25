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

import mysql.connector
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from werkzeug.utils import secure_filename

# Database configuration
DB_HOST = os.environ.get("HH_DB_HOST", "localhost")
DB_PORT = int(os.environ.get("HH_DB_PORT", "3306"))
DB_USER = os.environ.get("HH_DB_USER", "root")
DB_PASSWORD = os.environ.get("HH_DB_PASSWORD", "root")
DB_NAME = os.environ.get("HH_DB_NAME") or os.environ.get("BABYSTORE_DB") or "babystore"

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create blueprint
seller_api_bp = Blueprint("seller_api", __name__, url_prefix="/api/seller")


def _get_db_connection():
    """Get MySQL database connection."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connection_timeout=5,
    )


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
                productname as name,
                productdescription as description,
                productprice as price,
                productcategory as category,
                productquantity as stock_quantity,
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
    
    Request Body (JSON):
        name (str): Product name (required)
        description (str): Product description
        price (float): Product price (required)
        category (str): Product category
        stock_quantity (int): Stock quantity (default: 0)
        images (list): List of image URLs
    
    Returns:
        JSON response with created product
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    data = request.get_json()
    if not data:
        return _api_error("Invalid request: JSON body required", 400)
    
    # Validate required fields
    name = data.get('name', '').strip()
    price = data.get('price')
    
    if not name:
        return _api_error("Validation error: Product name is required", 400, {"name": "Required"})
    
    if price is None or price < 0:
        return _api_error("Validation error: Valid price is required", 400, {"price": "Must be >= 0"})
    
    # Extract optional fields
    description = data.get('description', '').strip()
    category = data.get('category', '').strip()
    stock_quantity = max(0, int(data.get('stock_quantity', 0)))
    images = data.get('images', [])
    
    # Convert images list to comma-separated string
    images_str = ','.join(images) if isinstance(images, list) else ''
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Insert product
        query = """
            INSERT INTO products 
            (productname, productdescription, productprice, productcategory, 
             productquantity, image_path, sellerID, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        cur.execute(query, (name, description, price, category, stock_quantity, images_str, seller_id))
        conn.commit()
        
        product_id = cur.lastrowid
        
        # Fetch the created product
        cur.execute("""
            SELECT 
                productID as id,
                productname as name,
                productdescription as description,
                productprice as price,
                productcategory as category,
                productquantity as stock_quantity,
                image_path as images,
                created_at,
                updated_at
            FROM products
            WHERE productID = %s
        """, (product_id,))
        product = cur.fetchone()
        
        # Process images
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
    
    Path Parameters:
        product_id (int): Product ID
    
    Request Body (JSON):
        name (str): Product name
        description (str): Product description
        price (float): Product price
        category (str): Product category
        stock_quantity (int): Stock quantity
        images (list): List of image URLs
    
    Returns:
        JSON response with updated product
    """
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    data = request.get_json()
    if not data:
        return _api_error("Invalid request: JSON body required", 400)
    
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
        
        if 'name' in data:
            update_fields.append("productname = %s")
            update_values.append(data['name'].strip())
        
        if 'description' in data:
            update_fields.append("productdescription = %s")
            update_values.append(data['description'].strip())
        
        if 'price' in data:
            if data['price'] < 0:
                return _api_error("Validation error: Price must be >= 0", 400)
            update_fields.append("productprice = %s")
            update_values.append(data['price'])
        
        if 'category' in data:
            update_fields.append("productcategory = %s")
            update_values.append(data['category'].strip())
        
        if 'stock_quantity' in data:
            update_fields.append("productquantity = %s")
            update_values.append(max(0, int(data['stock_quantity'])))
        
        if 'images' in data:
            images = data['images']
            images_str = ','.join(images) if isinstance(images, list) else ''
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
                productname as name,
                productdescription as description,
                productprice as price,
                productcategory as category,
                productquantity as stock_quantity,
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
        
        # Build query - using camelCase column names to match actual database schema
        # Using users table instead of buyers table
        query = """
            SELECT 
                so.sellerOrderID as id,
                so.orderNumber,
                COALESCE(u.email, 'Unknown Customer') as customerName,
                so.totalAmount,
                so.status,
                so.orderDate,
                so.createdAt,
                so.updatedAt
            FROM seller_orders so
            LEFT JOIN users u ON so.buyerID = u.userID
            WHERE so.sellerID = %s
        """
        params = [seller_id]
        
        if status_filter:
            query += " AND so.status = %s"
            params.append(status_filter)
        
        query += " ORDER BY so.orderDate DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        
        cur.execute(query, tuple(params))
        orders = cur.fetchall()
        
        # Convert Decimal to float and format response
        formatted_orders = []
        for order in orders:
            formatted_order = {
                'id': order.get('id'),
                'orderNumber': order.get('orderNumber', ''),
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
        
        # Fetch order - using camelCase column names and users table
        cur.execute("""
            SELECT 
                so.sellerOrderID as id,
                so.orderNumber,
                COALESCE(u.email, 'Unknown Customer') as customerName,
                so.totalAmount,
                so.status,
                so.orderDate,
                so.createdAt,
                so.updatedAt
            FROM seller_orders so
            LEFT JOIN users u ON so.buyerID = u.userID
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
            'orderNumber': order.get('orderNumber', ''),
            'customerName': order.get('customerName', 'Unknown Customer'),
            'totalAmount': float(order.get('totalAmount', 0)) if order.get('totalAmount') else 0.0,
            'status': order.get('status', 'pending'),
            'orderDate': order.get('orderDate').isoformat() if order.get('orderDate') else None,
            'lineItems': []
        }
        
        # Fetch line items if they exist in the database
        try:
            cur.execute("""
                SELECT 
                    productID as productId,
                    productName,
                    quantity,
                    price
                FROM order_line_items
                WHERE sellerOrderID = %s
            """, (order_id,))
            line_items = cur.fetchall()
            
            # Format line items
            for item in line_items:
                formatted_item = {
                    'productId': item.get('productId'),
                    'productName': item.get('productName', ''),
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
    valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    
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
        
        # Update status - using camelCase column names
        cur.execute("""
            UPDATE seller_orders 
            SET status = %s, updatedAt = NOW()
            WHERE sellerOrderID = %s
        """, (new_status, order_id))
        conn.commit()
        
        # Fetch updated order - using users table
        cur.execute("""
            SELECT 
                sellerOrderID as id,
                orderNumber,
                COALESCE(u.email, 'Unknown Customer') as customerName,
                totalAmount,
                status,
                orderDate,
                createdAt,
                updatedAt
            FROM seller_orders so
            LEFT JOIN users u ON so.buyerID = u.userID
            WHERE sellerOrderID = %s
        """, (order_id,))
        updated_order = cur.fetchone()
        
        # Format response
        formatted_order = {
            'id': updated_order.get('id'),
            'orderNumber': updated_order.get('orderNumber', ''),
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
