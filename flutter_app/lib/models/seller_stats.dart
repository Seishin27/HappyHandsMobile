class SellerSalesPoint {
  final String date; // yyyy-mm-dd
  final double totalSales;

  const SellerSalesPoint({required this.date, required this.totalSales});

  factory SellerSalesPoint.fromJson(Map<String, dynamic> json) {
    return SellerSalesPoint(
      date: (json['date'] ?? '').toString(),
      totalSales: (json['total_sales'] as num?)?.toDouble() ?? 0,
    );
  }
}

class SellerOrdersPoint {
  final String date; // yyyy-mm-dd
  final int orderCount;

  const SellerOrdersPoint({required this.date, required this.orderCount});

  factory SellerOrdersPoint.fromJson(Map<String, dynamic> json) {
    return SellerOrdersPoint(
      date: (json['date'] ?? '').toString(),
      orderCount: (json['order_count'] as num?)?.toInt() ?? 0,
    );
  }
}

class SellerRecentOrder {
  final int sellerOrderId;
  final String orderNumber;
  final String status;
  final double totalAmount;
  final String customerName;
  final String product;
  final int quantity;
  final String? orderDate;

  const SellerRecentOrder({
    required this.sellerOrderId,
    required this.orderNumber,
    required this.status,
    required this.totalAmount,
    required this.customerName,
    required this.product,
    required this.quantity,
    this.orderDate,
  });

  factory SellerRecentOrder.fromJson(Map<String, dynamic> json) {
    return SellerRecentOrder(
      // Flask /api/seller/stats/recent-orders returns `order_id` (legacy
      // routes used `sellerOrderID` — accept either).
      sellerOrderId: (json['order_id'] as num?)?.toInt() ??
          (json['sellerOrderID'] as num?)?.toInt() ??
          0,
      orderNumber: (json['order_number'] ?? '').toString(),
      // `order_status` from this endpoint, `status` from others.
      status: (json['order_status'] ?? json['status'] ?? '').toString(),
      // Flask returns `total` here, but `total_amount` in other endpoints.
      totalAmount: (json['total'] as num?)?.toDouble() ??
          (json['total_amount'] as num?)?.toDouble() ??
          0,
      customerName: (json['customer_name'] ?? '').toString(),
      product: (json['product'] ?? '').toString(),
      quantity: (json['quantity'] as num?)?.toInt() ?? 0,
      orderDate: json['order_date']?.toString(),
    );
  }
}

class SellerStatsSummary {
  final int totalProducts;
  final double totalEarnings;
  final int totalOrders;
  final int pendingOrders;
  final int deliveredOrders;

  const SellerStatsSummary({
    required this.totalProducts,
    required this.totalEarnings,
    required this.totalOrders,
    required this.pendingOrders,
    required this.deliveredOrders,
  });

  const SellerStatsSummary.empty()
      : totalProducts = 0,
        totalEarnings = 0,
        totalOrders = 0,
        pendingOrders = 0,
        deliveredOrders = 0;

  factory SellerStatsSummary.fromJson(Map<String, dynamic> json) {
    return SellerStatsSummary(
      totalProducts:   (json['total_products']   as num?)?.toInt()    ?? 0,
      totalEarnings:   (json['total_earnings']   as num?)?.toDouble() ?? 0,
      totalOrders:     (json['total_orders']     as num?)?.toInt()    ?? 0,
      pendingOrders:   (json['pending_orders']   as num?)?.toInt()    ?? 0,
      deliveredOrders: (json['delivered_orders'] as num?)?.toInt()    ?? 0,
    );
  }
}

