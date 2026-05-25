-- Run these queries in MySQL Workbench to find the correct column names

-- 1. Check users table columns
DESCRIBE users;

-- 2. Check products table columns
DESCRIBE products;

-- 3. Check seller_orders table columns
DESCRIBE seller_orders;

-- 4. Sample data from users (to see what column has customer names)
SELECT * FROM users LIMIT 3;

-- 5. Sample data from products (to see what column has product names)
SELECT * FROM products LIMIT 3;

-- 6. Sample data from seller_orders
SELECT * FROM seller_orders LIMIT 3;

-- 7. Check if there's a join between seller_orders and users
SELECT 
    so.*,
    u.*
FROM seller_orders so
LEFT JOIN users u ON so.buyerID = u.userID
LIMIT 1;
