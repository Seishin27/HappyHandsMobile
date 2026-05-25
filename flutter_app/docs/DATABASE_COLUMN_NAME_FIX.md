# Database Column Name Fix Guide

## Current Errors

1. **Orders Error**: `Unknown column 'u.username' in 'field list'`
2. **Products Error**: `Unknown column 'productname' in 'field list'`

## Root Cause

The Flask API is using column names that don't exist in your database. We need to find the actual column names.

---

## Step 1: Find Correct Column Names

### Option A: Using MySQL Workbench (RECOMMENDED)

1. Open MySQL Workbench
2. Connect to your database
3. Run these queries:

```sql
-- Check users table structure
DESCRIBE users;

-- Check products table structure
DESCRIBE products;

-- Check seller_orders table structure
DESCRIBE seller_orders;
```

Look for columns that contain:
- **Users table**: Customer name (could be: `email`, `name`, `firstName`, `fullName`, `user_name`, etc.)
- **Products table**: Product name (could be: `name`, `product_name`, `title`, etc.)

### Option B: Check Sample Data

```sql
-- See actual column names in users
SELECT * FROM users LIMIT 1;

-- See actual column names in products
SELECT * FROM products LIMIT 1;
```

---

## Step 2: Common Column Name Patterns

Based on your database, the columns are likely one of these:

### Users Table - Customer Name Column
- `email` ← Most likely
- `name`
- `firstName` + `lastName`
- `fullName`
- `user_name`
- `username` (but this doesn't exist in your case)

### Products Table - Product Name Column
- `name` ← Most likely
- `product_name`
- `title`
- `productName` (camelCase)
- `productname` (but this doesn't exist in your case)

---

## Step 3: Apply the Fix

Once you know the correct column names, update `seller_api.py`:

### Fix for Orders (3 locations)

**Find:**
```python
COALESCE(u.username, 'Unknown Customer') as customerName,
```

**Replace with** (use YOUR actual column name):
```python
COALESCE(u.email, 'Unknown Customer') as customerName,
# OR
COALESCE(u.name, 'Unknown Customer') as customerName,
# OR
COALESCE(CONCAT(u.firstName, ' ', u.lastName), 'Unknown Customer') as customerName,
```

### Fix for Products (multiple locations)

**Find all instances of:**
```python
productname
```

**Replace with** (use YOUR actual column name):
```python
name
# OR
product_name
# OR
productName
```

**Specific locations to fix:**

1. **GET /api/seller/products** (around line 145):
```python
# OLD
productname as name,

# NEW (if column is 'name')
name as name,
# OR (if column is 'product_name')
product_name as name,
```

2. **POST /api/seller/products** (around line 251):
```python
# OLD
(productname, productdescription, ...)

# NEW (if column is 'name')
(name, productdescription, ...)
# OR (if column is 'product_name')
(product_name, productdescription, ...)
```

3. **PUT /api/seller/products** (around line 352):
```python
# OLD
update_fields.append("productname = %s")

# NEW (if column is 'name')
update_fields.append("name = %s")
# OR (if column is 'product_name')
update_fields.append("product_name = %s")
```

---

## Step 4: Quick Find & Replace

### For Orders (if using 'email'):
- Find: `u.username`
- Replace: `u.email`
- Replace All

### For Products (if using 'name'):
- Find: `productname`
- Replace: `name`
- Replace All

### For Products (if using 'product_name'):
- Find: `productname`
- Replace: `product_name`
- Replace All

---

## Step 5: Check Other Columns Too

While you're at it, verify these columns also exist:

### Products Table
- `productdescription` → might be `description` or `product_description`
- `productprice` → might be `price` or `product_price`
- `productcategory` → might be `category` or `product_category`
- `productquantity` → might be `quantity` or `stock_quantity`

### Seller Orders Table
- `sellerOrderID` → might be `seller_order_id` or `id`
- `orderNumber` → might be `order_number`
- `totalAmount` → might be `total_amount`
- `orderDate` → might be `order_date`
- `createdAt` → might be `created_at`
- `updatedAt` → might be `updated_at`

---

## Step 6: Test After Fix

1. Save `seller_api.py`
2. Restart Flask server
3. Test orders endpoint
4. Test products endpoint

---

## Need Help?

If you're still getting errors, please:

1. Run `DESCRIBE users;` in MySQL Workbench
2. Run `DESCRIBE products;` in MySQL Workbench
3. Share the output (column names)
4. I'll create the exact fix for you

---

## Example: Complete Fix

If your database uses:
- Users: `email` column
- Products: `name` column

Then the fixes are:

**Orders (3 places):**
```python
COALESCE(u.email, 'Unknown Customer') as customerName,
```

**Products (multiple places):**
```python
# In SELECT queries
name as name,

# In INSERT queries
(name, description, price, ...)

# In UPDATE queries
update_fields.append("name = %s")
```

