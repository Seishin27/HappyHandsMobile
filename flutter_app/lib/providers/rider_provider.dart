import 'package:flutter/foundation.dart';

import '../models/rider_models.dart';
import '../services/flask_api_service.dart';

class RiderProvider extends ChangeNotifier {
  final FlaskApiService _api;

  RiderProvider(this._api);

  // Stats
  bool _loadingStats = false;
  String? _statsError;
  RiderStatsSummary _stats = const RiderStatsSummary.empty();

  // Orders
  bool _loadingOrders = false;
  String? _ordersError;
  List<RiderOrder> _orders = const [];

  bool _loadingDeliveredOrders = false;
  String? _deliveredOrdersError;
  List<RiderOrder> _deliveredOrders = const [];

  // Profile
  bool _loadingProfile = false;
  bool _savingProfile = false;
  String? _profileError;
  RiderProfile? _profile;

  // Legacy compat
  bool get isLoading => _loadingOrders;
  String? get error => _ordersError;
  List<RiderOrderSummary> get orders => _orders.map((o) => RiderOrderSummary(
    sellerOrderId: o.sellerOrderId,
    orderNumber: o.orderNumber,
    status: o.status,
    customerName: o.userName,
  )).toList();

  bool get loadingStats => _loadingStats;
  String? get statsError => _statsError;
  RiderStatsSummary get stats => _stats;

  bool get loadingOrders => _loadingOrders;
  String? get ordersError => _ordersError;
  List<RiderOrder> get activeOrders => _orders;

  bool get loadingDeliveredOrders => _loadingDeliveredOrders;
  String? get deliveredOrdersError => _deliveredOrdersError;
  List<RiderOrder> get deliveredOrders => _deliveredOrders;

  bool get loadingProfile => _loadingProfile;
  bool get savingProfile => _savingProfile;
  String? get profileError => _profileError;
  RiderProfile? get profile => _profile;

  Future<void> loadDashboard() async {
    await Future.wait([loadStats(), loadActiveOrders()]);
  }

  Future<void> loadStats() async {
    if (_loadingStats) return;
    _loadingStats = true;
    _statsError = null;
    notifyListeners();
    try {
      _stats = await _api.fetchRiderStats();
    } catch (e) {
      _statsError = e.toString();
    } finally {
      _loadingStats = false;
      notifyListeners();
    }
  }

  Future<void> loadOrders() => loadActiveOrders();

  Future<void> loadActiveOrders() async {
    if (_loadingOrders) return;
    _loadingOrders = true;
    _ordersError = null;
    notifyListeners();
    try {
      _orders = await _api.fetchRiderActiveOrders();
    } catch (e) {
      _ordersError = e.toString();
    } finally {
      _loadingOrders = false;
      notifyListeners();
    }
  }

  Future<void> loadDeliveredOrders() async {
    if (_loadingDeliveredOrders) return;
    _loadingDeliveredOrders = true;
    _deliveredOrdersError = null;
    notifyListeners();
    try {
      _deliveredOrders = await _api.fetchRiderDeliveredOrders();
    } catch (e) {
      _deliveredOrdersError = e.toString();
    } finally {
      _loadingDeliveredOrders = false;
      notifyListeners();
    }
  }

  Future<bool> respondToOrder(int orderId, String action) async {
    try {
      await _api.riderRespondToOrder(orderId, action);
      await loadActiveOrders();
      return true;
    } catch (e) {
      _ordersError = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateOrderStatus(int orderId, String status) async {
    try {
      await _api.riderUpdateOrderStatus(orderId, status);
      await loadActiveOrders();
      return true;
    } catch (e) {
      _ordersError = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> loadProfile() async {
    if (_loadingProfile) return;
    _loadingProfile = true;
    _profileError = null;
    notifyListeners();
    try {
      _profile = await _api.fetchRiderProfile();
    } catch (e) {
      _profileError = e.toString();
    } finally {
      _loadingProfile = false;
      notifyListeners();
    }
  }

  Future<bool> saveProfile(Map<String, String> fields) async {
    _savingProfile = true;
    _profileError = null;
    notifyListeners();
    try {
      await _api.updateRiderProfile(fields);
      await loadProfile();
      return true;
    } catch (e) {
      _profileError = e.toString();
      return false;
    } finally {
      _savingProfile = false;
      notifyListeners();
    }
  }

  Future<bool> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    _savingProfile = true;
    _profileError = null;
    notifyListeners();
    try {
      await _api.changeRiderPassword(
        currentPassword: currentPassword,
        newPassword: newPassword,
      );
      return true;
    } catch (e) {
      _profileError = e.toString();
      return false;
    } finally {
      _savingProfile = false;
      notifyListeners();
    }
  }

  // ── Proof of Delivery ────────────────────────────────────────────────────

  bool _uploadingPod = false;
  String? _podUploadError;
  // orderId → pod_image_url
  final Map<int, String?> _podUrls = {};

  bool get uploadingPod => _uploadingPod;
  String? get podUploadError => _podUploadError;

  String? podUrlFor(int orderId) => _podUrls[orderId];

  Future<bool> uploadPod({
    required int orderId,
    required Uint8List bytes,
    required String fileName,
  }) async {
    _uploadingPod = true;
    _podUploadError = null;
    notifyListeners();
    try {
      final result = await _api.uploadPod(
        orderId: orderId,
        bytes: bytes,
        fileName: fileName,
      );
      _podUrls[orderId] = result['pod_image_url'];
      return true;
    } catch (e) {
      _podUploadError = e.toString();
      return false;
    } finally {
      _uploadingPod = false;
      notifyListeners();
    }
  }

  Future<void> loadPodStatus(int orderId) async {
    try {
      final result = await _api.fetchPod(orderId);
      _podUrls[orderId] = result['pod_image_url'] as String?;
      notifyListeners();
    } catch (_) {
      // silently ignore — POD section will show fallback
    }
  }

  void reset() {
    _stats = const RiderStatsSummary.empty();
    _orders = const [];
    _profile = null;
    _statsError = null;
    _ordersError = null;
    _profileError = null;
    notifyListeners();
  }
}
