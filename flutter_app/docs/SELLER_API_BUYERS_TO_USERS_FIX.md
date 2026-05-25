# Fix: Replace 'buyers' Table with 'users' Table

## Problem
The Flask backend is trying to JOIN with a `buyers` table that doesn't exist. The database uses `users` table instead.

**Error:**
```
Error fetching seller orders: 1146 (42S02): Table 'babystore.buyers' doesn't exist
```

## Solution
Replace all references to `buyers` table with `users` table in the seller_api.py file.

---

## Changes Required

### Change 1: GET /api/seller/orders (Line ~380)

**FIND THIS:**
```python
        # Build query - using camelCase column names to match actual database schema
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

**REPLACE WITH:**
```python
        # Build query - using camelCase column names to match actual database schema
        query = """
            SELECT 
                so.sellerOrderID as id,
                so.orderNumber,
                COALESCE(u.username, 'Unknown Customer') as customerName,
                so.totalAmount,
                so.status,
                so.orderDate,
                so.createdAt,
                so.updatedAt
            FROM seller_orders so
            LEFT JOIN users u ON so.buyerID = u.userID
            WHERE so.sellerID = %s
        """
```

---

### Change 2: GET /api/seller/orders/<id> (Line ~450)

**FIND THIS:**
```python
        # Fetch order - using camelCase column names
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

**REPLACE WITH:**
```python
        # Fetch order - using camelCase column names
        cur.execute("""
            SELECT 
                so.sellerOrderID as id,
                so.orderNumber,
                COALESCE(u.username, 'Unknown Customer') as customerName,
                so.totalAmount,
                so.status,
                so.orderDate,
                so.createdAt,
                so.updatedAt
            FROM seller_orders so
            LEFT JOIN users u ON so.buyerID = u.userID
            WHERE so.sellerOrderID = %s AND so.sellerID = %s
        """, (order_id, seller_id))
```

---

### Change 3: PUT /api/seller/orders/<id>/status (Line ~530)

**FIND THIS:**
```python
        # Fetch updated order
        cur.execute("""
            SELECT 
                sellerOrderID as id,
                orderNumber,
                COALESCE(b.buyerName, 'Unknown Customer') as customerName,
                totalAmount,
                status,
                orderDate,
                createdAt,
                updatedAt
            FROM seller_orders so
            LEFT JOIN buyers b ON so.buyerID = b.buyerID
            WHERE sellerOrderID = %s
        """, (order_id,))
```

**REPLACE WITH:**
```python
        # Fetch updated order
        cur.execute("""
            SELECT 
                sellerOrderID as id,
                orderNumber,
                COALESCE(u.username, 'Unknown Customer') as customerName,
                totalAmount,
                status,
                orderDate,
                createdAt,
                updatedAt
            FROM seller_orders so
            LEFT JOIN users u ON so.buyerID = u.userID
            WHERE sellerOrderID = %s
        """, (order_id,))
```

---

## Summary of Changes

| What | Old | New |
|---|---|---|
| Table Name | `buyers` | `users` |
| Table Alias | `b` | `u` |
| Customer Name Column | `b.buyerName` | `u.username` |
| User ID Column | `b.buyerID` | `u.userID` |
| JOIN Condition | `so.buyerID = b.buyerID` | `so.buyerID = u.userID` |

---

## How to Apply

1. Open `../app/seller_api.py` in your editor
2. Find each section above (use Ctrl+F to search)
3. Replace the old code with the new code
4. Save the file
5. Restart Flask server
6. Test orders in Flutter app

---

## Verification

After making changes, run this query in MySQL to verify:

```sql
SELECT 
    so.sellerOrderID,
    so.orderNumber,
    u.username,
    so.totalAmount,
    so.status,
    so.orderDate
FROM seller_orders so
LEFT JOIN users u ON so.buyerID = u.userID
LIMIT 5;
```

Should return data without errors.

---

## Expected Result

✅ Orders list will load correctly
✅ Customer names will display from `users` table
✅ No more "Table 'babystore.buyers' doesn't exist" error
