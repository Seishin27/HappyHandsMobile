import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

import 'flask_api_service.dart';

class LocationService extends ChangeNotifier {
  Timer? _timer;
  int? _activeOrderId;
  bool _tracking = false;

  bool get isTracking => _tracking;

  Future<bool> _ensurePermission() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return false;

    LocationPermission perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    return perm == LocationPermission.whileInUse || perm == LocationPermission.always;
  }

  Future<void> startTracking(int orderId, FlaskApiService api) async {
    if (_tracking && _activeOrderId == orderId) return;
    stopTracking();

    final hasPermission = await _ensurePermission();
    if (!hasPermission) return;

    _activeOrderId = orderId;
    _tracking = true;
    notifyListeners();

    Future<void> sendLocation() async {
      try {
        final pos = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
        );
        await api.updateRiderLocation(orderId, pos.latitude, pos.longitude);
      } catch (_) {}
    }

    await sendLocation();
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => sendLocation());
  }

  void stopTracking() {
    _timer?.cancel();
    _timer = null;
    _activeOrderId = null;
    _tracking = false;
    notifyListeners();
  }

  @override
  void dispose() {
    stopTracking();
    super.dispose();
  }
}
