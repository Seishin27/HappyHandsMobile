-- Test query to verify the JOIN works
-- Run this in MySQL Workbench

SELECT 
    so.sellerOrderID,
    so.orderNumber,
    u.username,
    u.userID,
    so.buyerID
FROM seller_orders so
LEFT JOIN users u ON so.buyerID = u.userID
LIMIT 5;

-- If this fails, try without alias:
SELECT 
    seller_orders.sellerOrderID,
    seller_orders.orderNumber,
    users.username,
    users.userID,
    seller_orders.buyerID
FROM seller_orders
LEFT JOIN users ON seller_orders.buyerID = users.userID
LIMIT 5;

-- Also check if buyerID column exists in seller_orders:
DESCRIBE seller_orders;
