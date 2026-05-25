import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/models/seller_product.dart';
import 'package:flutter_app/models/seller_order.dart';
import 'package:flutter_app/models/order_line_item.dart';

void main() {
  group('SellerProduct', () {
    test('fromJson creates valid SellerProduct', () {
      final json = {
        'id': 1,
        'name': 'Test Product',
        'description': 'A test product',
        'price': 99.99,
        'category': 'Electronics',
        'stock_quantity': 10,
        'images': ['image1.jpg', 'image2.jpg'],
      };

      final product = SellerProduct.fromJson(json);

      expect(product.id, 1);
      expect(product.name, 'Test Product');
      expect(product.description, 'A test product');
      expect(product.price, 99.99);
      expect(product.category, 'Electronics');
      expect(product.stockQuantity, 10);
      expect(product.images, ['image1.jpg', 'image2.jpg']);
    });

    test('toJson creates valid JSON', () {
      const product = SellerProduct(
        id: 1,
        name: 'Test Product',
        description: 'A test product',
        price: 99.99,
        category: 'Electronics',
        stockQuantity: 10,
        images: ['image1.jpg', 'image2.jpg'],
      );

      final json = product.toJson();

      expect(json['id'], 1);
      expect(json['name'], 'Test Product');
      expect(json['description'], 'A test product');
      expect(json['price'], 99.99);
      expect(json['category'], 'Electronics');
      expect(json['stock_quantity'], 10);
      expect(json['images'], ['image1.jpg', 'image2.jpg']);
    });

    test('fromJson handles alternative field names', () {
      final json = {
        'product_id': 2,
        'product_name': 'Alt Product',
        'desc': 'Alternative description',
        'product_price': 49.99,
        'product_category': 'Books',
        'stock': 5,
        'image_urls': 'image1.jpg,image2.jpg',
      };

      final product = SellerProduct.fromJson(json);

      expect(product.id, 2);
      expect(product.name, 'Alt Product');
      expect(product.description, 'Alternative description');
      expect(product.price, 49.99);
      expect(product.category, 'Books');
      expect(product.stockQuantity, 5);
      expect(product.images, ['image1.jpg', 'image2.jpg']);
    });

    test('copyWith creates modified copy', () {
      const product = SellerProduct(
        id: 1,
        name: 'Test Product',
        description: 'A test product',
        price: 99.99,
        category: 'Electronics',
        stockQuantity: 10,
      );

      final modified = product.copyWith(price: 79.99, stockQuantity: 5);

      expect(modified.id, 1);
      expect(modified.name, 'Test Product');
      expect(modified.price, 79.99);
      expect(modified.stockQuantity, 5);
    });
  });

  group('OrderLineItem', () {
    test('fromJson creates valid OrderLineItem', () {
      final json = {
        'product_id': 1,
        'product_name': 'Test Product',
        'quantity': 2,
        'price': 50.0,
      };

      final item = OrderLineItem.fromJson(json);

      expect(item.productId, 1);
      expect(item.productName, 'Test Product');
      expect(item.quantity, 2);
      expect(item.price, 50.0);
    });

    test('toJson creates valid JSON', () {
      const item = OrderLineItem(
        productId: 1,
        productName: 'Test Product',
        quantity: 2,
        price: 50.0,
      );

      final json = item.toJson();

      expect(json['product_id'], 1);
      expect(json['product_name'], 'Test Product');
      expect(json['quantity'], 2);
      expect(json['price'], 50.0);
    });

    test('totalPrice calculates correctly', () {
      const item = OrderLineItem(
        productId: 1,
        productName: 'Test Product',
        quantity: 3,
        price: 25.0,
      );

      expect(item.totalPrice, 75.0);
    });

    test('fromJson handles alternative field names', () {
      final json = {
        'productId': 2,
        'name': 'Alt Product',
        'qty': 5,
        'unit_price': 10.0,
      };

      final item = OrderLineItem.fromJson(json);

      expect(item.productId, 2);
      expect(item.productName, 'Alt Product');
      expect(item.quantity, 5);
      expect(item.price, 10.0);
    });
  });

  group('SellerOrder', () {
    test('fromJson creates valid SellerOrder', () {
      final json = {
        'id': 1,
        'order_number': 'ORD-001',
        'customer_name': 'John Doe',
        'total_amount': 150.0,
        'status': 'pending',
        'order_date': '2024-01-15T10:30:00Z',
        'line_items': [
          {
            'product_id': 1,
            'product_name': 'Product 1',
            'quantity': 2,
            'price': 50.0,
          },
          {
            'product_id': 2,
            'product_name': 'Product 2',
            'quantity': 1,
            'price': 50.0,
          },
        ],
      };

      final order = SellerOrder.fromJson(json);

      expect(order.id, 1);
      expect(order.orderNumber, 'ORD-001');
      expect(order.customerName, 'John Doe');
      expect(order.totalAmount, 150.0);
      expect(order.status, 'pending');
      expect(order.orderDate, DateTime.parse('2024-01-15T10:30:00Z'));
      expect(order.lineItems.length, 2);
      expect(order.lineItems[0].productName, 'Product 1');
      expect(order.lineItems[1].productName, 'Product 2');
    });

    test('toJson creates valid JSON', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 150.0,
        status: 'pending',
        orderDate: DateTime.parse('2024-01-15T10:30:00Z'),
        lineItems: const [
          OrderLineItem(
            productId: 1,
            productName: 'Product 1',
            quantity: 2,
            price: 50.0,
          ),
        ],
      );

      final json = order.toJson();

      expect(json['id'], 1);
      expect(json['order_number'], 'ORD-001');
      expect(json['customer_name'], 'John Doe');
      expect(json['total_amount'], 150.0);
      expect(json['status'], 'pending');
      expect(json['order_date'], '2024-01-15T10:30:00.000Z');
      expect(json['line_items'], isA<List>());
      expect((json['line_items'] as List).length, 1);
    });

    test('fromJson handles alternative field names', () {
      final json = {
        'order_id': 2,
        'orderNumber': 'ORD-002',
        'customer': 'Jane Smith',
        'total': 200.0,
        'order_status': 'shipped',
        'created_at': '2024-01-16T14:00:00Z',
      };

      final order = SellerOrder.fromJson(json);

      expect(order.id, 2);
      expect(order.orderNumber, 'ORD-002');
      expect(order.customerName, 'Jane Smith');
      expect(order.totalAmount, 200.0);
      expect(order.status, 'shipped');
      expect(order.orderDate, DateTime.parse('2024-01-16T14:00:00Z'));
    });

    test('fromJson handles missing line items', () {
      final json = {
        'id': 3,
        'order_number': 'ORD-003',
        'customer_name': 'Bob Wilson',
        'total_amount': 100.0,
        'status': 'delivered',
        'order_date': '2024-01-17T09:00:00Z',
      };

      final order = SellerOrder.fromJson(json);

      expect(order.id, 3);
      expect(order.lineItems, isEmpty);
    });

    test('copyWith creates modified copy', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 150.0,
        status: 'pending',
        orderDate: DateTime.parse('2024-01-15T10:30:00Z'),
      );

      final modified = order.copyWith(status: 'shipped');

      expect(modified.id, 1);
      expect(modified.orderNumber, 'ORD-001');
      expect(modified.status, 'shipped');
      expect(modified.totalAmount, 150.0);
    });
  });
}
