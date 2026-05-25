import 'package:flutter/foundation.dart';

import '../models/seller_stats.dart';
import '../services/flask_api_service.dart';

class SellerProvider extends ChangeNotifier {
  final FlaskApiService _api;

  SellerProvider(this._api);

  bool _isLoading = false;
  String? _error;

  SellerStatsSummary summary = const SellerStatsSummary.empty();
  List<SellerSalesPoint> sales = const [];
  List<SellerOrdersPoint> orders = const [];
  List<SellerRecentOrder> recentOrders = const [];

  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Fetches all dashboard data from the API in parallel:
  /// - /api/seller/stats/summary
  /// - /api/seller/stats/sales
  /// - /api/seller/stats/orders
  /// - /api/seller/stats/recent-orders
  ///
  /// No cache short-circuit on purpose — every entry to the dashboard tab
  /// pulls fresh data so the user never sees stale numbers.
  Future<void> fetchDashboardStats() async {
    if (_isLoading) return;
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final results = await Future.wait([
        _api.fetchSellerSummary(),
        _api.fetchSellerSalesDaily(),
        _api.fetchSellerOrdersDaily(),
        _api.fetchSellerRecentOrders(),
      ]);
      summary      = results[0] as SellerStatsSummary;
      sales        = results[1] as List<SellerSalesPoint>;
      orders       = results[2] as List<SellerOrdersPoint>;
      recentOrders = results[3] as List<SellerRecentOrder>;
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Pull-to-refresh.
  Future<void> refresh() => fetchDashboardStats();

  /// Legacy alias kept for backward compatibility.
  @Deprecated('Use fetchDashboardStats() instead')
  Future<void> loadDashboard() => fetchDashboardStats();

  /// Clear all cached state — call on logout.
  void reset() {
    summary = const SellerStatsSummary.empty();
    sales = const [];
    orders = const [];
    recentOrders = const [];
    _error = null;
    notifyListeners();
  }
}

