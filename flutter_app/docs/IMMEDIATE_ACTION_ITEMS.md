# Immediate Action Items - May 7, 2026

## 🔴 CRITICAL: Two Blocking Issues

Both issues must be resolved before Phase 4 (Chat) can proceed.

---

## Action Item 1: Fix Flask Backend - Table Name Mismatch

### Priority: 🔴 CRITICAL
### Estimated Time: 10-15 minutes
### Status: AWAITING USER ACTION

### Problem
Orders API failing with: `Table 'babystore.buyers' doesn't exist`

### Solution

**File to Update**: `../app/seller_api.py`

**Changes Required**: 3 locations

#### Change 1: GET /api/seller/orders (around line 380)

Find this code:
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

Replace with:
```python
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

#### Change 2: GET /api/seller/orders/<id> (around line 450)

Find this code:
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

Replace with:
```python
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

#### Change 3: PUT /api/seller/orders/<id>/status (around line 530)

Find this code:
```python
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

Replace with:
```python
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

### After Making Changes

1. Save the file
2. Restart Flask server
3. Test orders endpoint:
   ```bash
   curl -X GET http://localhost:5000/api/seller/orders \
     -H "Authorization: Bearer <token>"
   ```
4. Should return 200 with orders data (not 500 error)

### Verification

Run this SQL query to verify the fix works:
```sql
SELECT 
    so.sellerOrderID,
    so.orderNumber,
    u.username,
    so.totalAmount,
    so.status
FROM seller_orders so
LEFT JOIN users u ON so.buyerID = u.userID
LIMIT 5;
```

Should return data without errors.

---

## Action Item 2: Debug JWT Authentication - 401 Errors

### Priority: 🔴 CRITICAL
### Estimated Time: 30-45 minutes
### Status: INVESTIGATING

### Problem
All seller API endpoints returning 401 Unauthorized

### Root Cause
Unknown - could be:
1. Token not being sent
2. Token invalid/expired
3. Flask JWT misconfigured
4. Token claims incorrect

### Investigation Steps

#### Step 1: Check Flask JWT Configuration

**File**: `../app/__init__.py` or `../app/run.py`

**Look for**:
```python
from flask_jwt_extended import JWTManager

jwt = JWTManager(app)

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
app.config['JWT_ALGORITHM'] = 'HS256'
```

**If Missing**: Add JWT initialization

#### Step 2: Verify Seller Login Returns Token

**Test with cURL**:
```bash
curl -X POST http://localhost:5000/api/seller/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seller@example.com","password":"password123"}'
```

**Expected Response**:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "seller": {...}
}
```

**If No Token**: Check login endpoint implementation

#### Step 3: Test Token with Protected Endpoint

**Get token from Step 2**, then:
```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."
curl -X GET http://localhost:5000/api/seller/orders \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: 200 with orders data

**If 401**: Token is invalid or Flask JWT not configured

#### Step 4: Check Flask JWT Error Handlers

**File**: `../app/__init__.py` or `../app/run.py`

**Should have**:
```python
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_data):
    return jsonify({"msg": "Token has expired"}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"msg": "Signature verification failed"}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"msg": "Request does not contain an access token"}), 401
```

**If Missing**: Add error handlers

#### Step 5: Check Protected Endpoint Decorator

**File**: `../app/seller_api.py`

**All protected endpoints should have**:
```python
@app.route('/api/seller/orders', methods=['GET'])
@jwt_required()  # ← THIS IS REQUIRED
def get_seller_orders():
    claims = get_jwt()
    seller_id = claims.get('seller', {}).get('sellerID')
    # ... rest of endpoint
```

**If Missing**: Add `@jwt_required()` decorator

### Debugging Checklist

- [ ] Flask JWT is initialized
- [ ] JWT_SECRET_KEY is configured
- [ ] Seller login returns valid token
- [ ] Token can be used to access protected endpoints
- [ ] JWT error handlers are set up
- [ ] Protected endpoints have @jwt_required() decorator
- [ ] Token claims include seller ID

### If Still Getting 401

1. Check Flask logs for JWT error messages
2. Verify JWT_SECRET_KEY is the same for token generation and validation
3. Check token expiration time
4. Verify token format: `Authorization: Bearer <token>`
5. Check for typos in endpoint paths

### Reference Documentation

See `docs/JWT_AUTHENTICATION_DEBUG_GUIDE.md` for detailed debugging steps.

---

## Action Item 3: Test After Fixes

### Priority: 🟡 HIGH
### Estimated Time: 15-20 minutes
### Status: PENDING

### Testing Checklist

After fixing both issues, test the following:

#### Orders Functionality
- [ ] Orders list loads without errors
- [ ] Customer names display correctly
- [ ] Order amounts display correctly
- [ ] Order status displays correctly
- [ ] Can click on order to view details
- [ ] Can update order status
- [ ] Filter by status works

#### Profile Functionality
- [ ] Profile loads without errors
- [ ] Profile fields display correctly
- [ ] Can edit profile
- [ ] Can save profile changes
- [ ] Can change password
- [ ] Password validation works

#### Products Functionality
- [ ] Products list loads without errors
- [ ] Can create new product
- [ ] Can edit product
- [ ] Can delete product
- [ ] Image upload works

#### Dashboard Functionality
- [ ] Dashboard statistics load
- [ ] Recent orders display
- [ ] All tabs accessible
- [ ] Navigation works smoothly

### Test Commands

**Test Orders Endpoint**:
```bash
curl -X GET http://localhost:5000/api/seller/orders \
  -H "Authorization: Bearer <token>"
```

**Test Profile Endpoint**:
```bash
curl -X GET http://localhost:5000/api/seller/profile \
  -H "Authorization: Bearer <token>"
```

**Test Products Endpoint**:
```bash
curl -X GET http://localhost:5000/api/seller/products \
  -H "Authorization: Bearer <token>"
```

All should return 200 with data.

---

## Summary

| Item | Priority | Time | Status | Action |
|------|----------|------|--------|--------|
| Fix Flask Backend (buyers → users) | 🔴 CRITICAL | 10-15 min | AWAITING | Update 3 SQL queries in seller_api.py |
| Debug JWT Authentication | 🔴 CRITICAL | 30-45 min | INVESTIGATING | Follow debugging steps, check Flask config |
| Test After Fixes | 🟡 HIGH | 15-20 min | PENDING | Run test checklist |

---

## Next Phase (After Fixes)

Once both issues are resolved:

1. **Phase 4: Real-Time Chat** (Tasks 25-32)
   - Integrate Socket.IO
   - Create chat models and provider
   - Build chat UI

2. **Phase 5: Notifications** (Tasks 33-39)
   - Create notification models and provider
   - Build notifications UI

3. **Final Integration** (Tasks 40-41)
   - Integration testing
   - Final validation

---

## Questions?

Refer to:
- `docs/SELLER_API_BUYERS_TO_USERS_FIX.md` - Detailed fix instructions
- `docs/JWT_AUTHENTICATION_DEBUG_GUIDE.md` - JWT debugging guide
- `docs/CURRENT_STATUS_AND_ACTION_PLAN.md` - Full status overview

