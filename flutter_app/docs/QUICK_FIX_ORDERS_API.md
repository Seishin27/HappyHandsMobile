# Quick Fix: Orders API - Unknown Column Error

## Problem
```
Unknown column 'u.username' in 'field list'
```

## Root Cause
The `users` table doesn't have a `username` column. The corrected code was using `u.username` which doesn't exist.

## Solution
Replace `u.username` with `u.email` in all three order endpoints.

---

## Quick Fix (3 Changes)

### Change 1: GET /api/seller/orders

**Find:**
```python
COALESCE(u.username, 'Unknown Customer') as customerName,
```

**Replace with:**
```python
COALESCE(u.email, 'Unknown Customer') as customerName,
```

### Change 2: GET /api/seller/orders/<id>

**Find:**
```python
COALESCE(u.username, 'Unknown Customer') as customerName,
```

**Replace with:**
```python
COALESCE(u.email, 'Unknown Customer') as customerName,
```

### Change 3: PUT /api/seller/orders/<id>/status

**Find:**
```python
COALESCE(u.username, 'Unknown Customer') as customerName,
```

**Replace with:**
```python
COALESCE(u.email, 'Unknown Customer') as customerName,
```

---

## Steps to Apply

1. Open `../app/seller_api.py`
2. Use Find & Replace (Ctrl+H):
   - Find: `COALESCE(u.username, 'Unknown Customer')`
   - Replace: `COALESCE(u.email, 'Unknown Customer')`
   - Replace All (should find 3 occurrences)
3. Save file
4. Restart Flask server
5. Test orders endpoint

---

## Verification

After applying the fix, test with:
```bash
curl -X GET http://localhost:5000/api/seller/orders \
  -H "Authorization: Bearer <token>"
```

Should return 200 with orders data.

---

## If Email Column Doesn't Work

If you still get "Unknown column 'u.email'", check your users table schema:

```sql
DESCRIBE users;
```

Look for the column that contains customer names. Common alternatives:
- `firstName` + `lastName`
- `fullName`
- `name`
- `displayName`

Then replace `u.email` with the correct column name.

For example, if it's `firstName`:
```python
COALESCE(u.firstName, 'Unknown Customer') as customerName,
```

---

## Complete Fixed Code

See `docs/flask_seller_api_FINAL_FIX.py` for the complete corrected functions.

