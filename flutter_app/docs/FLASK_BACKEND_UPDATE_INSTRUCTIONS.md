# Flask Backend Update Instructions - Orders API Fix

## Problem Summary
The Flask backend (`../app/seller_api.py`) is using **old snake_case column names** that don't match the actual database schema. The database uses **camelCase column names** in the `seller_orders` table.

## Database Schema (Actual)
```
seller_orders table columns:
- sellerOrderID (primary key)
- sellerID
- orderID
- status
- buyer_received_at
- revenue_released
- orderNumber
- totalAmount
- orderDate
- createdAt
- updatedAt
```

## What's Wrong in Current Code
The old code is trying to use column names like:
- `so_seller_order_id` ❌ (should be `sellerOrderID`)
- `so_order_number` ❌ (should be `orderNumber`)
- `so_total_amount` ❌ (should be `totalAmount`)
- `so_order_date` ❌ (should be `orderDate`)
- `so_created_at` ❌ (should be `createdAt`)
- `so_updated_at` ❌ (should be `updatedAt`)

## Solution
Replace the entire `../app/seller_api.py` file with the corrected version from `docs/flask_seller_api.py`.

### Key Changes in Order Management Endpoints

#### GET /api/seller/orders (List Orders)
**OLD (WRONG):**
```python
query = """
    SELECT 
        so.so_seller_order_id as id,
        so.so_order_number,
        ...
    FROM seller_orders so
"""
```

**NEW (CORRECT):**
```python
query = """
    SELECT 
        so.sellerOrderID as id,
        so.orderNumber,
        COALESCE(b.buyerName, 'Unknown Customer') as customerName,
        so.totalAmount,
        so.status,
        so.orderDate,
        so.createdAt,
        so.updatedAt
    FROM seller_orders so
    LEFT JOIN buyers b ON so.buyerID = b.buyerID
    WHERE so.sellerID = %s
"""
```

#### GET /api/seller/orders/<id> (Get Order Details)
**OLD (WRONG):**
```python
cur.execute("""
    SELECT so.so_seller_order_id as id, ...
    FROM seller_orders so
    WHERE so.so_seller_order_id = %s
""", (order_id, seller_id))
```

**NEW (CORRECT):**
```python
cur.execute("""
    SELECT 
        so.sellerOrderID as id,
        so.orderNumber,
        COALESCE(b.buyerName, 'Unknown Customer') as customerName,
        so.totalAmount,
        so.status,
        so.orderDate,
        so.createdAt,
        so.updatedAt
    FROM seller_orders so
    LEFT JOIN buyers b ON so.buyerID = b.buyerID
    WHERE so.sellerOrderID = %s AND so.sellerID = %s
""", (order_id, seller_id))
```

#### PUT /api/seller/orders/<id>/status (Update Order Status)
**OLD (WRONG):**
```python
cur.execute("""
    SELECT status 
    FROM seller_orders 
    WHERE so_seller_order_id = %s AND so_seller_id = %s
""", (order_id, seller_id))

# Update
cur.execute("""
    UPDATE seller_orders 
    SET so_status = %s, so_updated_at = NOW()
    WHERE so_seller_order_id = %s
""", (new_status, order_id))
```

**NEW (CORRECT):**
```python
cur.execute("""
    SELECT status 
    FROM seller_orders 
    WHERE sellerOrderID = %s AND sellerID = %s
""", (order_id, seller_id))

# Update
cur.execute("""
    UPDATE seller_orders 
    SET status = %s, updatedAt = NOW()
    WHERE sellerOrderID = %s
""", (new_status, order_id))
```

## Installation Steps

1. **Backup Current File** (Optional but recommended)
   ```bash
   cp ../app/seller_api.py ../app/seller_api.py.backup
   ```

2. **Copy Corrected File**
   - Copy the entire content from `docs/flask_seller_api.py`
   - Paste it into `../app/seller_api.py`
   - Save the file

3. **Restart Flask Server**
   ```bash
   # Stop the current Flask server (Ctrl+C if running in terminal)
   # Then restart it
   python run.py
   # or
   flask run
   ```

4. **Verify the Fix**
   - Open Flutter app
   - Navigate to Seller Dashboard → Orders tab
   - Orders should now load correctly with proper data

## What Gets Fixed

✅ Orders list will display correctly with:
- Order ID
- Order Number
- Customer Name
- Total Amount
- Status
- Order Date

✅ Order details will load without errors

✅ Order status updates will work properly

## Testing Checklist

After updating and restarting Flask:

- [ ] Orders list loads without errors
- [ ] Order data displays correctly (order number, customer name, amount, status)
- [ ] Can click on an order to view details
- [ ] Can update order status
- [ ] No SQL errors in Flask console

## Troubleshooting

If you still see errors after updating:

1. **Check Flask is restarted** - Make sure you restarted the Flask server
2. **Check file was copied completely** - Verify the entire file was replaced
3. **Check database connection** - Verify database credentials in environment variables
4. **Check column names** - Run this query in MySQL to verify column names:
   ```sql
   DESCRIBE seller_orders;
   ```

## Files Involved

- **To Update**: `../app/seller_api.py` (Flask backend)
- **Source**: `docs/flask_seller_api.py` (Corrected version)
- **No changes needed**: Flutter app code (already handles camelCase correctly)

---

**Status**: Ready to implement
**Priority**: HIGH - Orders feature is broken without this fix
**Estimated Time**: 5 minutes
