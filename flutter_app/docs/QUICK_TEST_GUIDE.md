# Quick Test Guide - Seller Login Redirect

## 🚀 Quick Start

### Build and Run
```bash
flutter clean
flutter pub get
flutter run
```

## 📋 Test Scenarios

### Scenario 1: Seller Login ✅

**Steps:**
1. Open app
2. Tap "Seller Portal" button
3. Click "Login" tab
4. Enter seller email: `seller@example.com`
5. Enter password: `password123`
6. Tap "Login as Seller"

**Expected Result:**
- ✅ Loading spinner appears
- ✅ Success message: "Welcome back, Seller!"
- ✅ Redirects to Seller Dashboard
- ✅ SellerShell displays with tabs: Dashboard, Orders, Products, Chat, Profile
- ✅ Dashboard tab shows statistics
- ✅ Orders tab shows orders from `/api/seller/orders`

**If it works:**
```
✅ Seller login redirect is working!
✅ Orders API integration is working!
```

---

### Scenario 2: Rider Login ✅

**Steps:**
1. Open app
2. Tap "Rider Portal" button
3. Click "Login" tab
4. Enter rider email: `rider@example.com`
5. Enter password: `password123`
6. Tap "Login as Rider"

**Expected Result:**
- ✅ Loading spinner appears
- ✅ Success message: "Welcome back, Rider!"
- ✅ Redirects to Rider Dashboard
- ✅ RiderShell displays

---

### Scenario 3: Customer Login ✅

**Steps:**
1. Open app (Home Screen)
2. Tap Profile icon (top right)
3. Click "Login" tab
4. Enter customer email: `customer@example.com`
5. Enter password: `password123`
6. Tap "Login as Customer"

**Expected Result:**
- ✅ Loading spinner appears
- ✅ Success message: "Welcome back, Customer!"
- ✅ Redirects to Home Screen
- ✅ User is logged in (profile icon shows user info)

---

### Scenario 4: Invalid Credentials ❌

**Steps:**
1. Open app
2. Tap "Seller Portal"
3. Click "Login" tab
4. Enter email: `seller@example.com`
5. Enter password: `wrongpassword`
6. Tap "Login as Seller"

**Expected Result:**
- ✅ Loading spinner appears
- ✅ Error message displays: "Invalid credentials" or similar
- ✅ Form remains on screen
- ✅ User can retry

---

### Scenario 5: Invalid Email Format ❌

**Steps:**
1. Open app
2. Tap "Seller Portal"
3. Click "Login" tab
4. Enter email: `notanemail`
5. Enter password: `password123`
6. Tap "Login as Seller"

**Expected Result:**
- ✅ Error message: "Enter a valid email address"
- ✅ Form validation prevents submission
- ✅ No API call made

---

### Scenario 6: Empty Fields ❌

**Steps:**
1. Open app
2. Tap "Seller Portal"
3. Click "Login" tab
4. Leave email and password empty
5. Tap "Login as Seller"

**Expected Result:**
- ✅ Error message: "Email is required" and "Password is required"
- ✅ Form validation prevents submission
- ✅ No API call made

---

### Scenario 7: Navigation Stack ✅

**Steps:**
1. Login as seller (see Scenario 1)
2. Verify you're on Seller Dashboard
3. Tap back button (or swipe back)

**Expected Result:**
- ✅ Goes back to Home Screen
- ✅ Does NOT go back to login screen
- ✅ Navigation stack is clean

---

### Scenario 8: Orders Tab ✅

**Steps:**
1. Login as seller (see Scenario 1)
2. Verify Dashboard tab shows
3. Tap "Orders" tab

**Expected Result:**
- ✅ Orders tab displays
- ✅ Shows loading indicator initially
- ✅ Orders load from `/api/seller/orders`
- ✅ Shows order list with order number, customer name, amount, status
- ✅ Can filter by status (Pending, Processing, Shipped, Delivered, Cancelled)
- ✅ Can tap order to see details

---

## 🐛 Troubleshooting

### Issue: Login button doesn't work
**Solution:**
- Check Flask backend is running
- Verify seller credentials in database
- Check network connection
- Look at console logs for errors

### Issue: Redirects to wrong screen
**Solution:**
- Check `AuthProvider.activeRole` is set correctly
- Verify routes in `lib/app.dart`
- Check `_navigateToDashboard()` logic

### Issue: Orders don't load
**Solution:**
- Check Flask `/api/seller/orders` endpoint is implemented
- Verify JWT token is being sent
- Check database has orders for this seller
- Look at network tab in DevTools

### Issue: Can go back to login screen
**Solution:**
- Check `pushNamedAndRemoveUntil` is being called
- Verify `route.isFirst` condition is correct
- Check navigation stack in DevTools

---

## 📊 Success Criteria

All of these should be ✅:

- [ ] Seller login redirects to seller dashboard
- [ ] Rider login redirects to rider dashboard
- [ ] Customer login redirects to home screen
- [ ] Orders tab loads and displays orders
- [ ] Error messages display for invalid input
- [ ] Navigation stack is clean (can't go back to login)
- [ ] Loading spinner shows during authentication
- [ ] Success message shows after login
- [ ] Can navigate between dashboard tabs
- [ ] Can filter orders by status

---

## 🎯 Key Endpoints to Verify

### Flask Backend Endpoints

1. **Seller Login**
   ```
   POST /api/seller/login
   Body: { email, password }
   Response: { success, token, seller }
   ```

2. **Seller Orders**
   ```
   GET /api/seller/orders?page=1&page_size=20
   Headers: Authorization: Bearer {token}
   Response: { success, orders, pagination }
   ```

### Check with curl:

```bash
# Login
curl -X POST http://localhost:5500/api/seller/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seller@example.com","password":"password123"}'

# Get orders (use token from login response)
curl -X GET http://localhost:5500/api/seller/orders \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 📝 Notes

- Seller credentials: `seller@example.com` / `password123`
- Rider credentials: `rider@example.com` / `password123`
- Customer credentials: `customer@example.com` / `password123`
- Flask backend should be running on `http://localhost:5500`
- Mobile app should be configured to use same backend URL

---

## ✅ When Everything Works

You should see:

1. **Seller Portal Login** → Seller Dashboard with Orders
2. **Rider Portal Login** → Rider Dashboard
3. **Customer Login** → Home Screen (logged in)
4. **Orders Tab** → Shows orders from API
5. **Error Handling** → Shows validation errors
6. **Navigation** → Clean stack, no back to login

**Congratulations! 🎉 The seller login redirect is working!**
