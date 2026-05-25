# JWT Authentication Debug Guide

## Problem
All seller API endpoints returning 401 Unauthorized errors, even though the Flutter app should be sending JWT tokens.

## Symptoms
```
POST /api/seller/login → 401
GET /api/seller/stats/sales → 401
GET /api/seller/orders → 401
GET /api/seller/products → 401
```

## Root Cause Analysis

### Possible Causes (in order of likelihood)

1. **JWT Token Not Being Sent**
   - Token not stored after login
   - Token not injected in Authorization header
   - Token is null or empty

2. **JWT Token Invalid**
   - Token expired
   - Token corrupted
   - Token format incorrect

3. **JWT Configuration Mismatch**
   - Flask JWT secret doesn't match token generation
   - JWT algorithm mismatch
   - JWT claims validation failing

4. **Flask JWT Not Configured**
   - JWT extension not initialized
   - JWT decorator not applied to endpoints
   - JWT error handlers not set up

---

## Step-by-Step Debugging

### Step 1: Verify Token is Being Stored

**In Flutter App:**

Add logging to `lib/providers/auth_provider.dart`:

```dart
Future<void> login({
  required String email,
  required String password,
  String? role,
}) async {
  // ... existing code ...
  
  try {
    final result = switch (_activeRole) {
      'seller' => await _service.loginAsSeller(
          email: trimmedEmail,
          password: password,
        ),
      // ... other roles ...
    };
    _user = result.user;
    _backendAccessToken = result.token;
    
    // ADD THIS DEBUG LOG
    print('✅ LOGIN SUCCESS');
    print('User: ${_user?.email}');
    print('Token: ${_backendAccessToken?.substring(0, 20)}...');
    print('Token length: ${_backendAccessToken?.length}');
    
    developer.log('Logged in as $_activeRole: ${_user?.email}');
  } catch (e) {
    print('❌ LOGIN FAILED: $e');
    _error = e.toString();
    developer.log('Login error: $e');
  } finally {
    _isLoading = false;
    notifyListeners();
  }
}
```

**Expected Output:**
```
✅ LOGIN SUCCESS
User: seller@example.com
Token: eyJhbGciOiJIUzI1NiIs...
Token length: 200+
```

**If Token is Empty/Null:**
- Check `MysqlAuthService.loginAsSeller()` is returning token
- Verify Flask `/api/seller/login` endpoint returns `token` field
- Check token is being saved to secure storage

---

### Step 2: Verify Token is Being Sent in Requests

**In Flutter App:**

Add logging to `lib/core/network/api_client.dart`:

```dart
Future<Map<String, String>> _headers({bool jsonBody = false}) async {
  final headers = <String, String>{
    'Accept': 'application/json',
  };
  if (jsonBody) {
    headers['Content-Type'] = 'application/json';
  }

  final token = await _tokenProvider();
  if (token != null && token.isNotEmpty) {
    headers['Authorization'] = 'Bearer $token';
    
    // ADD THIS DEBUG LOG
    print('✅ TOKEN INJECTED');
    print('Authorization: Bearer ${token.substring(0, 20)}...');
  } else {
    print('❌ NO TOKEN AVAILABLE');
  }
  
  return headers;
}

Future<Map<String, dynamic>> getJson(String path, {Map<String, String>? query}) async {
  final headers = await _headers();
  print('📤 GET $path');
  print('Headers: $headers');
  
  final res = await _client
      .get(_uri(path, query), headers: headers)
      .timeout(AppConfig.requestTimeout);
  
  print('📥 Response: ${res.statusCode}');
  
  return _decode(res);
}
```

**Expected Output:**
```
✅ TOKEN INJECTED
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
📤 GET /seller/orders
Headers: {Accept: application/json, Authorization: Bearer eyJ...}
📥 Response: 200
```

**If Token Not Injected:**
- `_tokenProvider()` is returning null
- Check AuthProvider is properly injected in main.dart
- Verify `getIdToken()` method in AuthProvider

**If Response is 401:**
- Token is being sent but Flask is rejecting it
- Check Flask JWT configuration (next step)

---

### Step 3: Check Flask JWT Configuration

**In Flask Backend (`../app/seller_api.py` or `../app/__init__.py`):**

Verify JWT is properly initialized:

```python
from flask_jwt_extended import JWTManager

# In app initialization
jwt = JWTManager(app)

# Check JWT configuration
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)
```

**Check JWT Error Handlers:**

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

**Check Seller Login Endpoint:**

```python
@app.route('/api/seller/login', methods=['POST'])
def seller_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Verify credentials
    seller = verify_seller_credentials(email, password)
    if not seller:
        return jsonify({"success": False, "msg": "Invalid credentials"}), 401
    
    # Generate JWT token
    access_token = create_access_token(
        identity=seller['sellerID'],
        additional_claims={
            'seller': {
                'sellerID': seller['sellerID'],
                'email': seller['email']
            }
        }
    )
    
    return jsonify({
        "success": True,
        "token": access_token,
        "seller": seller
    }), 200
```

**Check Protected Endpoints:**

```python
@app.route('/api/seller/orders', methods=['GET'])
@jwt_required()
def get_seller_orders():
    # Get seller ID from JWT
    claims = get_jwt()
    seller_id = claims.get('seller', {}).get('sellerID')
    
    if not seller_id:
        return jsonify({"success": False, "msg": "Invalid token"}), 401
    
    # ... rest of endpoint
```

---

### Step 4: Test JWT Token Manually

**Using cURL:**

```bash
# 1. Login and get token
curl -X POST http://localhost:5000/api/seller/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seller@example.com","password":"password123"}'

# Response should include token:
# {"success": true, "token": "eyJhbGciOiJIUzI1NiIs...", ...}

# 2. Use token to access protected endpoint
TOKEN="eyJhbGciOiJIUzI1NiIs..."
curl -X GET http://localhost:5000/api/seller/orders \
  -H "Authorization: Bearer $TOKEN"

# Should return 200 with orders data
```

**Using Postman:**

1. POST to `/api/seller/login`
   - Body: `{"email":"seller@example.com","password":"password123"}`
   - Copy token from response

2. GET to `/api/seller/orders`
   - Headers: `Authorization: Bearer <token>`
   - Should return 200

---

### Step 5: Check Token Claims

**In Flask Backend:**

Add logging to verify token claims:

```python
@app.route('/api/seller/orders', methods=['GET'])
@jwt_required()
def get_seller_orders():
    claims = get_jwt()
    print(f"JWT Claims: {claims}")
    print(f"Seller ID: {claims.get('seller', {}).get('sellerID')}")
    
    seller_id = claims.get('seller', {}).get('sellerID')
    if not seller_id:
        print("❌ No seller ID in token")
        return jsonify({"success": False, "msg": "Invalid token"}), 401
    
    print(f"✅ Seller ID: {seller_id}")
    # ... rest of endpoint
```

**Expected Output:**
```
JWT Claims: {'seller': {'sellerID': 1, 'email': 'seller@example.com'}, 'iat': 1715000000, 'exp': 1717592000}
Seller ID: 1
✅ Seller ID: 1
```

**If Seller ID is Missing:**
- Check `create_access_token()` is setting `additional_claims`
- Verify token structure matches what endpoints expect

---

## Common Issues and Solutions

### Issue 1: "Request does not contain an access token"

**Cause**: Authorization header not being sent

**Solution**:
1. Check ApiClient is injecting header
2. Verify token is not null
3. Check header format: `Authorization: Bearer <token>`

### Issue 2: "Signature verification failed"

**Cause**: JWT secret mismatch

**Solution**:
1. Verify Flask JWT_SECRET_KEY matches token generation
2. Check JWT algorithm is consistent (HS256)
3. Regenerate token and try again

### Issue 3: "Token has expired"

**Cause**: Token expiration time too short

**Solution**:
1. Increase JWT_ACCESS_TOKEN_EXPIRES in Flask
2. Regenerate token
3. Implement token refresh mechanism

### Issue 4: "Invalid token"

**Cause**: Token corrupted or malformed

**Solution**:
1. Check token is being stored correctly
2. Verify token is not being truncated
3. Check for encoding issues (UTF-8)

---

## Debugging Checklist

- [ ] Token is being stored after login (check AuthProvider)
- [ ] Token is being sent in Authorization header (check ApiClient)
- [ ] Token format is correct: `Bearer <token>`
- [ ] Flask JWT is initialized
- [ ] Flask JWT secret is configured
- [ ] Protected endpoints have `@jwt_required()` decorator
- [ ] Token claims include seller ID
- [ ] Token is not expired
- [ ] Token signature is valid

---

## Quick Test Script

**Add to Flutter app for quick testing:**

```dart
Future<void> testJWT() async {
  final authProvider = context.read<AuthProvider>();
  final apiClient = context.read<ApiClient>();
  
  print('=== JWT DEBUG ===');
  print('User: ${authProvider.user?.email}');
  print('Token: ${authProvider.backendAccessToken?.substring(0, 30)}...');
  
  try {
    final response = await apiClient.getJson('/seller/orders');
    print('✅ API Call Success: $response');
  } catch (e) {
    print('❌ API Call Failed: $e');
  }
}
```

---

## Next Steps

1. Add debug logging to Flutter app (Step 1-2)
2. Run app and check console output
3. Verify token is being stored and sent
4. Check Flask JWT configuration (Step 3)
5. Test manually with cURL/Postman (Step 4)
6. Check token claims (Step 5)
7. Fix any issues found
8. Restart Flask server
9. Test again in Flutter app

