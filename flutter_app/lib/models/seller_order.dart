import 'order_line_item.dart';

class SellerOrder {
  final int id;
  final String orderNumber;
  final String customerName;
  final double totalAmount;
  final String status;
  final DateTime orderDate;
  final List<OrderLineItem> lineItems;

  // New fields matching Flask web
  final String? shippingAddress;
  final String? contactNumber;
  final String? paymentMethod;
  final String? riderName;
  final int? riderId;

  const SellerOrder({
    required this.id,
    required this.orderNumber,
    required this.customerName,
    required this.totalAmount,
    required this.status,
    required this.orderDate,
    this.lineItems = const [],
    this.shippingAddress,
    this.contactNumber,
    this.paymentMethod,
    this.riderName,
    this.riderId,
  });

  factory SellerOrder.fromJson(Map<String, dynamic> json) {
    // Parse line items if present
    List<OrderLineItem> items = [];
    final dynamic rawLineItems = json['lineItems'] ?? json['line_items'] ?? json['items'] ?? json['order_items'];
    
    if (rawLineItems is List) {
      items = rawLineItems
          .map((item) {
            if (item is Map<String, dynamic>) {
              return OrderLineItem.fromJson(item);
            }
            return null;
          })
          .where((item) => item != null)
          .cast<OrderLineItem>()
          .toList();
    }

    // Extract customer name from various possible sources
    String customerName = 'Unknown Customer';
    if (json['customerName'] != null && json['customerName'].toString().isNotEmpty) {
      customerName = json['customerName'].toString();
    } else if (json['customer_name'] != null && json['customer_name'].toString().isNotEmpty) {
      customerName = json['customer_name'].toString();
    } else if (json['buyer_name'] != null && json['buyer_name'].toString().isNotEmpty) {
      customerName = json['buyer_name'].toString();
    } else if (json['customer'] != null && json['customer'].toString().isNotEmpty) {
      customerName = json['customer'].toString();
    } else if (json['username'] != null && json['username'].toString().isNotEmpty) {
      customerName = json['username'].toString();
    } else if (json['email'] != null && json['email'].toString().isNotEmpty) {
      customerName = json['email'].toString();
    }

    return SellerOrder(
      id: _parseInt(json['id'] ?? json['sellerOrderID'] ?? json['seller_order_id'] ?? json['order_id']) ?? 0,
      orderNumber: (json['orderNumber'] ?? json['order_number'] ?? json['order_no'] ?? json['tracking_number'] ?? 'N/A').toString(),
      customerName: customerName,
      totalAmount: _parseDouble(json['totalAmount'] ?? json['total_amount'] ?? json['total'] ?? json['amount']) ?? 0.0,
      status: (json['status'] ?? json['order_status'] ?? json['orderStatus'] ?? 'pending').toString(),
      orderDate: _parseDateTime(json['orderDate'] ?? json['order_date'] ?? json['items_received_at'] ?? json['created_at'] ?? json['date']) ?? DateTime.now(),
      lineItems: items,
      // New fields
      shippingAddress: json['shipping_address']?.toString() ?? json['shippingAddress']?.toString(),
      contactNumber: json['contact_number']?.toString() ?? json['contactNumber']?.toString() ?? json['phone']?.toString(),
      paymentMethod: json['payment_method']?.toString() ?? json['paymentMethod']?.toString(),
      riderName: json['rider_name']?.toString() ?? json['riderName']?.toString(),
      riderId: _parseInt(json['rider_id'] ?? json['riderID'] ?? json['riderId']),
    );
  }

  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    final s = value.toString().trim();
    if (s.isEmpty) return null;
    return int.tryParse(s) ?? double.tryParse(s)?.toInt();
  }

  static double? _parseDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    final s = value.toString().trim();
    if (s.isEmpty) return null;
    return double.tryParse(s);
  }

  static DateTime? _parseDateTime(dynamic value) {
    if (value == null) return null;
    if (value is DateTime) return value;
    final s = value.toString().trim();
    if (s.isEmpty) return null;
    return DateTime.tryParse(s);
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'orderNumber': orderNumber,
      'customerName': customerName,
      'totalAmount': totalAmount,
      'status': status,
      'orderDate': orderDate.toIso8601String(),
      'lineItems': lineItems.map((item) => item.toJson()).toList(),
      'shipping_address': shippingAddress,
      'contact_number': contactNumber,
      'payment_method': paymentMethod,
      'rider_name': riderName,
      'rider_id': riderId,
    };
  }

  SellerOrder copyWith({
    int? id,
    String? orderNumber,
    String? customerName,
    double? totalAmount,
    String? status,
    DateTime? orderDate,
    List<OrderLineItem>? lineItems,
    String? shippingAddress,
    String? contactNumber,
    String? paymentMethod,
    String? riderName,
    int? riderId,
  }) {
    return SellerOrder(
      id: id ?? this.id,
      orderNumber: orderNumber ?? this.orderNumber,
      customerName: customerName ?? this.customerName,
      totalAmount: totalAmount ?? this.totalAmount,
      status: status ?? this.status,
      orderDate: orderDate ?? this.orderDate,
      lineItems: lineItems ?? this.lineItems,
      shippingAddress: shippingAddress ?? this.shippingAddress,
      contactNumber: contactNumber ?? this.contactNumber,
      paymentMethod: paymentMethod ?? this.paymentMethod,
      riderName: riderName ?? this.riderName,
      riderId: riderId ?? this.riderId,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is SellerOrder && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() {
    return 'SellerOrder{id: $id, orderNumber: $orderNumber, customerName: $customerName, totalAmount: ₱$totalAmount, status: $status, orderDate: $orderDate, items: ${lineItems.length}, rider: $riderName}';
  }
}
