class RiderStatsSummary {
  final int totalDeliveries;
  final int activeOrders;
  final int completedToday;
  final double totalEarnings;
  final double earningsWeek;
  final double earningsMonth;

  const RiderStatsSummary({
    required this.totalDeliveries,
    required this.activeOrders,
    required this.completedToday,
    required this.totalEarnings,
    required this.earningsWeek,
    required this.earningsMonth,
  });

  const RiderStatsSummary.empty()
      : totalDeliveries = 0,
        activeOrders = 0,
        completedToday = 0,
        totalEarnings = 0,
        earningsWeek = 0,
        earningsMonth = 0;

  factory RiderStatsSummary.fromJson(Map<String, dynamic> json) {
    return RiderStatsSummary(
      totalDeliveries: (json['total_deliveries'] as num?)?.toInt() ?? 0,
      activeOrders:    (json['active_orders'] as num?)?.toInt() ?? 0,
      completedToday:  (json['completed_today'] as num?)?.toInt() ?? 0,
      totalEarnings:   (json['total_earnings'] as num?)?.toDouble() ?? 0.0,
      earningsWeek:    (json['earnings_week'] as num?)?.toDouble() ?? 0.0,
      earningsMonth:   (json['earnings_month'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class RiderOrder {
  final int sellerOrderId;
  final String orderNumber;
  final String status;
  final double totalAmount;
  final String shopName;
  final String userName;
  final String pickupAddress;
  final String deliveryAddress;
  final String createdAt;

  const RiderOrder({
    required this.sellerOrderId,
    required this.orderNumber,
    required this.status,
    required this.totalAmount,
    required this.shopName,
    required this.userName,
    required this.pickupAddress,
    required this.deliveryAddress,
    required this.createdAt,
  });

  factory RiderOrder.fromJson(Map<String, dynamic> json) {
    return RiderOrder(
      sellerOrderId:   (json['sellerOrderID'] as num?)?.toInt() ?? 0,
      orderNumber:     (json['order_number'] ?? '').toString(),
      status:          (json['status'] ?? 'pending').toString(),
      totalAmount:     (json['total_amount'] as num?)?.toDouble() ?? 0.0,
      shopName:        (json['shop_name'] ?? 'Shop').toString(),
      userName:        (json['user_name'] ?? 'Customer').toString(),
      pickupAddress:   (json['pickup_address'] ?? '').toString(),
      deliveryAddress: (json['delivery_address'] ?? '').toString(),
      createdAt:       (json['created_at'] ?? '').toString(),
    );
  }

  String get displayStatus {
    switch (status.toLowerCase()) {
      case 'assigned_to_rider': return 'Assigned';
      case 'on_the_way':        return 'On the Way';
      case 'delivered':         return 'Delivered';
      case 'packed':            return 'Packed';
      case 'cancelled':         return 'Cancelled';
      default:                  return status;
    }
  }
}

class RiderOrderSummary {
  final int sellerOrderId;
  final String orderNumber;
  final String status;
  final String? customerName;

  const RiderOrderSummary({
    required this.sellerOrderId,
    required this.orderNumber,
    required this.status,
    required this.customerName,
  });

  factory RiderOrderSummary.fromJson(Map<String, dynamic> json) {
    return RiderOrderSummary(
      sellerOrderId: (json['sellerOrderID'] as num?)?.toInt() ?? 0,
      orderNumber:   (json['order_number'] ?? '').toString(),
      status:        (json['status'] ?? '').toString(),
      customerName:  json['customer_name']?.toString(),
    );
  }
}

class RiderProfile {
  final int riderId;
  final String name;
  final String email;
  final String phone;
  final String vehicleType;
  final String profilePath;
  final String status;

  const RiderProfile({
    required this.riderId,
    required this.name,
    required this.email,
    required this.phone,
    required this.vehicleType,
    required this.profilePath,
    required this.status,
  });

  factory RiderProfile.fromJson(Map<String, dynamic> json) {
    return RiderProfile(
      riderId:     (json['riderID'] as num?)?.toInt() ?? 0,
      name:        (json['name'] ?? '').toString(),
      email:       (json['email'] ?? '').toString(),
      phone:       (json['phone'] ?? '').toString(),
      vehicleType: (json['vehicle_type'] ?? '').toString(),
      profilePath: (json['profile_path'] ?? '').toString(),
      status:      (json['status'] ?? '').toString(),
    );
  }
}
