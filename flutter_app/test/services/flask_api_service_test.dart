import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:flutter_app/core/network/api_client.dart';
import 'package:flutter_app/services/flask_api_service.dart';
import 'package:flutter_app/models/seller_stats.dart';
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
  group('FlaskApiService - Dashboard Statistics', () {
    late MockHttpClient mockHttpClient;
    late ApiClient apiClient;
    late FlaskApiService flaskApiService;

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
    });

    group('fetchSalesStats', () {
      test('successfully fetches sales statistics', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'data': [
            {'date': '2024-01-01', 'total_sales': 1500.50},
            {'date': '2024-01-02', 'total_sales': 2300.75},
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchSalesStats();

        // Assert
        expect(result, isA<List<SellerSalesPoint>>());
        expect(result.length, 2);
        expect(result[0].date, '2024-01-01');
        expect(result[0].totalSales, 1500.50);
        expect(result[1].date, '2024-01-02');
        expect(result[1].totalSales, 2300.75);
      });

      test('throws exception when success is false', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Unauthorized access',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.fetchSalesStats(),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Unauthorized access'),
          )),
        );
      });

      test('handles empty data array', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'data': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchSalesStats();

        // Assert
        expect(result, isEmpty);
      });

      test('throws exception on HTTP error', () async {
        // Arrange
        final responseBody = jsonEncode({
          'message': 'Internal server error',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 500));

        // Act & Assert
        expect(
          () => flaskApiService.fetchSalesStats(),
          throwsA(isA<Exception>()),
        );
      });
    });

    group('fetchOrderStats', () {
      test('successfully fetches order statistics', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'data': [
            {'date': '2024-01-01', 'order_count': 15},
            {'date': '2024-01-02', 'order_count': 23},
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchOrderStats();

        // Assert
        expect(result, isA<List<SellerOrdersPoint>>());
        expect(result.length, 2);
        expect(result[0].date, '2024-01-01');
        expect(result[0].orderCount, 15);
        expect(result[1].date, '2024-01-02');
        expect(result[1].orderCount, 23);
      });

      test('throws exception when success is false', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Failed to fetch order statistics',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.fetchOrderStats(),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Failed to fetch order statistics'),
          )),
        );
      });

      test('handles empty data array', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'data': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchOrderStats();

        // Assert
        expect(result, isEmpty);
      });

      test('throws exception on HTTP error', () async {
        // Arrange
        final responseBody = jsonEncode({
          'message': 'Internal server error',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 500));

        // Act & Assert
        expect(
          () => flaskApiService.fetchOrderStats(),
          throwsA(isA<Exception>()),
        );
      });
    });

    group('fetchRecentOrders', () {
      test('successfully fetches recent orders', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'order_id': 101,
              'order_number': 'ORD-001',
              'order_status': 'pending',
              'total': 150.50,
              'customer_name': 'John Doe',
              'product': 'Widget A',
              'quantity': 2,
              'order_date': '2024-01-01',
            },
            {
              'order_id': 102,
              'order_number': 'ORD-002',
              'order_status': 'completed',
              'total': 250.75,
              'customer_name': 'Jane Smith',
              'product': 'Widget B',
              'quantity': 1,
              'order_date': '2024-01-02',
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchRecentOrders();

        // Assert
        expect(result, isA<List<SellerRecentOrder>>());
        expect(result.length, 2);
        expect(result[0].sellerOrderId, 101);
        expect(result[0].orderNumber, 'ORD-001');
        expect(result[0].status, 'pending');
        expect(result[0].totalAmount, 150.50);
        expect(result[0].customerName, 'John Doe');
        expect(result[0].product, 'Widget A');
        expect(result[0].quantity, 2);
        expect(result[1].sellerOrderId, 102);
        expect(result[1].orderNumber, 'ORD-002');
      });

      test('throws exception when success is false', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Failed to fetch recent orders',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.fetchRecentOrders(),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Failed to fetch recent orders'),
          )),
        );
      });

      test('handles empty orders array', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchRecentOrders();

        // Assert
        expect(result, isEmpty);
      });

      test('throws exception on HTTP error', () async {
        // Arrange
        final responseBody = jsonEncode({
          'message': 'Internal server error',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 500));

        // Act & Assert
        expect(
          () => flaskApiService.fetchRecentOrders(),
          throwsA(isA<Exception>()),
        );
      });

      test('handles missing optional fields', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'order_id': 103,
              'order_number': 'ORD-003',
              'order_status': 'processing',
              'total': 99.99,
              'customer_name': 'Bob Johnson',
              'product': 'Widget C',
              'quantity': 3,
              // order_date is optional
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchRecentOrders();

        // Assert
        expect(result.length, 1);
        expect(result[0].orderDate, isNull);
      });
    });

    group('fetchSellerOrders', () {
      test('successfully fetches paginated seller orders', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [
            {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 150.50,
              'status': 'pending',
              'order_date': '2024-01-01T10:00:00Z',
              'line_items': [],
            },
            {
              'id': 2,
              'order_number': 'ORD-002',
              'customer_name': 'Jane Smith',
              'total_amount': 250.75,
              'status': 'processing',
              'order_date': '2024-01-02T11:00:00Z',
              'line_items': [],
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchSellerOrders(page: 1, pageSize: 20);

        // Assert
        expect(result.length, 2);
        expect(result[0].id, 1);
        expect(result[0].orderNumber, 'ORD-001');
        expect(result[0].customerName, 'John Doe');
        expect(result[0].totalAmount, 150.50);
        expect(result[0].status, 'pending');
        expect(result[1].id, 2);
        expect(result[1].orderNumber, 'ORD-002');
      });

      test('throws exception when success is false', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Failed to fetch seller orders',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.fetchSellerOrders(),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Failed to fetch seller orders'),
          )),
        );
      });

      test('handles empty orders array', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'orders': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchSellerOrders();

        // Assert
        expect(result, isEmpty);
      });
    });

    group('fetchOrderDetails', () {
      test('successfully fetches order details with line items', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 150.50,
            'status': 'pending',
            'order_date': '2024-01-01T10:00:00Z',
            'line_items': [
              {
                'product_id': 101,
                'product_name': 'Widget A',
                'quantity': 2,
                'price': 75.25,
              },
            ],
          },
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchOrderDetails('1');

        // Assert
        expect(result.id, 1);
        expect(result.orderNumber, 'ORD-001');
        expect(result.customerName, 'John Doe');
        expect(result.totalAmount, 150.50);
        expect(result.status, 'pending');
        expect(result.lineItems.length, 1);
        expect(result.lineItems[0].productName, 'Widget A');
        expect(result.lineItems[0].quantity, 2);
      });

      test('throws exception when success is false', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Order not found',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.fetchOrderDetails('999'),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Order not found'),
          )),
        );
      });

      test('handles order without line items', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 150.50,
            'status': 'pending',
            'order_date': '2024-01-01T10:00:00Z',
          },
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchOrderDetails('1');

        // Assert
        expect(result.lineItems, isEmpty);
      });
    });

    group('updateOrderStatus', () {
      test('successfully updates order status', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'order': {
            'id': 1,
            'order_number': 'ORD-001',
            'customer_name': 'John Doe',
            'total_amount': 150.50,
            'status': 'processing',
            'order_date': '2024-01-01T10:00:00Z',
            'line_items': [],
          },
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.updateOrderStatus('1', 'processing');

        // Assert
        expect(result.id, 1);
        expect(result.status, 'processing');
      });

      test('throws exception for invalid status transition', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Invalid status transition',
          'validation_errors': {'status': 'Cannot transition from delivered to pending'},
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.updateOrderStatus('1', 'pending'),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Validation error'),
          )),
        );
      });

      test('throws exception when seller does not own order', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'You do not have permission to update this order',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.updateOrderStatus('999', 'processing'),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('You do not have permission to update this order'),
          )),
        );
      });

      test('handles various valid status values', () async {
        // Arrange
        final statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'];
        
        for (final status in statuses) {
          final responseBody = jsonEncode({
            'success': true,
            'order': {
              'id': 1,
              'order_number': 'ORD-001',
              'customer_name': 'John Doe',
              'total_amount': 150.50,
              'status': status,
              'order_date': '2024-01-01T10:00:00Z',
              'line_items': [],
            },
          });

          mockHttpClient.setResponse(http.Response(responseBody, 200));

          // Act
          final result = await flaskApiService.updateOrderStatus('1', status);

          // Assert
          expect(result.status, status);
        }
      });
    });
  });
}
