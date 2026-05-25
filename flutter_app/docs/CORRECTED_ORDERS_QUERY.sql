-- CORRECTED Orders Query for Your Database
-- This matches your actual database schema

-- GET /api/seller/orders
SELECT 
    so.sellerOrderID as id,
    so.order_number as orderNumber,
    COALESCE(u.email, 'Unknown Customer') as customerName,
    so.total_amount as totalAmount,
    so.status,
    so.items_received_at as orderDate,
    NULL as createdAt,
    NULL as updatedAt
FROM seller_orders so
LEFT JOIN users u ON so.userID = u.userID
WHERE so.sellerID = %s
ORDER BY so.items_received_at DESC
LIMIT %s OFFSET %s;

-- GET /api/seller/orders/<id>
SELECT 
    so.sellerOrderID as id,
    so.order_number as orderNumber,
    COALESCE(u.email, 'Unknown Customer') as customerName,
    so.total_amount as totalAmount,
    so.status,
    so.items_received_at as orderDate,
    NULL as createdAt,
    NULL as updatedAt
FROM seller_orders so
LEFT JOIN users u ON so.userID = u.userID
WHERE so.sellerOrderID = %s AND so.sellerID = %s;

-- PUT /api/seller/orders/<id>/status (fetch updated order)
SELECT 
    sellerOrderID as id,
    order_number as orderNumber,
    COALESCE(u.email, 'Unknown Customer') as customerName,
    total_amount as totalAmount,
    status,
    items_received_at as orderDate,
    NULL as createdAt,
    NULL as updatedAt
FROM seller_orders so
LEFT JOIN users u ON so.userID = u.userID
WHERE sellerOrderID = %s;
