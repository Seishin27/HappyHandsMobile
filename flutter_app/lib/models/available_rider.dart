/// Model representing an available rider for order assignment.
///
/// Used in the seller's "Request Rider" flow to display selectable riders.
class AvailableRider {
  final int riderID;
  final String ridername;
  final String? rideremail;
  final String? phone;
  final String status;

  const AvailableRider({
    required this.riderID,
    required this.ridername,
    this.rideremail,
    this.phone,
    required this.status,
  });

  factory AvailableRider.fromJson(Map<String, dynamic> json) {
    return AvailableRider(
      riderID: _parseInt(json['riderID'] ?? json['rider_id'] ?? json['id']) ?? 0,
      ridername: (json['ridername'] ?? json['rider_name'] ?? json['name'] ?? 'Unknown').toString(),
      rideremail: json['rideremail']?.toString() ?? json['rider_email']?.toString(),
      phone: json['phone']?.toString() ?? json['contact']?.toString(),
      status: (json['status'] ?? 'active').toString(),
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

  @override
  String toString() =>
      'AvailableRider{riderID: $riderID, ridername: $ridername, phone: $phone}';
}
