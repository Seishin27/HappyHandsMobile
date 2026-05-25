# ============================================================================
# COPY THIS ENTIRE SECTION INTO YOUR seller_api.py
# Replace the get_seller_orders function (around line 551)
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
        
        # CORRECTED QUERY - uses actual database column names
        query = """
            SELECT 
                so.sellerOrderID as id,
                so.order_number as orderNumber,
                COALESCE(u.username, u.email, 'Unknown Customer') as customerName,
                so.total_amount as totalAmount,
                so.status,
                so.items_received_at as orderDate
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.sellerID = %s
        """
        params = [seller_id]
        
        if status_filter:
            query += " AND so.status = %s"
            params.append(status_filter)
        
        query += " ORDER BY so.items_received_at DESC LIMIT %s OFFSET %s"
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


# ============================================================================
# ALSO REPLACE get_seller_order_details function (around line 648)
# ============================================================================

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
        
        # CORRECTED QUERY - uses actual database column names
        cur.execute("""
            SELECT 
                so.sellerOrderID as id,
                so.order_number as orderNumber,
                COALESCE(u.username, u.email, 'Unknown Customer') as customerName,
                so.total_amount as totalAmount,
                so.status,
                so.items_received_at as orderDate
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
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


# ============================================================================
# ALSO REPLACE update_seller_order_status function (around line 740)
# ============================================================================

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
        
        # Check if order exists and belongs to seller
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
        
        # Update status
        cur.execute("""
            UPDATE seller_orders 
            SET status = %s
            WHERE sellerOrderID = %s
        """, (new_status, order_id))
        conn.commit()
        
        # Fetch updated order - CORRECTED QUERY
        cur.execute("""
            SELECT 
                sellerOrderID as id,
                order_number as orderNumber,
                COALESCE(u.username, u.email, 'Unknown Customer') as customerName,
                total_amount as totalAmount,
                status,
                items_received_at as orderDate
            FROM seller_orders so
            LEFT JOIN users u ON so.userID = u.userID
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
