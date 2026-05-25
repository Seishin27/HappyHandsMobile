class OrderLineItem {
  final int productId;
  final String productName;
  final int quantity;
  final double price;

  const OrderLineItem({
    required this.productId,
    required this.productName,
    required this.quantity,
    required this.price,
  });

  factory OrderLineItem.fromJson(Map<String, dynamic> json) {
    return OrderLineItem(
      productId: _parseInt(json['product_id'] ?? json['productId'] ?? json['id']) ?? 0,
      productName: (json['product_name'] ?? json['productName'] ?? json['name'] ?? '').toString(),
      quantity: _parseInt(json['quantity'] ?? json['qty'] ?? json['amount']) ?? 0,
      price: _parseDouble(json['price'] ?? json['unit_price'] ?? json['unitPrice']) ?? 0.0,
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

  Map<String, dynamic> toJson() {
    return {
      'product_id': productId,
      'product_name': productName,
      'quantity': quantity,
      'price': price,
    };
  }

  OrderLineItem copyWith({
    int? productId,
    String? productName,
    int? quantity,
    double? price,
  }) {
    return OrderLineItem(
      productId: productId ?? this.productId,
      productName: productName ?? this.productName,
      quantity: quantity ?? this.quantity,
      price: price ?? this.price,
    );
  }

  double get totalPrice => price * quantity;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is OrderLineItem && other.productId == productId;
  }

  @override
  int get hashCode => productId.hashCode;

  @override
  String toString() {
    return 'OrderLineItem{productId: $productId, productName: $productName, quantity: $quantity, price: ₱$price, total: ₱${totalPrice.toStringAsFixed(2)}}';
  }
}
