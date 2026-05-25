# Run the Flutter app on a physical device (USB or Wi-Fi debug).
# Uses .env to set API_BASE_URL so the app reaches the Flask server over LAN.
#
# If login still fails, check your PC's current IP with `ipconfig` and update
# the API_BASE_URL line in flutter_app/.env to match.

flutter run --dart-define-from-file=.env
