class RecentOrder {
  final int orderId;
  final String orderNumber;
  final String customerName;
  final double totalAmount;
  final String status;
  final DateTime orderDate;

  const RecentOrder({
    required this.orderId,
    required this.orderNumber,
    required this.customerName,
    required this.totalAmount,
    required this.status,
    required this.orderDate,
  });

  factory RecentOrder.fromJson(Map<String, dynamic> json) {
    return RecentOrder(
      orderId: _parseInt(json['order_id'] ?? json['orderId'] ?? json['id']) ?? 0,
      orderNumber: (json['order_number'] ?? json['orderNumber'] ?? '').toString(),
      customerName: (json['customer_name'] ?? json['customerName'] ?? '').toString(),
      totalAmount: _parseDouble(json['total_amount'] ?? json['totalAmount']) ?? 0.0,
      status: (json['status'] ?? '').toString(),
      orderDate: _parseDateTime(json['order_date'] ?? json['orderDate']) ?? DateTime.now(),
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
      'order_id': orderId,
      'order_number': orderNumber,
      'customer_name': customerName,
      'total_amount': totalAmount,
      'status': status,
      'order_date': orderDate.toIso8601String(),
    };
  }

  RecentOrder copyWith({
    int? orderId,
    String? orderNumber,
    String? customerName,
    double? totalAmount,
    String? status,
    DateTime? orderDate,
  }) {
    return RecentOrder(
      orderId: orderId ?? this.orderId,
      orderNumber: orderNumber ?? this.orderNumber,
      customerName: customerName ?? this.customerName,
      totalAmount: totalAmount ?? this.totalAmount,
      status: status ?? this.status,
      orderDate: orderDate ?? this.orderDate,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is RecentOrder && other.orderId == orderId;
  }

  @override
  int get hashCode => orderId.hashCode;

  @override
  String toString() {
    return 'RecentOrder{orderId: $orderId, orderNumber: $orderNumber, customerName: $customerName, totalAmount: ₱$totalAmount, status: $status, orderDate: $orderDate}';
  }
}
