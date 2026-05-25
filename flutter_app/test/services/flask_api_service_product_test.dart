import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:flutter_app/core/network/api_client.dart';
import 'package:flutter_app/services/flask_api_service.dart';
import 'package:flutter_app/models/seller_product.dart';

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
  group('FlaskApiService - Product Management', () {
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

    group('fetchSellerProducts', () {
      test('successfully fetches seller products', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'products': [
            {
              'id': 1,
              'name': 'Product A',
              'description': 'Description A',
              'price': 99.99,
              'category': 'Electronics',
              'stock_quantity': 10,
              'images': ['image1.jpg', 'image2.jpg'],
            },
            {
              'id': 2,
              'name': 'Product B',
              'description': 'Description B',
              'price': 149.99,
              'category': 'Clothing',
              'stock_quantity': 5,
              'images': ['image3.jpg'],
            },
          ],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchSellerProducts();

        // Assert
        expect(result, isA<List<SellerProduct>>());
        expect(result.length, 2);
        expect(result[0].id, 1);
        expect(result[0].name, 'Product A');
        expect(result[0].price, 99.99);
        expect(result[0].category, 'Electronics');
        expect(result[0].stockQuantity, 10);
        expect(result[0].images.length, 2);
        expect(result[1].id, 2);
        expect(result[1].name, 'Product B');
      });

      test('supports pagination parameters', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'products': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await flaskApiService.fetchSellerProducts(page: 2, pageSize: 10);

        // Assert - just verify it doesn't throw
        expect(true, true);
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
          () => flaskApiService.fetchSellerProducts(),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Unauthorized access'),
          )),
        );
      });

      test('handles empty products array', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'products': [],
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        final result = await flaskApiService.fetchSellerProducts();

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
          () => flaskApiService.fetchSellerProducts(),
          throwsA(isA<Exception>()),
        );
      });
    });

    group('deleteProduct', () {
      test('successfully deletes a product', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': true,
          'message': 'Product deleted successfully',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act
        await flaskApiService.deleteProduct('123');

        // Assert - should not throw
        expect(true, true);
      });

      test('throws exception when success is false', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'msg': 'Product not found',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.deleteProduct('123'),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Product not found'),
          )),
        );
      });

      test('throws exception when seller does not own product', () async {
        // Arrange
        final responseBody = jsonEncode({
          'success': false,
          'message': 'You do not have permission to delete this product',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 200));

        // Act & Assert
        expect(
          () => flaskApiService.deleteProduct('123'),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('permission'),
          )),
        );
      });

      test('throws exception on HTTP error', () async {
        // Arrange
        final responseBody = jsonEncode({
          'message': 'Internal server error',
        });

        mockHttpClient.setResponse(http.Response(responseBody, 500));

        // Act & Assert
        expect(
          () => flaskApiService.deleteProduct('123'),
          throwsA(isA<Exception>()),
        );
      });
    });
  });
}
