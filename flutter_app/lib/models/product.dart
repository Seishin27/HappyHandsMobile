class Product {
  final int id;
  final String name;
  final double price;
  final String? imageUrl;
  final String description;
  final int? stock;
  final String? category;
  final List<String> imageUrls;
  final double? rating;
  final int? reviewCount;

  const Product({
    required this.id,
    required this.name,
    required this.price,
    this.imageUrl,
    required this.description,
    this.stock,
    this.category,
    this.imageUrls = const [],
    this.rating,
    this.reviewCount,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    // Handle multiple image URLs — accept either a list or a comma-separated string.
    final dynamic rawImages = json['image_urls'] ??
        json['gallery_images'] ??
        json['image_path'] ??
        json['image_url'] ??
        json['image'] ??
        json['main_image'] ??
        json['imageurl'];

    List<String> images = [];
    if (rawImages is List) {
      images = rawImages
          .map((e) => e?.toString().trim() ?? '')
          .where((s) => s.isNotEmpty)
          .toList();
    } else if (rawImages != null) {
      final text = rawImages.toString();
      if (text.isNotEmpty) {
        images = text
            .split(RegExp(r'[,|;\n]'))
            .map((url) => url.trim())
            .where((url) => url.isNotEmpty)
            .toList();
      }
    }

    return Product(
      id: _parseInt(json['id'] ?? json['productID'] ?? json['product_id']) ?? 0,
      name: (json['name'] ?? json['title'] ?? '').toString(),
      price: _parseDouble(json['price']) ?? 0.0,
      imageUrl: images.isNotEmpty ? images.first : null,
      description: (json['description'] ?? json['desc'] ?? json['details'] ?? json['productdesc'] ?? '').toString(),
      stock: _parseInt(json['stock'] ?? json['quantity'] ?? json['qty']),
      category: json['category']?.toString(),
      imageUrls: images,
      rating: _parseDouble(json['rating']),
      reviewCount: _parseInt(json['review_count']),
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
      'id': id,
      'name': name,
      'price': price,
      'image_url': imageUrl,
      'description': description,
      'stock': stock,
      'category': category,
      'image_urls': imageUrls,
      'rating': rating,
      'review_count': reviewCount,
    };
  }

  Product copyWith({
    int? id,
    String? name,
    double? price,
    String? imageUrl,
    String? description,
    int? stock,
    String? category,
    List<String>? imageUrls,
    double? rating,
    int? reviewCount,
  }) {
    return Product(
      id: id ?? this.id,
      name: name ?? this.name,
      price: price ?? this.price,
      imageUrl: imageUrl ?? this.imageUrl,
      description: description ?? this.description,
      stock: stock ?? this.stock,
      category: category ?? this.category,
      imageUrls: imageUrls ?? this.imageUrls,
      rating: rating ?? this.rating,
      reviewCount: reviewCount ?? this.reviewCount,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Product && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() {
    return 'Product{id: $id, name: $name, price: ₱$price, stock: $stock}';
  }
}

