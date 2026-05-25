import 'package:flutter/foundation.dart';
import 'dart:developer' as developer;

import '../models/product.dart';
import '../services/flask_api_service.dart';
import '../core/constants/app_constants.dart';
import '../data/mock_products.dart';

class ProductProvider extends ChangeNotifier {
  FlaskApiService? _apiService;

  void bindApi(FlaskApiService api) {
    _apiService = api;
  }

  bool get _hasApi => _apiService != null;

  List<Product> _products = [];
  List<Product> _featuredProducts = [];
  List<Product> _searchResults = [];
  Product? _selectedProduct;

  bool _isLoading = false;
  bool _isLoadingFeatured = false;
  bool _isLoadingSearch = false;
  bool _isLoadingProduct = false;

  String? _error;
  String? _searchError;
  String? _productError;

  int _currentPage = 1;
  int _totalPages = 1;
  int _totalItems = 0;
  String? _currentCategory;
  String? _currentSearchQuery;
  String? _currentSortBy;
  String? _currentSortOrder;

  ProductProvider() {
    // Seed mock data immediately so the UI is never empty
    _products = List.of(MockProducts.all);
    _featuredProducts = List.of(MockProducts.featured);
    _totalItems = _products.length;
  }

  // Getters
  List<Product> get products => List.unmodifiable(_products);
  List<Product> get featuredProducts => List.unmodifiable(_featuredProducts);
  List<Product> get searchResults => List.unmodifiable(_searchResults);
  Product? get selectedProduct => _selectedProduct;

  bool get isLoading => _isLoading;
  bool get isLoadingFeatured => _isLoadingFeatured;
  bool get isLoadingSearch => _isLoadingSearch;
  bool get isLoadingProduct => _isLoadingProduct;

  String? get error => _error;
  String? get searchError => _searchError;
  String? get productError => _productError;

  int get currentPage => _currentPage;
  int get totalPages => _totalPages;
  int get totalItems => _totalItems;
  String? get currentCategory => _currentCategory;
  String? get currentSearchQuery => _currentSearchQuery;
  bool get hasMorePages => _currentPage < _totalPages;

  // Load products with pagination and filters
  Future<void> loadProducts({
    int page = 1,
    int limit = AppConstants.defaultPageSize,
    String? category,
    String? search,
    String? sortBy,
    String? sortOrder,
    bool refresh = false,
  }) async {
    if (refresh) {
      _currentPage = 1;
      _error = null;
    }

    if (_isLoading && !refresh) return;

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      if (!_hasApi) throw StateError('FlaskApiService not bound');
      final products = await _apiService!.fetchProducts(
        page: page,
        pageSize: limit,
        category: category,
        search: search,
        sortBy: sortBy,
        sortOrder: sortOrder,
      );

      // Merge: keep mock products that aren't returned by the API
      final apiIds = products.map((p) => p.id).toSet();
      final mockFallback = MockProducts.all
          .where((p) =>
              (category == null || p.category == category) &&
              !apiIds.contains(p.id))
          .toList();
      final merged = [...products, ...mockFallback];

      if (refresh || page == 1) {
        _products = merged;
      } else {
        _products.addAll(merged);
      }

      _currentPage = page;
      _currentCategory = category;
      _currentSearchQuery = search;
      _currentSortBy = sortBy;
      _currentSortOrder = sortOrder;
      _totalPages = (products.length < limit) ? page : page + 1;
      _totalItems = _products.length;

      developer.log('Loaded ${products.length} products (+ ${mockFallback.length} mock) for page $page');
    } catch (e) {
      // API failed — fall back entirely to mock data
      developer.log('API unavailable, using mock products: $e');
      final mock = category == null
          ? MockProducts.all
          : MockProducts.byCategory(category);
      if (refresh || page == 1) {
        _products = List.of(mock);
      }
      _totalItems = _products.length;
      _totalPages = 1;
      // Don't set _error so the UI shows mock products silently
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Load more products (pagination)
  Future<void> loadMoreProducts() async {
    if (!hasMorePages || _isLoading) return;

    await loadProducts(page: _currentPage + 1);
  }

  // Refresh products
  Future<void> refreshProducts() async {
    await loadProducts(
      page: 1,
      category: _currentCategory,
      search: _currentSearchQuery,
      sortBy: _currentSortBy,
      sortOrder: _currentSortOrder,
      refresh: true,
    );
  }

  // Load featured products
  Future<void> loadFeaturedProducts({
    int page = 1,
    int limit = AppConstants.defaultPageSize,
    bool refresh = false,
  }) async {
    if (refresh) {
      _featuredProducts.clear();
    }

    if (_isLoadingFeatured) return;

    _isLoadingFeatured = true;
    notifyListeners();

    try {
      if (!_hasApi) throw StateError('FlaskApiService not bound');
      final products =
          await _apiService!.fetchFeaturedProducts(page: page, perPage: limit);

      final apiIds = products.map((p) => p.id).toSet();
      final mockFallback = MockProducts.featured
          .where((p) => !apiIds.contains(p.id))
          .toList();
      final merged = [...products, ...mockFallback];

      if (refresh || page == 1) {
        _featuredProducts = merged;
      } else {
        _featuredProducts.addAll(merged);
      }

      developer.log('Loaded ${products.length} featured products (+ ${mockFallback.length} mock)');
    } catch (e) {
      // API failed — use mock featured products silently
      developer.log('API unavailable for featured, using mock: $e');
      if (_featuredProducts.isEmpty) {
        _featuredProducts = List.of(MockProducts.featured);
      }
    } finally {
      _isLoadingFeatured = false;
      notifyListeners();
    }
  }

  // Load single product by ID
  Future<void> loadProductById(int productId) async {
    if (_isLoadingProduct) return;

    // Check mock data first for instant display
    final mockProduct = MockProducts.all
        .where((p) => p.id == productId)
        .firstOrNull;
    if (mockProduct != null) {
      _selectedProduct = mockProduct;
      notifyListeners();
    }

    _isLoadingProduct = true;
    _productError = null;
    notifyListeners();

    try {
      if (!_hasApi) throw StateError('FlaskApiService not bound');
      final product = await _apiService!.fetchProduct(productId);
      _selectedProduct = product;
      developer.log('Loaded product: ${product.name}');
    } catch (e) {
      if (_selectedProduct == null) {
        _productError = e.toString();
      }
      developer.log('API unavailable for product $productId, using mock: $e');
    } finally {
      _isLoadingProduct = false;
      notifyListeners();
    }
  }

  // Search products
  Future<void> searchProducts(String query, {int page = 1}) async {
    if (query.trim().isEmpty) {
      _searchResults.clear();
      _searchError = null;
      notifyListeners();
      return;
    }

    _isLoadingSearch = true;
    _searchError = null;
    notifyListeners();

    try {
      if (!_hasApi) throw StateError('FlaskApiService not bound');
      final products = await _apiService!.searchProducts(query, page: page);

      if (page == 1) {
        _searchResults = products;
      } else {
        _searchResults.addAll(products);
      }

      _currentSearchQuery = query;
      developer.log('Found ${products.length} products for query: $query');
    } catch (e) {
      // Fall back to local mock search
      developer.log('API search unavailable, searching mock: $e');
      final q = query.toLowerCase();
      final mockResults = MockProducts.all.where((p) =>
          p.name.toLowerCase().contains(q) ||
          p.description.toLowerCase().contains(q) ||
          (p.category?.toLowerCase().contains(q) ?? false)).toList();
      _searchResults = mockResults;
      _currentSearchQuery = query;
    } finally {
      _isLoadingSearch = false;
      notifyListeners();
    }
  }

  // Clear search results
  void clearSearch() {
    _searchResults.clear();
    _searchError = null;
    _currentSearchQuery = null;
    notifyListeners();
  }

  // Load products by category
  Future<void> loadProductsByCategory(String category, {bool refresh = false}) async {
    await loadProducts(
      category: category,
      refresh: refresh,
    );
  }

  // Sort products
  Future<void> sortProducts(String sortBy, {String sortOrder = 'asc'}) async {
    await loadProducts(
      category: _currentCategory,
      search: _currentSearchQuery,
      sortBy: sortBy,
      sortOrder: sortOrder,
      refresh: true,
    );
  }

  // Clear errors
  void clearErrors() {
    _error = null;
    _searchError = null;
    _productError = null;
    notifyListeners();
  }

  // Clear selected product
  void clearSelectedProduct() {
    _selectedProduct = null;
    _productError = null;
    notifyListeners();
  }

  // Check if product exists in products list
  bool hasProduct(int productId) {
    return _products.any((product) => product.id == productId) ||
           _featuredProducts.any((product) => product.id == productId) ||
           _searchResults.any((product) => product.id == productId);
  }

  // Get product by ID from any list
  Product? getProductById(int productId) {
    for (final list in [_products, _featuredProducts, _searchResults]) {
      for (final p in list) {
        if (p.id == productId) return p;
      }
    }
    if (_selectedProduct?.id == productId) return _selectedProduct;
    return null;
  }

  // Update product in all lists
  void updateProduct(Product updatedProduct) {
    _updateProductInList(_products, updatedProduct);
    _updateProductInList(_featuredProducts, updatedProduct);
    _updateProductInList(_searchResults, updatedProduct);

    if (_selectedProduct?.id == updatedProduct.id) {
      _selectedProduct = updatedProduct;
    }

    notifyListeners();
  }

  void _updateProductInList(List<Product> list, Product updatedProduct) {
    final index = list.indexWhere((product) => product.id == updatedProduct.id);
    if (index != -1) {
      list[index] = updatedProduct;
    }
  }
}
