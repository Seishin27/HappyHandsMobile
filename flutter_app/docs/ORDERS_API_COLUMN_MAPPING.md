# Orders API - Column Name Mapping Reference

## Problem: Column Name Mismatch

The Flask backend was using **snake_case** column names that don't exist in the database. The actual database uses **camelCase** column names.

## Column Mapping Table

| Database Column | Old Code (WRONG) | New Code (CORRECT) | Type | Description |
|---|---|---|---|---|
| `sellerOrderID` | `so_seller_order_id` | `so.sellerOrderID` | INT | Primary key for seller order |
| `sellerID` | `so_seller_id` | `so.sellerID` | INT | Foreign key to sellers |
| `orderID` | `so_order_id` | `so.orderID` | INT | Foreign key to orders |
| `orderNumber` | `so_order_number` | `so.orderNumber` | VARCHAR | Order reference number |
| `totalAmount` | `so_total_amount` | `so.totalAmount` | DECIMAL | Order total |
| `status` | `so_status` | `so.status` | VARCHAR | Order status |
| `orderDate` | `so_order_date` | `so.orderDate` | DATETIME | When order was placed |
| `createdAt` | `so_created_at` | `so.createdAt` | DATETIME | Record creation time |
| `updatedAt` | `so_updated_at` | `so.updatedAt` | DATETIME | Last update time |
| `buyerID` | `so_buyer_id` | `so.buyerID` | INT | Foreign key to buyers |

## Related Tables

### buyers table
| Column | Usage | Notes |
|---|---|---|
| `buyerID` | JOIN key | Links to seller_orders.buyerID |
| `buyerName` | Display | Customer name in order list |

### order_line_items table (if used)
| Column | Usage | Notes |
|---|---|---|
| `sellerOrderID` | JOIN key | Links to seller_orders.sellerOrderID |
| `productID` | Product reference | |
| `productName` | Display | Product name in order details |
| `quantity` | Display | Quantity ordered |
| `price` | Display | Unit price |

## SQL Query Examples

### Example 1: Fetch Orders List (CORRECT)
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
WHERE so.sellerID = 1
ORDER BY so.orderDate DESC
LIMIT 20 OFFSET 0;
```

### Example 2: Fetch Order Details (CORRECT)
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
WHERE so.sellerOrderID = 61 AND so.sellerID = 1;
```

### Example 3: Update Order Status (CORRECT)
```sql
UPDATE seller_orders 
SET status = 'processing', updatedAt = NOW()
WHERE sellerOrderID = 61;
```

## API Response Format

### GET /api/seller/orders
```json
{
  "success": true,
  "orders": [
    {
      "id": 61,
      "orderNumber": "ORD-2025-001",
      "customerName": "John Doe",
      "totalAmount": 1500.00,
      "status": "pending",
      "orderDate": "2025-11-28T14:47:28"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

### GET /api/seller/orders/<id>
```json
{
  "success": true,
  "order": {
    "id": 61,
    "orderNumber": "ORD-2025-001",
    "customerName": "John Doe",
    "totalAmount": 1500.00,
    "status": "pending",
    "orderDate": "2025-11-28T14:47:28",
    "lineItems": [
      {
        "productId": 123,
        "productName": "Baby Stroller",
        "quantity": 1,
        "price": 1500.00
      }
    ]
  }
}
```

### PUT /api/seller/orders/<id>/status
```json
{
  "success": true,
  "message": "Order status updated successfully",
  "order": {
    "id": 61,
    "orderNumber": "ORD-2025-001",
    "customerName": "John Doe",
    "totalAmount": 1500.00,
    "status": "processing",
    "orderDate": "2025-11-28T14:47:28"
  }
}
```

## Verification Query

Run this in MySQL Workbench to verify column names:

```sql
-- Check seller_orders table structure
DESCRIBE seller_orders;

-- Check actual data
SELECT * FROM seller_orders LIMIT 1;

-- Check with JOIN
SELECT 
    so.sellerOrderID,
    so.orderNumber,
    b.buyerName,
    so.totalAmount,
    so.status,
    so.orderDate
FROM seller_orders so
LEFT JOIN buyers b ON so.buyerID = b.buyerID
LIMIT 5;
```

## Summary

- **Database uses**: camelCase (sellerOrderID, orderNumber, totalAmount, etc.)
- **Old code used**: snake_case (so_seller_order_id, so_order_number, etc.)
- **New code uses**: camelCase (so.sellerOrderID, so.orderNumber, etc.)
- **Result**: Orders API will now work correctly ✅
