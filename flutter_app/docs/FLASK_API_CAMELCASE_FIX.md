# Flask API CamelCase Column Names Fix

## Problem

The Flask seller API was using snake_case column names in SQL queries, but the actual database uses camelCase column names. This caused a 500 error:

```
Unknown column 'so.seller_order_id' in 'field list'
```

## Solution

Updated all SQL queries in `docs/flask_seller_api.py` to use the correct camelCase column names that match your actual database schema.

## Changes Made

### 1. GET /api/seller/orders (List Orders)

**Before:**
```sql
SELECT 
    so.seller_order_id as id,
    so.order_number,
    so.customer_name,
    so.total_amount,
    so.status,
    so.order_date,
    so.created_at,
    so.updated_at
FROM seller_orders so
WHERE so.seller_id = %s
```

**After:**
```sql
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
```

**Key Changes:**
- `seller_order_id` → `sellerOrderID`
- `order_number` → `orderNumber`
- `customer_name` → `buyerName` (from buyers table)
- `total_amount` → `totalAmount`
- `order_date` → `orderDate`
- `created_at` → `createdAt`
- `updated_at` → `updatedAt`
- `seller_id` → `sellerID`
- Added LEFT JOIN to `buyers` table to get customer name

### 2. GET /api/seller/orders/{id} (Order Details)

**Before:**
```sql
SELECT 
    so.seller_order_id as id,
    so.order_number,
    so.customer_name,
    so.total_amount,
    so.status,
    so.order_date,
    so.created_at,
    so.updated_at
FROM seller_orders so
WHERE so.seller_order_id = %s AND so.seller_id = %s
```

**After:**
```sql
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
```

**Key Changes:**
- Same column name mappings as above
- Added LEFT JOIN to buyers table

### 3. PUT /api/seller/orders/{id}/status (Update Order Status)

**Before:**
```sql
SELECT seller_id, status 
FROM seller_orders 
WHERE seller_order_id = %s

UPDATE seller_orders 
SET status = %s, updated_at = NOW()
WHERE seller_order_id = %s
```

**After:**
```sql
SELECT status 
FROM seller_orders 
WHERE sellerOrderID = %s AND sellerID = %s

UPDATE seller_orders 
SET status = %s, updatedAt = NOW()
WHERE sellerOrderID = %s
```

**Key Changes:**
- `seller_order_id` → `sellerOrderID`
- `seller_id` → `sellerID`
- `updated_at` → `updatedAt`

## Database Schema (Actual)

Your actual database schema uses these camelCase column names:

```
seller_orders table:
├── sellerOrderID (INT, PRIMARY KEY)
├── sellerID (INT, FOREIGN KEY)
├── orderID (INT)
├── orderNumber (VARCHAR)
├── buyerID (INT, FOREIGN KEY)
├── totalAmount (DECIMAL)
├── status (VARCHAR)
├── orderDate (TIMESTAMP)
├── buyer_received_at (TIMESTAMP)
├── revenue_released (TIMESTAMP)
├── createdAt (TIMESTAMP)
└── updatedAt (TIMESTAMP)

buyers table:
├── buyerID (INT, PRIMARY KEY)
├── buyerName (VARCHAR)
└── ...
```

## Installation

1. Copy the updated file to your Flask app:
   ```bash
   cp flutter_app/docs/flask_seller_api.py app/seller_api.py
   ```

2. Register the blueprint in `run.py`:
   ```python
   from app.seller_api import seller_api_bp
   app.register_blueprint(seller_api_bp)
   ```

3. Restart Flask server:
   ```bash
   python run.py
   ```

## Testing

After installation, test the endpoints:

```bash
# Get orders
curl -X GET http://localhost:5500/api/seller/orders \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get order details
curl -X GET http://localhost:5500/api/seller/orders/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Update order status
curl -X PUT http://localhost:5500/api/seller/orders/1/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "processing"}'
```

## Response Format

All endpoints now return properly formatted JSON with camelCase keys:

```json
{
  "success": true,
  "orders": [
    {
      "id": 1,
      "orderNumber": "ORD-001",
      "customerName": "John Doe",
      "totalAmount": 1500.0,
      "status": "pending",
      "orderDate": "2024-01-15T10:30:00"
    }
  ]
}
```

## Verification

The Flutter app expects the response in this format, which now matches the actual database schema. The Orders tab should now display correctly without errors.
