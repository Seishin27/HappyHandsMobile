/// Data model for seller profile information.
///
/// This model represents a seller's profile with personal and business details.
/// It includes validation methods for email and phone formats.
class SellerProfile {
  final String id;
  final String name;
  final String email;
  final String phone;
  final String businessName;
  final String businessAddress;

  SellerProfile({
    required this.id,
    required this.name,
    required this.email,
    required this.phone,
    required this.businessName,
    required this.businessAddress,
  });

  /// Creates a SellerProfile from JSON data.
  ///
  /// Expects JSON with keys: id, name, email, phone, businessName, businessAddress
  /// (or snake_case variants: business_name, business_address)
  factory SellerProfile.fromJson(Map<String, dynamic> json) {
    // The backend returns `id`/`sellerID` as ints — coerce to string.
    final rawId = json['id'] ?? json['sellerID'];
    return SellerProfile(
      id: rawId == null ? '' : rawId.toString(),
      name:  (json['name']  ?? json['sellername']  ?? '').toString(),
      email: (json['email'] ?? json['selleremail'] ?? '').toString(),
      phone: (json['phone'] ?? json['contactnumber'] ?? '').toString(),
      businessName: (json['businessName']
              ?? json['business_name']
              ?? json['storename']
              ?? '').toString(),
      businessAddress: (json['businessAddress']
              ?? json['business_address']
              ?? json['exact_address']
              ?? '').toString(),
    );
  }

  /// Converts the SellerProfile to JSON format.
  ///
  /// Returns a map with camelCase keys matching the API expectations.
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'phone': phone,
      'businessName': businessName,
      'businessAddress': businessAddress,
    };
  }

  /// Validates email format.
  ///
  /// Returns true if email is in valid format, false otherwise.
  bool isValidEmail() {
    final emailRegex = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    );
    return emailRegex.hasMatch(email);
  }

  /// Validates phone format.
  ///
  /// Returns true if phone contains at least 10 digits, false otherwise.
  bool isValidPhone() {
    final phoneDigits = phone.replaceAll(RegExp(r'[^\d]'), '');
    return phoneDigits.length >= 10;
  }

  /// Creates a copy of this profile with optional field overrides.
  SellerProfile copyWith({
    String? id,
    String? name,
    String? email,
    String? phone,
    String? businessName,
    String? businessAddress,
  }) {
    return SellerProfile(
      id: id ?? this.id,
      name: name ?? this.name,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      businessName: businessName ?? this.businessName,
      businessAddress: businessAddress ?? this.businessAddress,
    );
  }

  @override
  String toString() {
    return 'SellerProfile(id: $id, name: $name, email: $email, phone: $phone, '
        'businessName: $businessName, businessAddress: $businessAddress)';
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SellerProfile &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          name == other.name &&
          email == other.email &&
          phone == other.phone &&
          businessName == other.businessName &&
          businessAddress == other.businessAddress;

  @override
  int get hashCode =>
      id.hashCode ^
      name.hashCode ^
      email.hashCode ^
      phone.hashCode ^
      businessName.hashCode ^
      businessAddress.hashCode;
}
