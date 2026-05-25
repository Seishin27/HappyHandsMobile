import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' hide Category;
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../core/config/app_config.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exceptions.dart';
import '../models/api_response.dart';
import '../models/cart_item.dart';
import '../models/chat.dart';
import '../models/category.dart';
import '../models/product.dart';
import '../models/role.dart';
import '../models/seller_stats.dart';
import '../models/rider_models.dart';
import '../models/seller_product.dart';
import '../models/seller_order.dart';
import '../models/available_rider.dart';
import '../models/seller_profile.dart';

typedef TokenProvider = Future<String?> Function();

class FlaskApiService {
  final ApiClient _api;
  final TokenProvider? _tokenProvider;

  FlaskApiService(this._api, {TokenProvider? tokenProvider})
    : _tokenProvider = tokenProvider;

  List<Map<String, dynamic>> _readMapList(dynamic value) {
    if (value is List<dynamic>) {
      return value
          .whereType<Map<String, dynamic>>().map((e) => Map<String, dynamic>.from(e))
          .toList();
    }

    if (value is Map) {
      final nested = value['items'] ?? value['products'] ?? value['categories'];
      if (nested is List<dynamic>) {
        return nested
            .whereType<Map<String, dynamic>>().map((e) => Map<String, dynamic>.from(e))
            .toList();
      }
    }

    return const [];
  }

  Map<String, dynamic> _readMap(dynamic value) {
    return value is Map<String, dynamic> ? value : <String, dynamic>{};
  }

  Future<List<Product>> fetchProducts({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
    String? sortBy,
    String? sortOrder,
  }) async {
    final query = <String, String>{'page': '$page', 'page_size': '$pageSize'};
    if (category != null && category.isNotEmpty) query['category'] = category;
    if (search != null && search.isNotEmpty) query['search'] = search;
    if (sortBy != null && sortBy.isNotEmpty) query['sort_by'] = sortBy;
    if (sortOrder != null && sortOrder.isNotEmpty) { query['sort_order'] = sortOrder; }

    final raw = await _api.getJson('/products', query: query);

    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);
    if (!parsed.isSuccess && raw['status'] != null) {
      throw Exception(parsed.message);
    }

    final payload = parsed.data ?? raw['data'] ?? raw;
    final items = _readMapList(payload);
    if (items.isNotEmpty) {
      return items.map(Product.fromJson).toList();
    }

    if (payload is List<dynamic>) {
      return payload
          .whereType<Map<String, dynamic>>()
          .map(Product.fromJson)
          .toList();
    }

    return const [];
  }

  Future<List<Product>> fetchFeaturedProducts({
    int page = 1,
    int perPage = 12,
  }) async {
    final raw = await _api.getJson(
      '/products/featured',
      query: {'page': '$page', 'per_page': '$perPage'},
    );

    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);
    if (!parsed.isSuccess && raw['status'] != null) {
      throw Exception(parsed.message);
    }

    final payload = parsed.data ?? raw['data'] ?? raw;
    final items = _readMapList(payload);
    return items.map(Product.fromJson).toList();
  }

  Future<List<Product>> searchProducts(
    String query, {
    int page = 1,
    int pageSize = 20,
  }) async {
    return fetchProducts(search: query, page: page, pageSize: pageSize);
  }

  Future<List<Product>> fetchProductsByCategory(
    String category, {
    int page = 1,
    int pageSize = 20,
  }) async {
    return fetchProducts(category: category, page: page, pageSize: pageSize);
  }

  Future<
    ({Category current, List<Category> categories, List<Product> products})
  >
  fetchCategory(String slug, {int page = 1, int perPage = 12}) async {
    final raw = await _api.getJson(
      '/categories/$slug',
      query: {'page': '$page', 'per_page': '$perPage'},
    );

    // Accept both legacy JSON and envelope JSON.
    final categoriesRaw = _readMapList(raw['categories'] ?? raw['data']);
    final currentRaw = _readMap(
      raw['current_category'] ?? raw['current'] ?? raw['data'],
    );
    final productsRaw = _readMapList(raw['products'] ?? raw['data']);

    final categories = categoriesRaw
        .whereType<Map<String, dynamic>>()
        .map(Category.fromJson)
        .where((c) => c.slug.isNotEmpty)
        .toList();

    final current = Category.fromJson(currentRaw);
    final products = productsRaw
        .whereType<Map<String, dynamic>>()
        .map(Product.fromJson)
        .toList();

    return (current: current, categories: categories, products: products);
  }

  Future<Product> fetchProduct(int id) async {
    final raw = await _api.getJson('/products/$id');
    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);
    if (!parsed.isSuccess && raw['status'] != null) {
      throw Exception(parsed.message);
    }

    final payload = parsed.data ?? raw['data'] ?? raw['product'] ?? raw;
    if (payload is Map<String, dynamic>) {
      return Product.fromJson(payload);
    }

    throw Exception('Invalid product response');
  }

  Future<List<CartItem>> fetchCart() async {
    final raw = await _api.getJson('/cart');
    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);

    if (!parsed.isSuccess && raw['status'] != null) {
      throw Exception(parsed.message);
    }

    final payload = parsed.data ?? raw['data'] ?? raw;
    final items = _readMapList(payload);
    return items.map(CartItem.fromJson).toList();
  }

  Future<CartItem> addToCart({
    required int productId,
    int quantity = 1,
    String? size,
    String? color,
  }) async {
    final body = <String, dynamic>{
      'product_id': productId,
      'quantity': quantity,
    };
    if (size != null) body['size'] = size;
    if (color != null) body['color'] = color;

    final raw = await _api.postJson('/cart', body);
    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);
    if (!parsed.isSuccess) {
      throw Exception(parsed.message);
    }
    final payload = parsed.data ?? raw['data'] ?? raw;
    if (payload is Map<String, dynamic>) {
      return CartItem.fromJson(payload);
    }
    throw Exception('Invalid addToCart response');
  }

  Future<CartItem> updateCartItem({
    required int cartItemId,
    required int quantity,
  }) async {
    final raw = await _api.putJson('/cart/$cartItemId', {'quantity': quantity});
    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);
    if (!parsed.isSuccess) {
      throw Exception(parsed.message);
    }
    final payload = parsed.data ?? raw['data'] ?? raw;
    if (payload is Map<String, dynamic>) {
      return CartItem.fromJson(payload);
    }
    throw Exception('Invalid updateCartItem response');
  }

  Future<void> removeFromCart(int cartItemId) async {
    final raw = await _api.deleteJson('/cart/$cartItemId');
    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);
    if (!parsed.isSuccess) {
      throw Exception(parsed.message);
    }
  }

  Future<void> clearCart() async {
    final raw = await _api.deleteJson('/cart');
    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);
    if (!parsed.isSuccess) {
      throw Exception(parsed.message);
    }
  }

  Future<List<AppRole>> fetchRoles(String email) async {
    final raw = await _api.postJson('/roles', {'email': email});
    final parsed = ApiResponse.fromJson<dynamic>(raw, (data) => data);

    if (!parsed.isSuccess && raw['status'] != null) {
      throw Exception(parsed.message);
    }

    final payload = parsed.data ?? raw['data'] ?? raw;
    final roles = payload is Map<String, dynamic>
        ? (payload['roles'] as List<dynamic>? ?? const [])
        : const [];
    return roles
        .map((e) => AppRoleX.fromKey(e.toString()))
        .whereType<AppRole>()
        .toList();
  }

  Future<List<SellerSalesPoint>> fetchSellerSalesDaily() async {
    final raw = await _api.getJson(
      '/seller/stats/sales',
      query: {'range': 'daily'},
    );
    final ok = raw['success'] == true;
    if (!ok) {
      throw Exception(
        (raw['msg'] ?? 'Failed to fetch seller sales').toString(),
      );
    }
    final data = (raw['data'] as List<dynamic>? ?? const []);
    return data
        .whereType<Map<String, dynamic>>()
        .map(SellerSalesPoint.fromJson)
        .toList();
  }

  Future<List<SellerOrdersPoint>> fetchSellerOrdersDaily() async {
    final raw = await _api.getJson(
      '/seller/stats/orders',
      query: {'range': 'daily'},
    );
    final ok = raw['success'] == true;
    if (!ok) {
      throw Exception(
        (raw['msg'] ?? 'Failed to fetch seller orders stats').toString(),
      );
    }
    final data = (raw['data'] as List<dynamic>? ?? const []);
    return data
        .whereType<Map<String, dynamic>>()
        .map(SellerOrdersPoint.fromJson)
        .toList();
  }

  Future<List<SellerRecentOrder>> fetchSellerRecentOrders({
    int limit = 10,
  }) async {
    final raw = await _api.getJson(
      '/seller/stats/recent-orders',
      query: {'limit': '$limit'},
    );
    final ok = raw['success'] == true;
    if (!ok) {
      throw Exception(
        (raw['msg'] ?? 'Failed to fetch recent orders').toString(),
      );
    }
    // Flask returns the list under `data`, not `orders`.
    final orders =
        (raw['data'] as List<dynamic>? ??
        raw['orders'] as List<dynamic>? ??
        const []);
    return orders
        .whereType<Map<String, dynamic>>()
        .map(SellerRecentOrder.fromJson)
        .toList();
  }

  Future<SellerStatsSummary> fetchSellerSummary() async {
    final raw = await _api.getJson('/seller/stats/summary');
    final ok = raw['success'] == true;
    if (!ok) {
      throw Exception(
        (raw['msg'] ?? 'Failed to fetch seller summary').toString(),
      );
    }
    final data = raw['data'];
    if (data is Map<String, dynamic>) {
      return SellerStatsSummary.fromJson(data);
    }
    return const SellerStatsSummary.empty();
  }

  Future<List<RiderOrderSummary>> fetchRiderOrders() async {
    final raw = await _api.getJson('/rider/orders');
    final ok = raw['success'] == true;
    if (!ok) {
      throw Exception(
        (raw['msg'] ?? 'Failed to fetch rider orders').toString(),
      );
    }
    final orders = (raw['orders'] as List<dynamic>? ?? const []);
    return orders
        .whereType<Map<String, dynamic>>()
        .map(RiderOrderSummary.fromJson)
        .toList();
  }

  // ── Rider mobile endpoints ────────────────────────────────────────────────

  Future<RiderStatsSummary> fetchRiderStats() async {
    final raw = await _api.getJson('/rider/stats/summary');
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to load rider stats')); }
    final data = raw['data'];
    if (data is Map<String, dynamic>) return RiderStatsSummary.fromJson(data);
    return const RiderStatsSummary.empty();
  }

  Future<List<RiderOrder>> fetchRiderActiveOrders() async {
    final raw = await _api.getJson('/rider/orders/active');
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to load orders')); }
    final data = raw['data'];
    final list =
        (data is Map ? data['orders'] : null) as List<dynamic>? ?? const [];
    return list
        .whereType<Map<String, dynamic>>()
        .map(RiderOrder.fromJson)
        .toList();
  }

  Future<List<RiderOrder>> fetchRiderDeliveredOrders() async {
    final raw = await _api.getJson('/rider/orders/delivered');
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to load orders')); }
    final data = raw['data'];
    final list =
        (data is Map ? data['orders'] : null) as List<dynamic>? ?? const [];
    return list
        .whereType<Map<String, dynamic>>()
        .map(RiderOrder.fromJson)
        .toList();
  }

  Future<void> riderRespondToOrder(int orderId, String action) async {
    final raw = await _api.postJson('/rider/orders/$orderId/respond', {
      'action': action,
    });
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to respond to order')); }
  }

  Future<void> riderUpdateOrderStatus(int orderId, String status) async {
    final raw = await _api.postJson('/rider/orders/$orderId/status', {
      'status': status,
    });
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to update status')); }
  }

  Future<RiderProfile> fetchRiderProfile() async {
    final raw = await _api.getJson('/rider/profile/me');
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to load profile')); }
    final data = raw['data'];
    if (data is Map<String, dynamic>) return RiderProfile.fromJson(data);
    throw Exception('Invalid profile response');
  }

  Future<void> updateRiderProfile(Map<String, String> fields) async {
    final raw = await _api.putJson('/rider/profile/me', fields);
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to update profile')); }
  }

  Future<void> changeRiderPassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    final raw = await _api.postJson('/rider/profile/change-password', {
      'current_password': currentPassword,
      'new_password': newPassword,
      'confirm_password': newPassword,
    });
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to change password')); }
  }

  /// Upload a Proof of Delivery image for a delivered order.
  /// Returns the pod_image_url and uploaded_at from the server.
  Future<Map<String, String>> uploadPod({
    required int orderId,
    required Uint8List bytes,
    required String fileName,
  }) async {
    final base = AppConfig.apiBaseUrl.replaceAll(RegExp(r'/$'), '');
    final uri = Uri.parse('$base/rider/orders/$orderId/pod');

    // Derive MIME type from extension so the backend receives the correct
    // content-type even when running on Flutter Web.
    final ext = fileName.split('.').last.toLowerCase();

    final req = http.MultipartRequest('POST', uri);
    req.files.add(http.MultipartFile.fromBytes(
      'image',
      bytes,
      filename: fileName,
      contentType: MediaType('image', ext == 'png' ? 'png' : 'jpeg'),
    ));

    final token = (_tokenProvider != null) ? await _tokenProvider!() : null;
    if (token != null && token.isNotEmpty) {
      req.headers['Authorization'] = 'Bearer $token';
    }
    req.headers['Accept'] = 'application/json';

    final streamed = await req.send().timeout(AppConfig.requestTimeout);
    final res = await http.Response.fromStream(streamed);

    Map<String, dynamic> body;
    try {
      body = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {
      throw Exception('Invalid server response (HTTP ${res.statusCode})');
    }

    if (!_envelopeOk(body)) {
      throw Exception(_envelopeError(body, 'Failed to upload proof of delivery'));
    }

    final data = (body['data'] as Map<String, dynamic>?) ?? {};
    return {
      'pod_image_url': (data['pod_image_url'] ?? '').toString(),
      'uploaded_at':   (data['uploaded_at'] ?? '').toString(),
    };
  }

  /// Fetch the POD image info for an order (customer or rider view).
  Future<Map<String, dynamic>> fetchPod(int orderId) async {
    final raw = await _api.getJson('/orders/$orderId/pod');
    if (!_envelopeOk(raw)) { throw Exception(_envelopeError(raw, 'Failed to fetch proof of delivery')); }
    final data = (raw['data'] as Map<String, dynamic>?) ?? {};
    return {
      'pod_image_url': data['pod_image_url'],
      'uploaded_at':   data['uploaded_at'],
      'order_status':  data['order_status'],
    };
  }

  // ── Rider Chat ───────────────────────────────────────────────────────────

  Future<List<Conversation>> fetchRiderConversations() async {
    final raw = await _api.getJson('/rider/chat/conversations');
    final ok = raw['success'] == true || _envelopeOk(raw);
    if (!ok) {
      throw Exception(_envelopeError(raw, 'Failed to fetch conversations'));
    }
    final list =
        (raw['conversations'] as List<dynamic>? ??
        raw['data'] as List<dynamic>? ??
        const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(Conversation.fromJson)
        .toList();
  }

  Future<List<ChatMessage>> fetchRiderChatMessages(
    int partnerId,
    String partnerType, {
    int limit = 100,
  }) async {
    final raw = await _api.getJson(
      '/rider/chat/messages',
      query: {'partner_id': '$partnerId', 'type': partnerType, 'limit': '$limit'},
    );
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to fetch messages'));
    }
    final list = (raw['data'] as List<dynamic>? ?? const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(ChatMessage.fromJson)
        .toList();
  }

  // Dashboard statistics API methods for seller dashboard integration
  Future<List<SellerSalesPoint>> fetchSalesStats() async {
    try {
      final raw = await _api.getJson('/seller/stats/sales');
      final ok = raw['success'] == true;
      if (!ok) {
        throw Exception(
          (raw['msg'] ?? raw['message'] ?? 'Failed to fetch sales statistics')
              .toString(),
        );
      }
      final data = (raw['data'] as List<dynamic>? ?? const []);
      return data
          .whereType<Map<String, dynamic>>()
          .map(SellerSalesPoint.fromJson)
          .toList();
    } catch (e) {
      throw Exception('Error fetching sales statistics: ${e.toString()}');
    }
  }

  Future<List<SellerOrdersPoint>> fetchOrderStats() async {
    try {
      final raw = await _api.getJson('/seller/stats/orders');
      final ok = raw['success'] == true;
      if (!ok) {
        throw Exception(
          (raw['msg'] ?? raw['message'] ?? 'Failed to fetch order statistics')
              .toString(),
        );
      }
      final data = (raw['data'] as List<dynamic>? ?? const []);
      return data
          .whereType<Map<String, dynamic>>()
          .map(SellerOrdersPoint.fromJson)
          .toList();
    } catch (e) {
      throw Exception('Error fetching order statistics: ${e.toString()}');
    }
  }

  Future<List<SellerRecentOrder>> fetchRecentOrders() async {
    try {
      final raw = await _api.getJson('/seller/stats/recent-orders');
      final ok = raw['success'] == true;
      if (!ok) {
        throw Exception(
          (raw['msg'] ?? raw['message'] ?? 'Failed to fetch recent orders')
              .toString(),
        );
      }
      final orders = (raw['orders'] as List<dynamic>? ?? const []);
      return orders
          .whereType<Map<String, dynamic>>()
          .map(SellerRecentOrder.fromJson)
          .toList();
    } catch (e) {
      throw Exception('Error fetching recent orders: ${e.toString()}');
    }
  }

  // Product management API methods for seller dashboard integration

  /// Fetches paginated list of seller products.
  ///
  /// Parameters:
  /// - [page]: Page number (default: 1)
  /// - [pageSize]: Number of items per page (default: 20)
  ///
  /// Returns list of SellerProduct objects.
  ///
  /// Throws Exception if the request fails.
  // ── Seller products (CRUD against /api/seller/products) ────────────────────
  // The mobile_api blueprint returns the standard envelope:
  //   { "status": "success" | "error", "message": "...", "data": ... }
  // For create/update we send multipart/form-data with an optional `image`
  // file inline — no separate upload endpoint required.

  bool _envelopeOk(Map<String, dynamic> raw) {
    final status = raw['status']?.toString();
    if (status == 'success') return true;
    if (status == 'error') return false;
    // Accept legacy {success: true} too.
    return raw['success'] == true;
  }

  String _envelopeError(Map<String, dynamic> raw, String fallback) {
    final detail = (raw['data'] is Map<String, dynamic>)
        ? (raw['data'] as Map<String, dynamic>)['error']?.toString()
        : null;
    final msg = (raw['message'] ?? raw['msg'] ?? fallback).toString();
    return detail != null && detail.isNotEmpty ? '$msg ($detail)' : msg;
  }

  Future<List<SellerProduct>> fetchSellerProducts({
    int page = 1,
    int pageSize = 20,
  }) async {
    final raw = await _api.getJson('/seller/products');
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to fetch seller products'));
    }
    // seller_api.py returns the list under 'products'; fall back to 'data'
    // for any future envelope-style refactor.
    final list = (raw['products'] as List<dynamic>? ??
        raw['data'] as List<dynamic>? ??
        const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(SellerProduct.fromJson)
        .toList();
  }

  Future<SellerProduct> createProduct(
    SellerProduct product,
    List<PlatformFile>? images,
  ) async {
    final raw = await _multipartProduct(
      method: 'POST',
      path: '/seller/products',
      product: product,
      images: images,
    );
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to create product'));
    }
    // seller_api.py returns the created product under 'product' (singular);
    // fall back to 'data' for envelope-style responses.
    final data = raw['product'] ?? raw['data'];
    if (data is Map<String, dynamic>) {
      return SellerProduct.fromJson(data);
    }
    throw Exception('Unexpected create-product response shape');
  }

  Future<SellerProduct> updateProduct(
    String id,
    SellerProduct product,
    List<PlatformFile>? images,
  ) async {
    final raw = await _multipartProduct(
      method: 'PUT',
      path: '/seller/products/$id',
      product: product,
      images: images,
      existingImageUrls: product.images,
    );
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to update product'));
    }
    // seller_api.py returns the updated product under 'product' (singular);
    // fall back to 'data' for envelope-style responses.
    final data = raw['product'] ?? raw['data'];
    if (data is Map<String, dynamic>) {
      return SellerProduct.fromJson(data);
    }
    throw Exception('Unexpected update-product response shape');
  }

  Future<void> deleteProduct(String id) async {
    final raw = await _api.deleteJson('/seller/products/$id');
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to delete product'));
    }
  }

  /// Builds and sends a multipart product request.
  Future<Map<String, dynamic>> _multipartProduct({
    required String method,
    required String path,
    required SellerProduct product,
    List<PlatformFile>? images,
    List<String>? existingImageUrls,
  }) async {
    final base = AppConfig.apiBaseUrl.replaceAll(RegExp(r'/$'), '');
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    final uri = Uri.parse('$base/$cleanPath');

    final req = http.MultipartRequest(method, uri);
    req.fields['name'] = product.name;
    req.fields['description'] = product.description;
    req.fields['price'] = product.price.toString();
    req.fields['stock'] = product.stockQuantity.toString();
    if (product.category.isNotEmpty) {
      req.fields['category_id'] = product.category;
    }
    if (existingImageUrls != null && existingImageUrls.isNotEmpty) {
      req.fields['existing_images'] = existingImageUrls.join(',');
    }
    if (images != null) {
      for (int i = 0; i < images.length && i < 4; i++) {
        final img = images[i];
        if (img.bytes != null) {
          req.files.add(http.MultipartFile.fromBytes('image$i', img.bytes!, filename: img.name));
        } else if (img.path != null) {
          req.files.add(await http.MultipartFile.fromPath('image$i', img.path!));
        }
      }
    }

    final token = (_tokenProvider != null) ? await _tokenProvider!() : null;
    if (token != null && token.isNotEmpty) {
      req.headers['Authorization'] = 'Bearer $token';
    }
    req.headers['Accept'] = 'application/json';

    final streamed = await req.send().timeout(AppConfig.requestTimeout);
    final res = await http.Response.fromStream(streamed);
    Map<String, dynamic> body;
    try {
      body = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {
      throw ApiException(
        'Invalid server response (HTTP ${res.statusCode})',
        statusCode: res.statusCode,
      );
    }
    if (res.statusCode >= 200 && res.statusCode < 300) return body;
    // Flask returns the same envelope for error cases — let the caller decode.
    return body;
  }

  /// Fetches the allowed categories for the logged-in seller.
  Future<List<Map<String, dynamic>>> fetchSellerCategories() async {
    try {
      final raw = await _api.getJson('/seller/categories');
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to fetch seller categories'));
      }
      final data = raw['data'] as Map<String, dynamic>?;
      if (data != null && data.containsKey('categories')) {
        return (data['categories'] as List)
            .whereType<Map<String, dynamic>>()
            .toList();
      }
      return [];
    } catch (e) {
      throw Exception('Error fetching seller categories: ${e.toString()}');
    }
  }

  // Order management API methods for seller dashboard integration

  /// Fetches paginated list of seller orders.
  ///
  /// Parameters:
  /// - [page]: Page number (default: 1)
  /// - [pageSize]: Number of items per page (default: 20)
  ///
  /// Returns list of SellerOrder objects.
  ///
  /// Throws Exception if the request fails.
  Future<List<SellerOrder>> fetchSellerOrders({
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final raw = await _api.getJson(
        '/seller/orders',
        query: {'page': '$page', 'page_size': '$pageSize'},
      );

      debugPrint('📥 Raw orders response: $raw'); // Debug log

      final ok = raw['success'] == true;
      if (!ok) {
        final errorMsg =
            (raw['msg'] ?? raw['message'] ?? 'Failed to fetch seller orders')
                .toString();
        debugPrint('❌ Orders API error: $errorMsg');
        throw Exception(errorMsg);
      }

      final orders =
          (raw['orders'] as List<dynamic>? ??
          raw['data'] as List<dynamic>? ??
          const []);

      debugPrint('📦 Found ${orders.length} orders'); // Debug log

      if (orders.isNotEmpty) {
        debugPrint('📋 First order sample: ${orders.first}'); // Debug log
      }

      return orders
          .whereType<Map<String, dynamic>>()
          .map(SellerOrder.fromJson)
          .toList();
    } catch (e) {
      debugPrint('❌ Error fetching seller orders: $e');
      throw Exception('Error fetching seller orders: ${e.toString()}');
    }
  }

  /// Fetches detailed information for a specific order.
  ///
  /// Parameters:
  /// - [orderId]: Order ID to fetch
  ///
  /// Returns SellerOrder object with complete details including line items.
  ///
  /// Throws Exception if the request fails or order not found.
  Future<SellerOrder> fetchOrderDetails(String orderId) async {
    try {
      final raw = await _api.getJson('/seller/orders/$orderId');

      final ok = raw['success'] == true;
      if (!ok) {
        throw Exception(
          (raw['msg'] ?? raw['message'] ?? 'Failed to fetch order details')
              .toString(),
        );
      }

      final orderJson =
          raw['order'] as Map<String, dynamic>? ??
          raw['data'] as Map<String, dynamic>? ??
          raw;
      return SellerOrder.fromJson(orderJson);
    } catch (e) {
      throw Exception('Error fetching order details: ${e.toString()}');
    }
  }

  /// Updates the status of an order.
  ///
  /// Parameters:
  /// - [orderId]: Order ID to update
  /// - [newStatus]: New status value (e.g., 'pending', 'processing', 'shipped', 'delivered', 'cancelled')
  ///
  /// Returns the updated SellerOrder.
  ///
  /// Throws Exception if validation fails (invalid status transition),
  /// seller doesn't own order, or request fails.
  Future<SellerOrder> updateOrderStatus(
    String orderId,
    String newStatus, {
    String? notes,
  }) async {
    try {
      final body = <String, dynamic>{'status': newStatus};
      if (notes != null && notes.isNotEmpty) {
        body['notes'] = notes;
      }

      final raw = await _api.putJson('/seller/orders/$orderId/status', body);

      final ok = raw['success'] == true;
      if (!ok) {
        final message =
            raw['msg'] ?? raw['message'] ?? 'Failed to update order status';
        final errors = raw['errors'] ?? raw['validation_errors'];
        if (errors != null) {
          throw Exception('Validation error: ${errors.toString()}');
        }
        throw Exception(message.toString());
      }

      final orderJson =
          raw['order'] as Map<String, dynamic>? ??
          raw['data'] as Map<String, dynamic>? ??
          raw;
      return SellerOrder.fromJson(orderJson);
    } catch (e) {
      throw Exception('Error updating order status: ${e.toString()}');
    }
  }

  // Profile management API methods for seller dashboard integration

  /// Fetches the current seller's profile information.
  ///
  /// Returns SellerProfile object with seller's personal and business details.
  ///
  /// Throws Exception if the request fails or profile not found.
  Future<SellerProfile> fetchSellerProfile() async {
    final raw = await _api.getJson('/seller/profile');
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to fetch seller profile'));
    }
    final data = raw['data'];
    if (data is Map<String, dynamic>) {
      return SellerProfile.fromJson(data);
    }
    throw Exception('Unexpected profile response shape');
  }

  Future<SellerProfile> updateSellerProfile(SellerProfile profile) async {
    final raw = await _api.putJson('/seller/profile', profile.toJson());
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to update seller profile'));
    }
    final data = raw['data'];
    if (data is Map<String, dynamic>) {
      return SellerProfile.fromJson(data);
    }
    throw Exception('Unexpected profile update response shape');
  }

  Future<void> changePassword(
    String currentPassword,
    String newPassword,
  ) async {
    final raw = await _api.postJson('/seller/profile/change-password', {
      'current_password': currentPassword,
      'new_password': newPassword,
    });
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to change password'));
    }
  }

  // ── Seller chat (read-only, Phase 4 first slice) ──────────────────────────

  Future<List<Conversation>> fetchSellerConversations() async {
    final raw = await _api.getJson('/seller/chat/conversations');
    // This endpoint uses the older {success, conversations} shape — accept
    // it as well as the standard envelope.
    final ok = raw['success'] == true || _envelopeOk(raw);
    if (!ok) {
      throw Exception(_envelopeError(raw, 'Failed to fetch conversations'));
    }
    final list =
        (raw['conversations'] as List<dynamic>? ??
        raw['data'] as List<dynamic>? ??
        const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(Conversation.fromJson)
        .toList();
  }

  Future<List<ChatMessage>> fetchSellerChatMessages(
    int userId, {
    int limit = 100,
  }) async {
    final raw = await _api.getJson(
      '/seller/chat/messages',
      query: {'user_id': '$userId', 'limit': '$limit'},
    );
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to fetch messages'));
    }
    final list = (raw['data'] as List<dynamic>? ?? const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(ChatMessage.fromJson)
        .toList();
  }

  /// Sends a message from the seller to a specific user.
  Future<void> sendSellerChatMessage(int userId, String message) async {
    final raw = await _api.postJson('/seller/chat/messages', {
      'user_id': userId,
      'message': message,
    });
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to send message'));
    }
  }

  // ── User Address ─────────────────────────────────────────────────────────

  Future<Map<String, String>?> fetchSavedAddress() async {
    final raw = await _api.getJson('/user/address');
    if (!_envelopeOk(raw)) return null;
    final data = raw['data'];
    if (data is! Map<String, dynamic>) return null;
    return {
      'region': (data['region'] ?? '').toString(),
      'province': (data['province'] ?? '').toString(),
      'city': (data['city'] ?? '').toString(),
      'barangay': (data['barangay'] ?? '').toString(),
      'home_address': (data['home_address'] ?? '').toString(),
      'contact_number': (data['contact_number'] ?? '').toString(),
    };
  }

  Future<void> saveSavedAddress(Map<String, String> address) async {
    final raw = await _api.postJson('/user/address', address);
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to save address'));
    }
  }

  Future<double> estimateShipping({
    required String region,
    required String province,
    required String city,
    required String barangay,
    required List<int> productIds,
  }) async {
    final raw = await _api.postJson('/shipping/estimate', {
      'region': region,
      'province': province,
      'city': city,
      'barangay': barangay,
      'items': productIds,
    });
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to estimate shipping'));
    }
    final data = raw['data'];
    if (data is Map<String, dynamic>) {
      final shipping = data['shipping_fee'];
      if (shipping is num) return shipping.toDouble();
      final asText = shipping?.toString();
      if (asText != null) return double.tryParse(asText) ?? 0.0;
    }
    return 0.0;
  }

  // ── Checkout ─────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> placeOrder({
    required String region,
    required String province,
    required String city,
    required String barangay,
    required String homeAddress,
    required String contactNumber,
    required List<int> productIds,
  }) async {
    final body = <String, dynamic>{
      'region': region,
      'province': province,
      'city': city,
      'barangay': barangay,
      'home_address': homeAddress,
      'contact_number': contactNumber,
      'payment_method': 'cash_on_delivery',
      'items': productIds,
    };
    final raw = await _api.postJson('/checkout', body);
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to place order'));
    }
    final data = raw['data'];
    if (data is Map<String, dynamic>) return data;
    return const {};
  }
  // ── Seller Rider Management ─────────────────────────────────────────────

  /// Fetches list of available riders for order assignment.
  Future<List<AvailableRider>> fetchAvailableRiders() async {
    try {
      final raw = await _api.getJson('/seller/mobile/riders');
      final ok = raw['success'] == true;
      if (!ok) {
        throw Exception(
          (raw['msg'] ?? raw['message'] ?? 'Failed to fetch riders').toString(),
        );
      }
      final riders = (raw['riders'] as List<dynamic>? ?? const []);
      return riders
          .whereType<Map<String, dynamic>>()
          .map((e) => AvailableRider.fromJson(e))
          .toList();
    } catch (e) {
      throw Exception('Error fetching riders: ${e.toString()}');
    }
  }

  // ── User Orders ────────────────────────────────────────────────────────────

  /// Fetches user's order history.
  Future<List<Map<String, dynamic>>> fetchUserOrders({
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final raw = await _api.getJson(
        '/user/orders',
        query: {'page': '$page', 'page_size': '$pageSize'},
      );
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to fetch orders'));
      }
      // Backend returns { status, message, data: { orders: [...], page, page_size } }
      // Navigate the nested structure explicitly before falling back.
      final data = raw['data'];
      if (data is Map<String, dynamic>) {
        final nested = data['orders'];
        if (nested is List<dynamic>) {
          return nested
              .whereType<Map<String, dynamic>>().map((e) => Map<String, dynamic>.from(e))
              .toList();
        }
      }
      // Fallback: top-level orders key or flat list in data
      return _readMapList(raw['orders'] ?? raw['data']);
    } catch (e) {
      throw Exception('Error fetching orders: ${e.toString()}');
    }
  }

  /// Fetches detailed information for a specific user order.
  Future<Map<String, dynamic>> fetchUserOrderDetails(String orderId) async {
    try {
      final raw = await _api.getJson('/user/orders/$orderId');
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to fetch order details'));
      }
      return _readMap(raw['order'] ?? raw['data'] ?? raw);
    } catch (e) {
      throw Exception('Error fetching order details: ${e.toString()}');
    }
  }

  /// Confirms that the buyer has received the order.
  Future<void> confirmOrderReceived(int sellerOrderId) async {
    final raw = await _api.postJson('/user/orders/$sellerOrderId/confirm-received', {});
    if (!_envelopeOk(raw)) {
      throw Exception(_envelopeError(raw, 'Failed to confirm order received'));
    }
  }

  // ── User Profile ───────────────────────────────────────────────────────────

  /// Fetches user's profile information.
  Future<Map<String, dynamic>> fetchUserProfile() async {
    try {
      final raw = await _api.getJson('/profile');
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to fetch profile'));
      }
      return raw['user'] as Map<String, dynamic>? ??
          raw['data'] as Map<String, dynamic>? ??
          raw;
    } catch (e) {
      throw Exception('Error fetching profile: ${e.toString()}');
    }
  }

  /// Updates user's profile information.
  Future<Map<String, dynamic>> updateUserProfile(
    Map<String, dynamic> profileData,
  ) async {
    try {
      final raw = await _api.postJson('/profile', profileData);
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to update profile'));
      }
      return raw['user'] as Map<String, dynamic>? ??
          raw['data'] as Map<String, dynamic>? ??
          raw;
    } catch (e) {
      throw Exception('Error updating profile: ${e.toString()}');
    }
  }

  /// Changes user's password.
  Future<void> changeUserPassword(
    String currentPassword,
    String newPassword,
  ) async {
    try {
      final raw = await _api.postJson('/profile/change-password', {
        'current_password': currentPassword,
        'new_password': newPassword,
      });
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to change password'));
      }
    } catch (e) {
      throw Exception('Error changing password: ${e.toString()}');
    }
  }

  // ── User Messages ─────────────────────────────────────────────────────────

  /// Fetches user's message conversations with sellers.
  Future<List<Map<String, dynamic>>> fetchUserConversations() async {
    try {
      final raw = await _api.getJson('/user/conversations');
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to fetch conversations'));
      }
      final conversations =
          raw['conversations'] as List<dynamic>? ??
          raw['data'] as List<dynamic>? ??
          const [];
      return conversations.whereType<Map<String, dynamic>>().toList();
    } catch (e) {
      throw Exception('Error fetching conversations: ${e.toString()}');
    }
  }

  /// Fetches messages for a specific conversation with a seller.
  Future<List<Map<String, dynamic>>> fetchUserMessages(
    int sellerId, {
    int limit = 100,
  }) async {
    try {
      final raw = await _api.getJson(
        '/user/messages',
        query: {'seller_id': '$sellerId', 'limit': '$limit'},
      );
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to fetch messages'));
      }
      final messages =
          raw['messages'] as List<dynamic>? ??
          raw['data'] as List<dynamic>? ??
          const [];
      return messages.whereType<Map<String, dynamic>>().toList();
    } catch (e) {
      throw Exception('Error fetching messages: ${e.toString()}');
    }
  }

  /// Sends a message to a seller.
  Future<Map<String, dynamic>> sendUserMessage(
    int sellerId,
    String message,
  ) async {
    try {
      final raw = await _api.postJson('/user/messages', {
        'seller_id': sellerId,
        'message': message,
      });
      if (!_envelopeOk(raw)) {
        throw Exception(_envelopeError(raw, 'Failed to send message'));
      }
      return raw['message'] as Map<String, dynamic>? ??
          raw['data'] as Map<String, dynamic>? ??
          raw;
    } catch (e) {
      throw Exception('Error sending message: ${e.toString()}');
    }
  }

  // ── Seller Rider Management ─────────────────────────────────────────────

  /// Assigns a rider to a seller order.
  Future<Map<String, dynamic>> assignRiderToOrder(
    String orderId,
    int riderId,
  ) async {
    try {
      final raw = await _api.postJson(
        '/seller/orders/$orderId/mobile-assign-rider', {
        'riderID': riderId,
      });
      final ok = raw['success'] == true;
      if (!ok) {
        throw Exception(
          (raw['msg'] ?? raw['message'] ?? 'Failed to assign rider').toString(),
        );
      }
      return raw;
    } catch (e) {
      throw Exception('Error assigning rider: ${e.toString()}');
    }
  }

  // ── Rider Location Tracking ─────────────────────────────────────────────

  Future<void> updateRiderLocation(int orderId, double lat, double lng) async {
    await _api.postJson('/rider/orders/$orderId/location', {'lat': lat, 'lng': lng});
  }

  Future<Map<String, dynamic>?> fetchRiderLocation(int orderId) async {
    try {
      final raw = await _api.getJson('/orders/$orderId/rider-location');
      if (raw['success'] == true) {
        return raw['data'] as Map<String, dynamic>?;
      }
    } catch (_) {}
    return null;
  }
}
