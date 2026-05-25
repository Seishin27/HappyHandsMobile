# Quick Start Checklist

## ✅ Configuration Status

- [x] `.env` file configured with `http://192.168.1.12:5500/api`
- [x] `app_config.dart` reads from environment variable
- [x] Flutter models updated to match database schema
- [x] Debug logging enabled in API service

## ⏳ Backend Status

- [ ] Flask `seller_api.py` updated with corrected SQL queries
- [ ] Flask server running on `192.168.1.12:5500`
- [ ] Firewall allows connections on port 5500

---

## Step-by-Step: Get Everything Working

### Step 1: Fix Flask Backend (REQUIRED)

1. Open `seller_api.py`
2. Replace 3 functions with code from `docs/COPY_PASTE_ORDERS_FIX.py`:
   - `get_seller_orders`
   - `get_seller_order_details`
   - `update_seller_order_status`
3. Save file

### Step 2: Start Flask Server

```bash
cd "Happy Hands SUPER FINAL"
python run.py
```

Should show:
```
* Running on http://192.168.1.12:5500
```

### Step 3: Run Flutter App

```bash
flutter run --dart-define-from-file=.env
```

### Step 4: Test

1. Login as seller
2. Check Orders tab - should load ✅
3. Check Products tab - should load ✅
4. Check Profile tab - should load ✅

---

## If Orders Still Don't Load

### Check Flask Console

Look for error messages like:
```
Error fetching seller orders: 1054 (42S22): Unknown column 'u.username'
```

If you see this, the backend hasn't been updated yet.

### Check Flutter Console

Look for debug logs:
```
📥 Raw orders response: {...}
📦 Found X orders
```

This shows what the backend is returning.

---

## Common Issues

### Issue 1: "Connection refused"
**Solution:** Flask server not running or wrong IP
- Check Flask is running on 192.168.1.12:5500
- Check phone and PC on same Wi-Fi

### Issue 2: "Unknown column 'u.username'"
**Solution:** Backend not updated
- Apply fixes from `docs/COPY_PASTE_ORDERS_FIX.py`
- Restart Flask server

### Issue 3: "401 Unauthorized"
**Solution:** JWT authentication issue
- Check seller login is working
- Check JWT token is being sent

---

## Success Criteria

When everything works, you should see:

✅ Login as seller succeeds
✅ Dashboard shows statistics
✅ Orders tab shows list of orders
✅ Products tab shows list of products
✅ Profile tab shows seller info
✅ No error messages in console

---

## Current Status

**Flutter App:** ✅ Ready (configured for 192.168.1.12:5500)
**Backend:** ⏳ Needs SQL query fixes
**Next Step:** Update `seller_api.py` with corrected queries

