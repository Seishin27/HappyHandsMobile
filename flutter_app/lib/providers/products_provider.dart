import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'dart:developer' as developer;

import '../models/product.dart';
import '../models/seller_product.dart';
import '../services/flask_api_service.dart';

class ProductsProvider extends ChangeNotifier {
  final FlaskApiService _apiService;

  ProductsProvider(this._apiService);

  bool _isLoading = false;
  String? _error;
  List<Product> _items = const [];
  List<SellerProduct> _sellerProducts = const [];
  List<Map<String, dynamic>> _sellerCategories = const [];

  bool get isLoading => _isLoading;
  String? get error => _error;
  List<Product> get items => _items;
  List<SellerProduct> get sellerProducts => _sellerProducts;
  List<Map<String, dynamic>> get sellerCategories => _sellerCategories;

  Future<void> fetch({int page = 1, int pageSize = 20}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _items = await _apiService.fetchProducts(page: page, pageSize: pageSize);
      developer.log('Loaded ${_items.length} products from Flask/MySQL.');
    } catch (e) {
      _error = 'Failed to load products: $e';
      developer.log('Error in ProductsProvider: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetches seller-specific products from the API.
  ///
  /// Parameters:
  /// - [page]: Page number for pagination (default: 1)
  /// - [pageSize]: Number of items per page (default: 20)
  ///
  /// Updates [_sellerProducts] with the fetched data and manages loading/error states.
  /// Calls [notifyListeners] to update UI.
  ///
  /// Requirements: 3.1
  Future<void> fetchSellerProducts({int page = 1, int pageSize = 20}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _sellerProducts = await _apiService.fetchSellerProducts(
        page: page,
        pageSize: pageSize,
      );
      developer.log('Loaded ${_sellerProducts.length} seller products.');
    } catch (e) {
      _error = 'Failed to load seller products: $e';
      developer.log('Error in ProductsProvider.fetchSellerProducts: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetches the categories allowed for the logged-in seller.
  Future<void> fetchSellerCategories() async {
    try {
      _sellerCategories = await _apiService.fetchSellerCategories();
      developer.log('Loaded ${_sellerCategories.length} seller categories.');
      notifyListeners();
    } catch (e) {
      developer.log('Error in ProductsProvider.fetchSellerCategories: $e');
    }
  }

  /// Creates a new product with optional images.
  ///
  /// Parameters:
  /// - [product]: SellerProduct object with product details
  /// - [images]: Optional list of image files to upload
  ///
  /// Adds the created product to [_sellerProducts] and manages loading/error states.
  /// Calls [notifyListeners] to update UI.
  ///
  /// Requirements: 3.7, 3.10
  Future<void> createProduct(
    SellerProduct product,
    List<PlatformFile>? images,
  ) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final createdProduct = await _apiService.createProduct(product, images);
      // Add the new product to the local list
      _sellerProducts = [..._sellerProducts, createdProduct];
      developer.log('Created product: ${createdProduct.name} (ID: ${createdProduct.id})');
    } catch (e) {
      _error = 'Failed to create product: $e';
      developer.log('Error in ProductsProvider.createProduct: $e');
      rethrow; // Re-throw to allow UI to handle specific error cases
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Updates an existing product with optional new images.
  ///
  /// Parameters:
  /// - [id]: Product ID to update
  /// - [product]: SellerProduct object with updated details
  /// - [images]: Optional list of new image files to upload
  ///
  /// Updates the product in [_sellerProducts] and manages loading/error states.
  /// Calls [notifyListeners] to update UI.
  ///
  /// Requirements: 3.7, 3.9
  Future<void> updateProduct(
    String id,
    SellerProduct product,
    List<PlatformFile>? images,
  ) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final updatedProduct = await _apiService.updateProduct(id, product, images);
      // Update the product in the local list
      _sellerProducts = _sellerProducts.map((p) {
        return p.id.toString() == id ? updatedProduct : p;
      }).toList();
      developer.log('Updated product: ${updatedProduct.name} (ID: ${updatedProduct.id})');
    } catch (e) {
      _error = 'Failed to update product: $e';
      developer.log('Error in ProductsProvider.updateProduct: $e');
      rethrow; // Re-throw to allow UI to handle specific error cases
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Deletes a product.
  ///
  /// Parameters:
  /// - [id]: Product ID to delete
  ///
  /// Removes the product from [_sellerProducts] and manages loading/error states.
  /// Calls [notifyListeners] to update UI.
  ///
  /// Requirements: 3.11
  Future<void> deleteProduct(String id) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      await _apiService.deleteProduct(id);
      // Remove the product from the local list
      _sellerProducts = _sellerProducts.where((p) {
        return p.id.toString() != id;
      }).toList();
      developer.log('Deleted product with ID: $id');
    } catch (e) {
      _error = 'Failed to delete product: $e';
      developer.log('Error in ProductsProvider.deleteProduct: $e');
      rethrow; // Re-throw to allow UI to handle specific error cases
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
