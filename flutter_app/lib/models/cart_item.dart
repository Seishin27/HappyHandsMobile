import 'product.dart';

class CartItem {
  final int id;
  final int quantity;
  final double unitPrice;
  final double totalPrice;
  final Product product;
  final String? size;
  final String? color;
  final DateTime addedAt;

  const CartItem({
    required this.id,
    required this.quantity,
    required this.unitPrice,
    required this.totalPrice,
    required this.product,
    this.size,
    this.color,
    required this.addedAt,
  });

  factory CartItem.fromJson(Map<String, dynamic> json) {
    return CartItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      quantity: (json['quantity'] as num?)?.toInt() ?? 1,
      unitPrice: (json['unit_price'] as num?)?.toDouble() ?? 0.0,
      totalPrice: (json['total_price'] as num?)?.toDouble() ?? 0.0,
      product: Product.fromJson(json['product'] ?? json['product_data'] ?? {}),
      size: json['size']?.toString(),
      color: json['color']?.toString(),
      addedAt: json['added_at'] != null && json['added_at'].toString().isNotEmpty
          ? DateTime.tryParse(json['added_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'quantity': quantity,
      'unit_price': unitPrice,
      'total_price': totalPrice,
      'product': product.toJson(),
      'size': size,
      'color': color,
      'added_at': addedAt.toIso8601String(),
    };
  }

  CartItem copyWith({
    int? id,
    int? quantity,
    double? unitPrice,
    double? totalPrice,
    Product? product,
    String? size,
    String? color,
    DateTime? addedAt,
  }) {
    return CartItem(
      id: id ?? this.id,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      totalPrice: totalPrice ?? this.totalPrice,
      product: product ?? this.product,
      size: size ?? this.size,
      color: color ?? this.color,
      addedAt: addedAt ?? this.addedAt,
    );
  }

  double get subtotal => product.price * quantity;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is CartItem && 
           other.product.id == product.id &&
           other.size == size &&
           other.color == color;
  }

  @override
  int get hashCode => Object.hash(product.id, size, color);

  @override
  String toString() {
    return 'CartItem{product: ${product.name}, quantity: $quantity, size: $size, color: $color}';
  }
}

