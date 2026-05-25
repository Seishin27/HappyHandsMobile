import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:flutter_app/core/network/api_client.dart';
import 'package:flutter_app/services/flask_api_service.dart';
import 'package:flutter_app/providers/cart_provider.dart';
import 'package:flutter_app/models/cart_item.dart';
import 'package:flutter_app/models/product.dart';

/// Mock that returns a different response per HTTP method.
class MockHttpClient extends http.BaseClient {
  final Map<String, http.Response> _responses = {};

  void setResponse(String method, http.Response response) {
    _responses[method.toUpperCase()] = response;
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final r = _responses[request.method.toUpperCase()];
    if (r == null) {
      throw Exception('No response set for ${request.method}');
    }
    return http.StreamedResponse(
      Stream.value(r.bodyBytes),
      r.statusCode,
      headers: r.headers,
    );
  }
}

void main() {
  group('CartProvider.removeFromCart', () {
    late MockHttpClient mockHttp;
    late FlaskApiService apiService;
    late CartProvider provider;

    setUp(() {
      mockHttp = MockHttpClient();
      final apiClient = ApiClient(
        client: mockHttp,
        tokenProvider: () async => 'test-token',
      );
      apiService = FlaskApiService(
        apiClient,
        tokenProvider: () async => 'test-token',
      );
      provider = CartProvider()..bindApi(apiService);
    });

    CartItem _seedItem({int id = 42}) {
      final item = CartItem(
        id: id,
        quantity: 1,
        unitPrice: 100,
        totalPrice: 100,
        product: const Product(
          id: 13,
          name: 'Avent Bottle',
          price: 100,
          description: '',
          imageUrl: '',
          category: 'Feeding',
          stock: 5,
        ),
        addedAt: DateTime(2026, 1, 1),
      );
      // Bootstrap cart with one item via the public addToCart path.
      // Mock the POST /cart response so addToCart populates _cartItems.
      mockHttp.setResponse(
        'POST',
        http.Response(
          jsonEncode({
            'status': 'success',
            'message': 'Added',
            'data': {
              'id': id,
              'quantity': 1,
              'unit_price': 100,
              'total_price': 100,
              'product': {
                'id': 13,
                'name': 'Avent Bottle',
                'price': 100,
                'description': '',
                'image_url': '',
                'category': 'Feeding',
                'stock': 5,
              },
              'added_at': '2026-01-01T00:00:00Z',
            },
          }),
          201,
        ),
      );
      return item;
    }

    test(
      'returns false and KEEPS item in local cart when API DELETE fails',
      () async {
        // Arrange — seed one cart item via addToCart.
        final seeded = _seedItem(id: 42);
        await provider.addToCart(
          product: seeded.product,
          quantity: 1,
          authToken: 'test-token',
        );
        expect(provider.cartItems.length, 1,
            reason: 'precondition: cart should contain the seeded item');

        // The DELETE will fail server-side.
        mockHttp.setResponse(
          'DELETE',
          http.Response(
            jsonEncode({
              'status': 'error',
              'message': 'Server error removing from cart',
              'data': null,
            }),
            500,
          ),
        );

        // Act
        final result = await provider.removeFromCart(
          cartItem: provider.cartItems.first,
          authToken: 'test-token',
        );

        // Assert — bug: currently returns true and removes the item locally,
        // so on next loadCart the deleted item reappears. Correct behavior:
        // surface the failure and keep local state in sync with the server.
        expect(result, false,
            reason: 'remove should report failure when server delete fails');
        expect(provider.cartItems.length, 1,
            reason: 'item must remain in local cart so state matches server');
        expect(provider.error, isNotNull,
            reason: 'error message should be set so UI can display it');
      },
    );

    test('returns true and removes item locally when API DELETE succeeds',
        () async {
      final seeded = _seedItem(id: 42);
      await provider.addToCart(
        product: seeded.product,
        quantity: 1,
        authToken: 'test-token',
      );
      expect(provider.cartItems.length, 1);

      mockHttp.setResponse(
        'DELETE',
        http.Response(
          jsonEncode({
            'status': 'success',
            'message': 'Item removed from cart',
            'data': null,
          }),
          200,
        ),
      );

      final result = await provider.removeFromCart(
        cartItem: provider.cartItems.first,
        authToken: 'test-token',
      );

      expect(result, true);
      expect(provider.cartItems, isEmpty);
    });
  });
}
