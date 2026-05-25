class OrderStats {
  final int totalOrders;
  final int pendingOrders;
  final int processingOrders;
  final int completedOrders;

  const OrderStats({
    required this.totalOrders,
    required this.pendingOrders,
    required this.processingOrders,
    required this.completedOrders,
  });

  factory OrderStats.fromJson(Map<String, dynamic> json) {
    return OrderStats(
      totalOrders: _parseInt(json['total_orders'] ?? json['totalOrders']) ?? 0,
      pendingOrders: _parseInt(json['pending_orders'] ?? json['pendingOrders']) ?? 0,
      processingOrders: _parseInt(json['processing_orders'] ?? json['processingOrders']) ?? 0,
      completedOrders: _parseInt(json['completed_orders'] ?? json['completedOrders']) ?? 0,
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

  Map<String, dynamic> toJson() {
    return {
      'total_orders': totalOrders,
      'pending_orders': pendingOrders,
      'processing_orders': processingOrders,
      'completed_orders': completedOrders,
    };
  }

  OrderStats copyWith({
    int? totalOrders,
    int? pendingOrders,
    int? processingOrders,
    int? completedOrders,
  }) {
    return OrderStats(
      totalOrders: totalOrders ?? this.totalOrders,
      pendingOrders: pendingOrders ?? this.pendingOrders,
      processingOrders: processingOrders ?? this.processingOrders,
      completedOrders: completedOrders ?? this.completedOrders,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is OrderStats &&
        other.totalOrders == totalOrders &&
        other.pendingOrders == pendingOrders &&
        other.processingOrders == processingOrders &&
        other.completedOrders == completedOrders;
  }

  @override
  int get hashCode =>
      totalOrders.hashCode ^
      pendingOrders.hashCode ^
      processingOrders.hashCode ^
      completedOrders.hashCode;

  @override
  String toString() {
    return 'OrderStats{totalOrders: $totalOrders, pendingOrders: $pendingOrders, processingOrders: $processingOrders, completedOrders: $completedOrders}';
  }
}
