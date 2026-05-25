import 'package:flutter/foundation.dart';
import '../core/config/app_config.dart';

class SellerProduct {
  final int id;
  final String name;
  final String description;
  final double price;
  final String category;
  final int stockQuantity;
  final List<String> images;

  const SellerProduct({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.category,
    required this.stockQuantity,
    this.images = const [],
  });

  factory SellerProduct.fromJson(Map<String, dynamic> json) {
    // Backend (mobile_api) returns:
    //   image_path:  "prod_17_xxx.jpg"          (raw filename for storage)
    //   image_url:   "/static/uploads/prod_..."  (relative URL for display)
    // Older shapes may use `images` (list) or `image_urls` (comma string).
    final dynamic rawImages = json['images'] ??
        json['image_urls'] ??
        json['gallery_images'];

    List<String> imageList = [];
    if (rawImages is List) {
      imageList = rawImages
          .map((e) => e?.toString().trim() ?? '')
          .where((s) => s.isNotEmpty)
          .toList();
    } else if (rawImages != null) {
      final text = rawImages.toString();
      if (text.isNotEmpty) {
        imageList = text
            .split(RegExp(r'[,|;\n]'))
            .map((url) => url.trim())
            .where((url) => url.isNotEmpty)
            .toList();
      }
    }

    // Single-image fallback: prefer the server-rendered URL, fall back to
    // the raw filename in `image_path`.
    if (imageList.isEmpty) {
      final url = json['image_url']?.toString().trim();
      final path = json['image_path']?.toString().trim();
      if (url != null && url.isNotEmpty) {
        imageList = [url];
      } else if (path != null && path.isNotEmpty) {
        imageList = [path];
      }
    }

    // Resolve each entry to a fully-qualified URL the UI can hand to
    // Image.network directly. Skip already-absolute URLs.
    imageList = imageList.map(_resolveImageUrl).toList();
    // ignore: avoid_print
    debugPrint('[SellerProduct] resolved images: $imageList');

    return SellerProduct(
      id: _parseInt(json['id'] ?? json['productID'] ?? json['product_id']) ?? 0,
      name: (json['name'] ?? json['product_name'] ?? json['productName'] ?? '').toString(),
      description: (json['description'] ?? json['desc'] ?? json['product_description'] ?? '').toString(),
      price: _parseDouble(json['price'] ?? json['product_price']) ?? 0.0,
      category: (json['category_id'] ?? json['categoryID'] ?? json['category'] ?? json['product_category'] ?? '').toString(),
      stockQuantity: _parseInt(json['stock'] ?? json['stock_quantity'] ?? json['stockQuantity'] ?? json['quantity']) ?? 0,
      images: imageList,
    );
  }

  static String _resolveImageUrl(String raw) {
    if (raw.isEmpty) return raw;
    // Already a full absolute URL — use as-is.
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    // uploadsBaseUrl is derived from apiBaseUrl with /api stripped, then /uploads appended.
    // e.g. http://127.0.0.1:5500/api → http://127.0.0.1:5500/uploads
    final uploadsBase = AppConfig.uploadsBaseUrl; // e.g. http://127.0.0.1:5500/uploads
    final serverBase = uploadsBase.replaceAll(RegExp(r'/uploads/?$'), ''); // e.g. http://127.0.0.1:5500
    // Path already contains /uploads — just prepend server root.
    if (raw.startsWith('/uploads/') || raw.startsWith('/uploads')) {
      return '$serverBase$raw';
    }
    // Path contains /static/uploads or /static — just prepend server root.
    if (raw.startsWith('/static/')) {
      return '$serverBase$raw';
    }
    // Bare filename (e.g. "prod_seller1_xxx.jpg") → served from /uploads/.
    return '$uploadsBase/$raw';
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
      'description': description,
      'price': price,
      'categoryID': category, // Match database column name
      'stock': stockQuantity, // Match database column name
      'images': images,
    };
  }

  SellerProduct copyWith({
    int? id,
    String? name,
    String? description,
    double? price,
    String? category,
    int? stockQuantity,
    List<String>? images,
  }) {
    return SellerProduct(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      price: price ?? this.price,
      category: category ?? this.category,
      stockQuantity: stockQuantity ?? this.stockQuantity,
      images: images ?? this.images,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is SellerProduct && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() {
    return 'SellerProduct{id: $id, name: $name, price: ₱$price, category: $category, stock: $stockQuantity}';
  }
}
