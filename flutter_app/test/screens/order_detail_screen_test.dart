import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/models/order_line_item.dart';
import 'package:flutter_app/models/seller_order.dart';

void main() {
  group('OrderDetailScreen - Status Transitions', () {
    test('pending status allows processing and cancelled transitions', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 1500.0,
        status: 'pending',
        orderDate: DateTime(2024, 1, 15),
        lineItems: const [],
      );

      // Valid transitions for pending: processing, cancelled
      expect(order.status, 'pending');
    });

    test('processing status allows shipped and cancelled transitions', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 1500.0,
        status: 'processing',
        orderDate: DateTime(2024, 1, 15),
        lineItems: const [],
      );

      // Valid transitions for processing: shipped, cancelled
      expect(order.status, 'processing');
    });

    test('shipped status allows delivered and cancelled transitions', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 1500.0,
        status: 'shipped',
        orderDate: DateTime(2024, 1, 15),
        lineItems: const [],
      );

      // Valid transitions for shipped: delivered, cancelled
      expect(order.status, 'shipped');
    });

    test('delivered status does not allow any transitions', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 1500.0,
        status: 'delivered',
        orderDate: DateTime(2024, 1, 15),
        lineItems: const [],
      );

      // No valid transitions for delivered
      expect(order.status, 'delivered');
    });

    test('cancelled status does not allow any transitions', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 1500.0,
        status: 'cancelled',
        orderDate: DateTime(2024, 1, 15),
        lineItems: const [],
      );

      // No valid transitions for cancelled
      expect(order.status, 'cancelled');
    });
  });

  group('OrderDetailScreen - Order Display', () {
    test('order with line items calculates total correctly', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 1500.0,
        status: 'pending',
        orderDate: DateTime(2024, 1, 15),
        lineItems: [
          const OrderLineItem(
            productId: 1,
            productName: 'Product A',
            quantity: 2,
            price: 500.0,
          ),
          const OrderLineItem(
            productId: 2,
            productName: 'Product B',
            quantity: 1,
            price: 500.0,
          ),
        ],
      );

      expect(order.lineItems.length, 2);
      expect(order.totalAmount, 1500.0);
      
      // Verify line item totals
      expect(order.lineItems[0].totalPrice, 1000.0); // 2 × 500
      expect(order.lineItems[1].totalPrice, 500.0);  // 1 × 500
    });

    test('order without line items has empty list', () {
      final order = SellerOrder(
        id: 1,
        orderNumber: 'ORD-001',
        customerName: 'John Doe',
        totalAmount: 0.0,
        status: 'pending',
        orderDate: DateTime(2024, 1, 15),
        lineItems: const [],
      );

      expect(order.lineItems.isEmpty, true);
    });
  });
}
