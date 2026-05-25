class SalesStats {
  final double totalSales;
  final double todaySales;
  final double monthlySales;
  final double yearlyRevenue;

  const SalesStats({
    required this.totalSales,
    required this.todaySales,
    required this.monthlySales,
    required this.yearlyRevenue,
  });

  factory SalesStats.fromJson(Map<String, dynamic> json) {
    return SalesStats(
      totalSales: _parseDouble(json['total_sales'] ?? json['totalSales']) ?? 0.0,
      todaySales: _parseDouble(json['today_sales'] ?? json['todaySales']) ?? 0.0,
      monthlySales: _parseDouble(json['monthly_sales'] ?? json['monthlySales']) ?? 0.0,
      yearlyRevenue: _parseDouble(json['yearly_revenue'] ?? json['yearlyRevenue']) ?? 0.0,
    );
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
      'total_sales': totalSales,
      'today_sales': todaySales,
      'monthly_sales': monthlySales,
      'yearly_revenue': yearlyRevenue,
    };
  }

  SalesStats copyWith({
    double? totalSales,
    double? todaySales,
    double? monthlySales,
    double? yearlyRevenue,
  }) {
    return SalesStats(
      totalSales: totalSales ?? this.totalSales,
      todaySales: todaySales ?? this.todaySales,
      monthlySales: monthlySales ?? this.monthlySales,
      yearlyRevenue: yearlyRevenue ?? this.yearlyRevenue,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is SalesStats &&
        other.totalSales == totalSales &&
        other.todaySales == todaySales &&
        other.monthlySales == monthlySales &&
        other.yearlyRevenue == yearlyRevenue;
  }

  @override
  int get hashCode =>
      totalSales.hashCode ^
      todaySales.hashCode ^
      monthlySales.hashCode ^
      yearlyRevenue.hashCode;

  @override
  String toString() {
    return 'SalesStats{totalSales: ₱$totalSales, todaySales: ₱$todaySales, monthlySales: ₱$monthlySales, yearlyRevenue: ₱$yearlyRevenue}';
  }
}
