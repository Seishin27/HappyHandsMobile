import 'package:flutter/foundation.dart';
import 'dart:developer' as developer;

import '../core/network/api_exceptions.dart';
import '../models/available_rider.dart';
import '../models/seller_order.dart';
import '../services/flask_api_service.dart';

/// Provider for managing seller order state.
///
/// Handles fetching orders, order details, updating order status,
/// searching, filtering, and rider assignment.
class OrdersProvider extends ChangeNotifier {
  final FlaskApiService _apiService;

  OrdersProvider(this._apiService);

  bool _isLoading = false;
  String? _error;
  List<SellerOrder> _orders = const [];
  SellerOrder? _selectedOrder;
  String? _statusFilter;
  String _searchQuery = '';

  // Rider state
  List<AvailableRider> _availableRiders = const [];
  bool _isLoadingRiders = false;

  bool get isLoading => _isLoading;
  String? get error => _error;
  List<SellerOrder> get orders => _orders;
  SellerOrder? get selectedOrder => _selectedOrder;
  String? get statusFilter => _statusFilter;
  String get searchQuery => _searchQuery;
  List<AvailableRider> get availableRiders => _availableRiders;
  bool get isLoadingRiders => _isLoadingRiders;

  /// Returns filtered orders based on the current status filter and search query.
  List<SellerOrder> get filteredOrders {
    var result = List<SellerOrder>.from(_orders);

    // Apply status filter
    if (_statusFilter != null && _statusFilter!.isNotEmpty) {
      result = result.where((order) => order.status == _statusFilter).toList();
    }

    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      result = result.where((order) {
        return order.orderNumber.toLowerCase().contains(q) ||
            order.customerName.toLowerCase().contains(q);
      }).toList();
    }

    return result;
  }

  /// Returns count of orders for each status (for filter chip badges).
  Map<String, int> get statusCounts {
    final counts = <String, int>{'all': _orders.length};
    for (final order in _orders) {
      final s = order.status;
      counts[s] = (counts[s] ?? 0) + 1;
    }
    return counts;
  }

  /// Sets the search query for filtering orders.
  void setSearchQuery(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  /// Fetches paginated list of seller orders from the API.
  Future<void> fetchOrders({int page = 1, int pageSize = 20}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _orders = await _apiService.fetchSellerOrders(
        page: page,
        pageSize: pageSize,
      );
      developer.log('Loaded ${_orders.length} seller orders.');
    } on ApiException catch (e) {
      _error = e.statusCode == 401
          ? 'Session expired. Please log in again.'
          : 'Failed to load orders: ${e.message}';
      developer.log('OrdersProvider.fetchOrders ApiException: ${e.statusCode} ${e.message}');
    } catch (e) {
      _error = 'Failed to load orders: $e';
      developer.log('Error in OrdersProvider.fetchOrders: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetches detailed information for a specific order.
  Future<void> fetchOrderDetails(String id) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _selectedOrder = await _apiService.fetchOrderDetails(id);
      developer.log('Loaded order details for order ID: $id');
    } catch (e) {
      _error = 'Failed to load order details: $e';
      developer.log('Error in OrdersProvider.fetchOrderDetails: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Updates the status of an order with optional notes.
  Future<void> updateOrderStatus(String id, String status, {String? notes}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final updatedOrder = await _apiService.updateOrderStatus(id, status, notes: notes);
      
      // Update the order in the local list
      _orders = _orders.map((order) {
        return order.id.toString() == id ? updatedOrder : order;
      }).toList();
      
      // Update selected order if it's the one being updated
      if (_selectedOrder?.id.toString() == id) {
        _selectedOrder = updatedOrder;
      }
      
      developer.log('Updated order status for order ID: $id to $status');
    } catch (e) {
      _error = 'Failed to update order status: $e';
      developer.log('Error in OrdersProvider.updateOrderStatus: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetches list of available riders for assignment.
  Future<void> fetchAvailableRiders() async {
    _isLoadingRiders = true;
    notifyListeners();

    try {
      _availableRiders = await _apiService.fetchAvailableRiders();
      developer.log('Loaded ${_availableRiders.length} available riders.');
    } catch (e) {
      developer.log('Error fetching riders: $e');
      _availableRiders = const [];
    } finally {
      _isLoadingRiders = false;
      notifyListeners();
    }
  }

  /// Assigns a rider to an order.
  Future<void> assignRider(String orderId, int riderId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final result = await _apiService.assignRiderToOrder(orderId, riderId);
      
      // Update local order with rider info
      final riderData = result['rider'] as Map<String, dynamic>?;
      final riderName = riderData?['ridername']?.toString();

      _orders = _orders.map((order) {
        if (order.id.toString() == orderId) {
          return order.copyWith(
            riderId: riderId,
            riderName: riderName,
          );
        }
        return order;
      }).toList();

      // Update selected order if applicable
      if (_selectedOrder?.id.toString() == orderId) {
        _selectedOrder = _selectedOrder!.copyWith(
          riderId: riderId,
          riderName: riderName,
        );
      }

      developer.log('Assigned rider $riderId to order $orderId');
    } catch (e) {
      _error = 'Failed to assign rider: $e';
      developer.log('Error in OrdersProvider.assignRider: $e');
      rethrow;
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
}
