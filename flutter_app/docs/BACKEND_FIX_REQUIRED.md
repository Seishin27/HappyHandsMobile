# Backend Fix Required - seller_api.py

## Current Situation

The Flutter app is ready and flexible enough to handle various response formats, but the Flask backend `seller_api.py` has SQL errors because it's using wrong column names.

## The Problem

Your `seller_api.py` file is using column names that don't exist in your database:

### Orders Query Issues:
- ❌ Uses `so.buyerID` but database has `so.userID`
- ❌ Uses `so.orderNumber` but database has `so.order_number`
- ❌ Uses `so.totalAmount` but database has `so.total_amount`
- ❌ Uses `so.orderDate` but database has `so.items_received_at`
- ❌ Uses `so.createdAt` but this column doesn't exist
- ❌ Uses `so.updatedAt` but this column doesn't exist
- ❌ Uses `LEFT JOIN users b ON so.usersID = b.userID` (typo: `usersID` should be `userID`)

### Products Query Issues:
- ❌ Uses `productname` but database has `name`
- ❌ Uses `productdescription` but database has `description`
- ❌ Uses `productprice` but database has `price`
- ❌ Uses `productcategory` but database has `categoryID`
- ❌ Uses `productquantity` but database has `stock`

---

## The Solution

You MUST update your `seller_api.py` file with the correct column names. Here's the exact SQL query that will work:

### Corrected Orders Query

```python
@seller_api_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_seller_orders():
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(100, max(1, int(request.args.get('page_size', 20))))
    offset = (page - 1) * page_size
    status_filter = request.args.get('status', '').strip()
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # CORRECTED QUERY - matches your actual database schema
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
        
        # Format response
        formatted_orders = []
        for order in orders:
            formatted_orders.append({
                'id': order.get('id'),
                'orderNumber': order.get('orderNumber', ''),
                'customerName': order.get('customerName', 'Unknown Customer'),
                'totalAmount': float(order.get('totalAmount', 0)) if order.get('totalAmount') else 0.0,
                'status': order.get('status', 'pending'),
                'orderDate': order.get('orderDate').isoformat() if order.get('orderDate') else None,
            })
        
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
```

### Corrected Products Query

```python
@seller_api_bp.route('/products', methods=['GET'])
@jwt_required()
def get_seller_products():
    seller_id = _get_authenticated_seller_id()
    if not seller_id:
        return _api_error("Unauthorized: Seller authentication required", 401)
    
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(100, max(1, int(request.args.get('page_size', 20))))
    offset = (page - 1) * page_size
    
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # CORRECTED QUERY - matches your actual database schema
        query = """
            SELECT 
                productID as id,
                name,
                description,
                price,
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
```

---

## What I've Done on Flutter Side

✅ Updated `lib/models/seller_order.dart` to handle multiple field name variations
✅ Updated `lib/models/seller_product.dart` to handle multiple field name variations
✅ Added debug logging to `lib/services/flask_api_service.dart` to see what's coming from backend
✅ Made the models very flexible to accept any reasonable field name

---

## What You Need to Do

You need to copy the corrected SQL queries above into your `seller_api.py` file. The key changes are:

1. `so.buyerID` → `so.userID`
2. `so.orderNumber` → `so.order_number`
3. `so.totalAmount` → `so.total_amount`
4. `so.orderDate` → `so.items_received_at`
5. Remove `so.createdAt` and `so.updatedAt` (don't exist)
6. `productname` → `name`
7. `productdescription` → `description`
8. `productprice` → `price`
9. `productcategory` → `categoryID`
10. `productquantity` → `stock`

---

## Testing

After you update `seller_api.py`:

1. Restart Flask server
2. Check Flutter app console for debug logs
3. You should see:
   ```
   📥 Raw orders response: {success: true, orders: [...]}
   📦 Found X orders
   📋 First order sample: {id: 1, orderNumber: ..., customerName: ...}
   ```

If you still see errors, the debug logs will show exactly what's wrong.

---

## Alternative: Send Me the Working Web API

If you have a working seller dashboard in the web version, you can:
1. Show me the PHP/Python code that fetches seller orders
2. I'll make the Flutter app match that exact format

