# How to Fix the Backend RIGHT NOW

## The Problem
Your `seller_api.py` is using `u.username` but it should check if username exists first, or use email as fallback.

## The Solution (3 Steps)

### Step 1: Open seller_api.py
You already have it open in your editor.

### Step 2: Find and Replace These 3 Functions

#### Function 1: get_seller_orders (around line 551)
**Find the function that starts with:**
```python
@seller_api_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_seller_orders():
```

**Replace the ENTIRE function** with the code from `docs/COPY_PASTE_ORDERS_FIX.py` (lines 1-95)

#### Function 2: get_seller_order_details (around line 648)
**Find the function that starts with:**
```python
@seller_api_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_seller_order_details(order_id):
```

**Replace the ENTIRE function** with the code from `docs/COPY_PASTE_ORDERS_FIX.py` (lines 98-175)

#### Function 3: update_seller_order_status (around line 740)
**Find the function that starts with:**
```python
@seller_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_seller_order_status(order_id):
```

**Replace the ENTIRE function** with the code from `docs/COPY_PASTE_ORDERS_FIX.py` (lines 178-280)

### Step 3: Save and Restart
1. Save `seller_api.py` (Ctrl+S)
2. Restart your Flask server
3. Test the Flutter app

---

## What Changed?

### OLD (WRONG):
```sql
LEFT JOIN users b ON so.usersID = b.userID  -- typo: usersID
SELECT ... b.buyerName ...  -- column doesn't exist
```

### NEW (CORRECT):
```sql
LEFT JOIN users u ON so.userID = u.userID  -- correct column
SELECT ... COALESCE(u.username, u.email, 'Unknown Customer') ...  -- fallback to email
```

---

## Key Fixes:
1. ✅ `so.usersID` → `so.userID` (fixed typo)
2. ✅ `b.buyerName` → `COALESCE(u.username, u.email, 'Unknown Customer')` (handles missing username)
3. ✅ `so.orderNumber` → `so.order_number`
4. ✅ `so.totalAmount` → `so.total_amount`
5. ✅ `so.orderDate` → `so.items_received_at`
6. ✅ Removed `so.createdAt` and `so.updatedAt` (don't exist)

---

## After the Fix

Your orders should load correctly! ✅

If you still have issues, check the Flask console for any new error messages.

