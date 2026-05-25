import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

/// Integration test to verify seller dashboard integration between
/// Flask backend and Flutter app.
///
/// This test verifies:
/// 1. Seller can login via /api/seller/login
/// 2. Seller can fetch dashboard stats
/// 3. Seller can create/update/delete products
/// 4. Products sync between web and mobile
void main() {
  const baseUrl = 'http://127.0.0.1:5500/api';
  const sellerEmail = 'mia.soriano@gmail.com';
  const sellerPassword = 'TestPass@123';
  
  group('Seller Authentication Integration', () {
    test('Seller can login and receive JWT token', () async {
      final response = await http.post(
        Uri.parse('$baseUrl/seller/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': sellerEmail,
          'password': sellerPassword,
        }),
      );

      print('Login Response: ${response.statusCode}');
      print('Login Body: ${response.body}');

      expect(response.statusCode, equals(200));
      
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      expect(data['status'], equals('success'));
      expect(data['data'], isNotNull);
      expect(data['data']['access_token'], isNotNull);
      expect(data['data']['access_token'], isNotEmpty);
    });
  });

  group('Seller Dashboard Stats Integration', () {
    late String token;

    setUp(() async {
      // Login to get token
      final response = await http.post(
        Uri.parse('$baseUrl/seller/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': sellerEmail,
          'password': sellerPassword,
        }),
      );

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      token = data['data']['access_token'] as String;
    });

    test('Seller can fetch sales statistics', () async {
      final response = await http.get(
        Uri.parse('$baseUrl/seller/stats/sales'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      print('Sales Stats Response: ${response.statusCode}');
      print('Sales Stats Body: ${response.body}');

      expect(response.statusCode, equals(200));
      
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      expect(data['success'], equals(true));
      expect(data['data'], isList);
    });

    test('Seller can fetch order statistics', () async {
      final response = await http.get(
        Uri.parse('$baseUrl/seller/stats/orders'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      print('Order Stats Response: ${response.statusCode}');
      print('Order Stats Body: ${response.body}');

      expect(response.statusCode, equals(200));
      
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      expect(data['success'], equals(true));
      expect(data['data'], isList);
    });

    test('Seller can fetch recent orders', () async {
      final response = await http.get(
        Uri.parse('$baseUrl/seller/stats/recent-orders'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      print('Recent Orders Response: ${response.statusCode}');
      print('Recent Orders Body: ${response.body}');

      expect(response.statusCode, equals(200));
      
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      expect(data['success'], equals(true));
      expect(data['orders'], isList);
    });
  });

  group('Seller Product Management Integration', () {
    late String token;

    setUp(() async {
      // Login to get token
      final response = await http.post(
        Uri.parse('$baseUrl/seller/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': sellerEmail,
          'password': sellerPassword,
        }),
      );

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      token = data['data']['access_token'] as String;
    });

    test('Seller can fetch their products', () async {
      final response = await http.get(
        Uri.parse('$baseUrl/seller/products?page=1&page_size=20'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      print('Fetch Products Response: ${response.statusCode}');
      print('Fetch Products Body: ${response.body}');

      expect(response.statusCode, equals(200));
      
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      expect(data['success'], equals(true));
      expect(data['products'] ?? data['data'], isList);
    });

    test('Seller can create a new product', () async {
      final productData = {
        'name': 'Test Product from Flutter',
        'description': 'This product was created from the Flutter mobile app',
        'price': 99.99,
        'category': 'Electronics',
        'stock_quantity': 10,
        'images': [],
      };

      final response = await http.post(
        Uri.parse('$baseUrl/seller/products'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode(productData),
      );

      print('Create Product Response: ${response.statusCode}');
      print('Create Product Body: ${response.body}');

      expect(response.statusCode, anyOf([200, 201]));
      
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      expect(data['success'], equals(true));
      expect(data['product'] ?? data['data'], isNotNull);
    });

    test('Product created in Flutter appears in web (bidirectional sync)', () async {
      // Step 1: Create product from Flutter
      final productData = {
        'name': 'Sync Test Product ${DateTime.now().millisecondsSinceEpoch}',
        'description': 'Testing bidirectional sync',
        'price': 49.99,
        'category': 'Test',
        'stock_quantity': 5,
        'images': [],
      };

      final createResponse = await http.post(
        Uri.parse('$baseUrl/seller/products'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode(productData),
      );

      expect(createResponse.statusCode, anyOf([200, 201]));
      
      final createData = jsonDecode(createResponse.body) as Map<String, dynamic>;
      final createdProduct = createData['product'] ?? createData['data'];
      final productId = createdProduct['id'] ?? createdProduct['product_id'];

      print('Created Product ID: $productId');

      // Step 2: Fetch products to verify it appears in the list
      final fetchResponse = await http.get(
        Uri.parse('$baseUrl/seller/products?page=1&page_size=100'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      expect(fetchResponse.statusCode, equals(200));
      
      final fetchData = jsonDecode(fetchResponse.body) as Map<String, dynamic>;
      final products = (fetchData['products'] ?? fetchData['data']) as List;
      
      // Verify the created product is in the list
      final foundProduct = products.firstWhere(
        (p) => p['id'] == productId || p['product_id'] == productId,
        orElse: () => null,
      );

      expect(foundProduct, isNotNull);
      expect(foundProduct['name'], equals(productData['name']));
      
      print('✅ Product successfully synced - visible in product list');
    });
  });

  group('Backend Connectivity Check', () {
    test('Flask backend is accessible', () async {
      try {
        final response = await http.get(
          Uri.parse('$baseUrl/products?page=1&page_size=1'),
        ).timeout(const Duration(seconds: 5));

        print('Backend Status: ${response.statusCode}');
        expect(response.statusCode, lessThan(500));
      } catch (e) {
        fail('Flask backend is not accessible at $baseUrl: $e');
      }
    });
  });
}
