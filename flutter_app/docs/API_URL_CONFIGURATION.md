# API URL Configuration - 192.168.1.12:5500

## Current Configuration ✅

Your Flutter app is already configured to use:
```
http://192.168.1.12:5500/api
```

This is set in the `.env` file.

---

## How to Run the App with This Configuration

### Option 1: Using .env file (Recommended)

Run the app with:
```bash
flutter run --dart-define-from-file=.env
```

Or build APK with:
```bash
flutter build apk --dart-define-from-file=.env
```

### Option 2: Override at Runtime

You can also override the URL when running:
```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.12:5500/api
```

---

## Verify the Configuration

After starting the app, check the console logs. You should see API calls going to:
```
http://192.168.1.12:5500/api/seller/orders
http://192.168.1.12:5500/api/seller/products
```

---

## For Different Devices

### Android Emulator
If running on Android emulator, use:
```
API_BASE_URL=http://10.0.2.2:5500/api
```

### Physical Phone (Same Wi-Fi)
If running on physical phone connected to same Wi-Fi as your PC:
```
API_BASE_URL=http://192.168.1.12:5500/api
```
(This is what you have now ✅)

### iOS Simulator / Desktop
If running on iOS simulator or desktop:
```
API_BASE_URL=http://127.0.0.1:5500/api
```

---

## Current Setup Summary

✅ `.env` file configured with: `http://192.168.1.12:5500/api`
✅ `app_config.dart` reads from environment variable
✅ Ready to use!

---

## Testing

1. Make sure Flask server is running on `192.168.1.12:5500`
2. Run Flutter app with: `flutter run --dart-define-from-file=.env`
3. Login as seller
4. Check if orders and products load

---

## Troubleshooting

### If app can't connect:

1. **Check Flask is running:**
   ```bash
   # On your PC, Flask should show:
   * Running on http://192.168.1.12:5500
   ```

2. **Check firewall:**
   - Windows Firewall might be blocking port 5500
   - Allow Python/Flask through firewall

3. **Check same network:**
   - Phone and PC must be on same Wi-Fi network
   - Check PC IP with `ipconfig` (should be 192.168.1.12)

4. **Test connection:**
   - Open browser on phone
   - Go to: `http://192.168.1.12:5500`
   - Should see Flask app

---

## Quick Commands

### Run app with .env:
```bash
flutter run --dart-define-from-file=.env
```

### Build APK with .env:
```bash
flutter build apk --dart-define-from-file=.env
```

### Run with custom URL:
```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.12:5500/api
```

