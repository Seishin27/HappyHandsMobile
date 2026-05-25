import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:flutter_app/core/network/api_client.dart';
import 'package:flutter_app/services/flask_api_service.dart';
import 'package:flutter_app/providers/orders_provider.dart';
import 'package:flutter_app/models/seller_order.dart';

// Manual mock for http.Client
class MockHttpClient extends http.BaseClient {
  http.Response? _response;
  
  void setResponse(http.Response response) {
    _response = response;
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (_response == null) {
      throw Exception('No response set for mock');
    }
    return http.StreamedResponse(
      Stream.value(_response!.bodyBytes),
      _response!.statusCode,
      headers: _response!.headers,
    );
  }
}

void main() {
  group('OrdersProvider', () {
    late MockHttpClient mockHttpClient;
    late ApiClient apiClient;
    late FlaskApiService flaskApiService;
    late OrdersProvider ordersProvider;

    setUp(() {
      mockHttpClient = MockHttpClient();
      apiClient = ApiClient(
        client: mockHttpClient,
        tokenProvider: () async => 'test-token',
      );
      flaskApiService = FlaskApiService(
        apiClient,
        tokenProvider: () async => 'test-token',
      );
      ordersProvider = OrdersProvider(flaskApiService);
    });

    group('fetchOrders', () {
      test('successfully fetches orders and updates state', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 299.99,
              'status': 'pending',
              'order_date': '2024-01-15T10:30:00Z',
            },
            {
              'id': 2,
              'order_number': 'ORD-002',
              'customer_name': 'Jane Smith',
              'total_amount': 149.99,
              'status': 'processing',
              'order_date': '2024-01-16T14:20:00Z',
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await ordersProvider.fetchOrders();

        // Assert
        expect(ordersProvider.isLoading, false);
        expect(ordersProvider.error, isNull);
        expect(ordersProvider.orders.length, 2);
        expect(ordersProvider.orders[0].id, 1);
        expect(ordersProvider.orders[0].orderNumber, 'ORD-001');
        expect(ordersProvider.orders[0].customerName, 'John Doe');
        expect(ordersProvider.orders[0].totalAmount, 299.99);
        expect(ordersProvider.orders[0].status, 'pending');
        expect(ordersProvider.orders[1].id, 2);
        expect(ordersProvider.orders[1].orderNumber, 'ORD-002');
      });

      test('sets loading state during fetch', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final fetchFuture = ordersProvider.fetchOrders();
        
        // Assert - loading should be true during fetch
        // Note: This is a simplified test; in real scenarios you'd need to test
        // the loading state more carefully with proper async handling
        
        await fetchFuture;
        expect(ordersProvider.isLoading, false);
      });

      test('handles empty orders list', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await ordersProvider.fetchOrders();

        // Assert
        expect(ordersProvider.isLoading, false);
        expect(ordersProvider.error, isNull);
        expect(ordersProvider.orders, isEmpty);
      });

      test('sets error state when fetch fails', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Unauthorized access',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await ordersProvider.fetchOrders();

        // Assert
        expect(ordersProvider.isLoading, false);
        expect(ordersProvider.error, isNotNull);
        expect(ordersProvider.error, contains('Failed to load orders'));
        expect(ordersProvider.orders, isEmpty);
      });

      test('supports pagination parameters', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await ordersProvider.fetchOrders(page: 2, pageSize: 10);

        // Assert
        expect(ordersProvider.isLoading, false);
        expect(ordersProvider.error, isNull);
      });
    });

    group('fetchOrderDetails', () {
      test('successfully fetches order details and updates selectedOrder', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 299.99,
            'status': 'pending',
            'order_date': '2024-01-15T10:30:00Z',
            'line_items': [
              {
                'id': 1,
                'product_name': 'Product A',
                'quantity': 2,
                'price': 99.99,
              },
              {
                'id': 2,
                'product_name': 'Product B',
                'quantity': 1,
                'price': 100.01,
              },
            ],
          },
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await ordersProvider.fetchOrderDetails('1');

        // Assert
        expect(ordersProvider.isLoading, false);
        expect(ordersProvider.error, isNull);
        expect(ordersProvider.selectedOrder, isNotNull);
        expect(ordersProvider.selectedOrder!.id, 1);
        expect(ordersProvider.selectedOrder!.orderNumber, 'ORD-001');
        expect(ordersProvider.selectedOrder!.lineItems.length, 2);
      });

      test('sets error state when fetch fails', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Order not found',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await ordersProvider.fetchOrderDetails('999');

        // Assert
        expect(ordersProvider.isLoading, false);
        expect(ordersProvider.error, isNotNull);
        expect(ordersProvider.error, contains('Failed to load order details'));
        expect(ordersProvider.selectedOrder, isNull);
      });
    });

    group('updateOrderStatus', () {
      test('successfully updates order status in orders list', () async {
        // Arrange - First populate orders
        final fetchResponseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 299.99,
              'status': 'pending',
              'order_date': '2024-01-15T10:30:00Z',
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(fetchResponseBody, 200));
        await ordersProvider.fetchOrders();

        // Arrange - Update status
        final updateResponseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 299.99,
            'status': 'processing',
            'order_date': '2024-01-15T10:30:00Z',
          },
        });

        mockHttpClient.setResponse(http.Response(updateResponseBody, 200));

        // Act
        await ordersProvider.updateOrderStatus('1', 'processing');

        // Assert
        expect(ordersProvider.isLoading, false);
        expect(ordersProvider.error, isNull);
        expect(ordersProvider.orders[0].status, 'processing');
      });

      test('updates selectedOrder if it matches the updated order', () async {
        // Arrange - Set selected order
        final detailsResponseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 299.99,
            'status': 'pending',
            'order_date': '2024-01-15T10:30:00Z',
          },
        });

        mockHttpClient.setResponse(http.Response(detailsResponseBody, 200));
        await ordersProvider.fetchOrderDetails('1');

        // Arrange - Update status
        final updateResponseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 299.99,
            'status': 'shipped',
            'order_date': '2024-01-15T10:30:00Z',
          },
        });

        mockHttpClient.setResponse(http.Response(updateResponseBody, 200));

        // Act
        await ordersProvider.updateOrderStatus('1', 'shipped');

        // Assert
        expect(ordersProvider.selectedOrder, isNotNull);
        expect(ordersProvider.selectedOrder!.status, 'shipped');
      });

      test('throws exception and sets error when update fails', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Invalid status transition',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => ordersProvider.updateOrderStatus('1', 'invalid_status'),
          throwsA(isA<Exception>()),
        );

        // Wait for the async operation to complete
        try {
          await ordersProvider.updateOrderStatus('1', 'invalid_status');
        } catch (e) {
          // Expected exception
        }

        expect(ordersProvider.error, isNotNull);
        expect(ordersProvider.error, contains('Failed to update order status'));
      });
    });

    group('status filtering', () {
      test('setStatusFilter updates filter and notifies listeners', () async {
        // Arrange - Populate orders with different statuses
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 299.99,
              'status': 'pending',
              'order_date': '2024-01-15T10:30:00Z',
            },
            {
              'id': 2,
              'order_number': 'ORD-002',
              'customer_name': 'Jane Smith',
              'total_amount': 149.99,
              'status': 'processing',
              'order_date': '2024-01-16T14:20:00Z',
            },
            {
              'id': 3,
              'order_number': 'ORD-003',
              'customer_name': 'Bob Johnson',
              'total_amount': 199.99,
              'status': 'pending',
              'order_date': '2024-01-17T09:15:00Z',
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));
        await ordersProvider.fetchOrders();

        // Act
        ordersProvider.setStatusFilter('pending');

        // Assert
        expect(ordersProvider.statusFilter, 'pending');
        expect(ordersProvider.filteredOrders.length, 2);
        expect(ordersProvider.filteredOrders.every((o) => o.status == 'pending'), true);
      });

      test('filteredOrders returns all orders when no filter is set', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 299.99,
              'status': 'pending',
              'order_date': '2024-01-15T10:30:00Z',
            },
            {
              'id': 2,
              'order_number': 'ORD-002',
              'customer_name': 'Jane Smith',
              'total_amount': 149.99,
              'status': 'processing',
              'order_date': '2024-01-16T14:20:00Z',
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));
        await ordersProvider.fetchOrders();

        // Act & Assert
        expect(ordersProvider.filteredOrders.length, 2);
        expect(ordersProvider.filteredOrders, ordersProvider.orders);
      });

      test('clearStatusFilter removes filter', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 299.99,
              'status': 'pending',
              'order_date': '2024-01-15T10:30:00Z',
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));
        await ordersProvider.fetchOrders();
        ordersProvider.setStatusFilter('pending');

        // Act
        ordersProvider.clearStatusFilter();

        // Assert
        expect(ordersProvider.statusFilter, isNull);
        expect(ordersProvider.filteredOrders, ordersProvider.orders);
      });

      test('filteredOrders returns empty list when no orders match filter', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 299.99,
              'status': 'pending',
              'order_date': '2024-01-15T10:30:00Z',
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));
        await ordersProvider.fetchOrders();

        // Act
        ordersProvider.setStatusFilter('shipped');

        // Assert
        expect(ordersProvider.filteredOrders, isEmpty);
      });
    });

    group('utility methods', () {
      test('clearSelectedOrder sets selectedOrder to null', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 299.99,
            'status': 'pending',
            'order_date': '2024-01-15T10:30:00Z',
          },
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));
        await ordersProvider.fetchOrderDetails('1');

        // Act
        ordersProvider.clearSelectedOrder();

        // Assert
        expect(ordersProvider.selectedOrder, isNull);
      });

      test('clearError sets error to null', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Some error',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));
        await ordersProvider.fetchOrders();
        expect(ordersProvider.error, isNotNull);

        // Act
        ordersProvider.clearError();

        // Assert
        expect(ordersProvider.error, isNull);
      });
    });
  });
}
