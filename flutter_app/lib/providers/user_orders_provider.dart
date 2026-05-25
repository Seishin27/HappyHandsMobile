import 'package:flutter/foundation.dart';
import 'dart:developer' as developer;

import '../services/flask_api_service.dart';

/// Provider for managing user order state.
///
/// Handles fetching user orders, order details, and filtering.
class UserOrdersProvider extends ChangeNotifier {
  final FlaskApiService _apiService;

  UserOrdersProvider(this._apiService);

  bool _isLoading = false;
  String? _error;
  List<Map<String, dynamic>> _orders = const [];
  Map<String, dynamic>? _selectedOrder;
  String? _statusFilter;
  String _searchQuery = '';

  bool get isLoading => _isLoading;
  String? get error => _error;
  List<Map<String, dynamic>> get orders => _orders;
  Map<String, dynamic>? get selectedOrder => _selectedOrder;
  String? get statusFilter => _statusFilter;
  String get searchQuery => _searchQuery;

  /// Returns filtered orders based on the current status filter and search query.
  List<Map<String, dynamic>> get filteredOrders {
    var result = List<Map<String, dynamic>>.from(_orders);

    // Apply status filter
    if (_statusFilter != null && _statusFilter!.isNotEmpty) {
      result = result.where((order) {
        final status = order['status']?.toString().toLowerCase() ?? '';
        return status == _statusFilter!.toLowerCase();
      }).toList();
    }

    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      result = result.where((order) {
        final orderNumber = order['order_number']?.toString().toLowerCase() ?? '';
        return orderNumber.contains(q);
      }).toList();
    }

    return result;
  }

  /// Returns count of orders for each status (for filter chip badges).
  Map<String, int> get statusCounts {
    final counts = <String, int>{'all': _orders.length};
    for (final order in _orders) {
      final status = order['status']?.toString().toLowerCase() ?? 'unknown';
      counts[status] = (counts[status] ?? 0) + 1;
    }
    return counts;
  }

  /// Sets the search query for filtering orders.
  void setSearchQuery(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  /// Fetches paginated list of user orders from the API.
  Future<void> fetchOrders({int page = 1, int pageSize = 20}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _orders = await _apiService.fetchUserOrders(
        page: page,
        pageSize: pageSize,
      );
      developer.log('Loaded ${_orders.length} user orders.');
    } catch (e) {
      _error = 'Failed to load orders: $e';
      developer.log('Error in UserOrdersProvider.fetchOrders: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetches detailed information for a specific order.
  Future<void> fetchOrderDetails(String orderId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _selectedOrder = await _apiService.fetchUserOrderDetails(orderId);
      developer.log('Loaded order details for order ID: $orderId');
    } catch (e) {
      _error = 'Failed to load order details: $e';
      developer.log('Error in UserOrdersProvider.fetchOrderDetails: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Sets the status filter for orders.
  void setStatusFilter(String? status) {
    _statusFilter = status;
    developer.log('Set order status filter to: ${status ?? "none"}');
    notifyListeners();
  }

  /// Clears the status filter.
  void clearStatusFilter() {
    _statusFilter = null;
    developer.log('Cleared order status filter');
    notifyListeners();
  }

  /// Clears the selected order.
  void clearSelectedOrder() {
    _selectedOrder = null;
    notifyListeners();
  }

  /// Clears any error state.
  void clearError() {
    _error = null;
    notifyListeners();
  }

  /// Confirms the buyer has received the order, then refreshes the list.
  Future<bool> confirmOrderReceived(int sellerOrderId) async {
    try {
      await _apiService.confirmOrderReceived(sellerOrderId);
      await fetchOrders();
      return true;
    } catch (e) {
      _error = 'Failed to confirm receipt: $e';
      notifyListeners();
      return false;
    }
  }

  /// Fetches the POD image URL for a single delivered order.
  /// Returns the URL string or null if not available.
  Future<String?> fetchPodForOrder(int sellerOrderId) async {
    try {
      final result = await _apiService.fetchPod(sellerOrderId);
      return result['pod_image_url'] as String?;
    } catch (_) {
      return null;
    }
  }
}
