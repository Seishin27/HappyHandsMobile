import 'package:flutter/foundation.dart';
import 'dart:developer' as developer;

import '../models/cart_item.dart';
import '../models/product.dart';
import '../services/flask_api_service.dart';

class CartProvider extends ChangeNotifier {
  FlaskApiService? _apiService;

  void bindApi(FlaskApiService api) {
    _apiService = api;
  }

  bool get _hasApi => _apiService != null;

  List<CartItem> _cartItems = [];
  bool _isLoading = false;
  bool _isUpdating = false;
  String? _error;

  // Getters
  List<CartItem> get cartItems => List.unmodifiable(_cartItems);
  bool get isLoading => _isLoading;
  bool get isUpdating => _isUpdating;
  String? get error => _error;

  int get itemCount => _cartItems.fold(0, (sum, item) => sum + item.quantity);
  double get subtotal => _cartItems.fold(0.0, (sum, item) => sum + item.subtotal);
  double get shippingCost => 0.0;
  double get total => subtotal + shippingCost;
  bool get isEmpty => _cartItems.isEmpty;
  bool get isNotEmpty => _cartItems.isNotEmpty;

  // Tracks the last token used to load cart — prevents duplicate loads
  String? _lastLoadedToken;

  // Called by main.dart's ChangeNotifierProxyProvider2 whenever AuthProvider
  // changes. Automatically loads cart on login/session-restore, clears on logout.
  void onAuthChanged({String? token, bool isLoading = false}) {
    if (isLoading) return; // session restore still in progress — wait
    if (token == null) {
      clearLocalCart();
      _lastLoadedToken = null;
      return;
    }
    if (token != _lastLoadedToken) {
      _lastLoadedToken = token;
      loadCart(token); // fire-and-forget
    }
  }

  // Load cart from API. The `authToken` argument is kept for back-compat with
  // older call sites; FlaskApiService obtains the JWT from AuthProvider itself.
  Future<void> loadCart(String? authToken) async {
    if (authToken == null || authToken.isEmpty || !_hasApi) {
      notifyListeners();
      return;
    }

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final cartItems = await _apiService!.fetchCart();
      _cartItems = cartItems;
      developer.log('Loaded ${cartItems.length} items in cart');
    } catch (e) {
      developer.log('Cart API unavailable, keeping local cart: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  static const String loginRequiredError =
      'Please log in to add items to your cart.';

  /// True when the most recent failed cart action was due to the user not
  /// being logged in. Calling sites can use this to show a "Login" prompt
  /// instead of a generic error.
  bool _loginRequired = false;
  bool get loginRequired => _loginRequired;

  // Add item to cart
  Future<bool> addToCart({
    required Product product,
    required int quantity,
    String? size,
    String? color,
    String? authToken,
  }) async {
    // Auth gate — non-logged-in users cannot add to cart.
    if (authToken == null || authToken.isEmpty) {
      _error = loginRequiredError;
      _loginRequired = true;
      notifyListeners();
      return false;
    }

    if (!_hasApi) {
      _error = 'Cart service unavailable. Please try again.';
      notifyListeners();
      return false;
    }

    _isUpdating = true;
    _error = null;
    _loginRequired = false;

    final existingIndex = _cartItems.indexWhere(
      (item) =>
          item.product.id == product.id &&
          item.size == size &&
          item.color == color,
    );

    // Capture pre-mutation state for rollback on API failure
    CartItem? preMutationItem;
    final int tempId = -(DateTime.now().millisecondsSinceEpoch);

    if (existingIndex != -1) {
      preMutationItem = _cartItems[existingIndex];
      _cartItems[existingIndex] = preMutationItem.copyWith(
        quantity: preMutationItem.quantity + quantity,
        totalPrice: preMutationItem.product.price * (preMutationItem.quantity + quantity),
      );
    } else {
      _cartItems.add(CartItem(
        id: tempId,
        quantity: quantity,
        unitPrice: product.price,
        totalPrice: product.price * quantity,
        product: product,
        size: size,
        color: color,
        addedAt: DateTime.now(),
      ));
    }
    notifyListeners(); // badge / item count updates immediately

    try {
      if (existingIndex != -1) {
        final updated = await _apiService!.updateCartItem(
          cartItemId: preMutationItem!.id,
          quantity: preMutationItem.quantity + quantity,
        );
        final confirmedIndex = _cartItems.indexWhere((i) => i.id == preMutationItem!.id);
        if (confirmedIndex != -1) _cartItems[confirmedIndex] = updated;
      } else {
        final cartItem = await _apiService!.addToCart(
          productId: product.id,
          quantity: quantity,
          size: size,
          color: color,
        );
        final tempIndex = _cartItems.indexWhere((i) => i.id == tempId);
        if (tempIndex != -1) _cartItems[tempIndex] = cartItem;
      }
      developer.log('Added ${product.name} to cart via API');
      return true;
    } catch (e) {
      // Rollback optimistic changes
      if (existingIndex != -1) {
        final rollbackIndex = _cartItems.indexWhere((i) => i.id == preMutationItem!.id);
        if (rollbackIndex != -1) _cartItems[rollbackIndex] = preMutationItem!;
      } else {
        _cartItems.removeWhere((i) => i.id == tempId);
      }
      _error = e.toString();
      developer.log('Cart API error: $e');
      return false;
    } finally {
      _isUpdating = false;
      notifyListeners();
    }
  }

  // Update item quantity
  Future<bool> updateItemQuantity({
    required CartItem cartItem,
    required int quantity,
    String? authToken,
  }) async {
    if (quantity <= 0) {
      return removeFromCart(cartItem: cartItem, authToken: authToken);
    }

    _isUpdating = true;
    _error = null;
    notifyListeners();

    try {
      if (authToken != null && authToken.isNotEmpty && _hasApi) {
        try {
          final updatedItem = await _apiService!.updateCartItem(
            cartItemId: cartItem.id,
            quantity: quantity,
          );
          final index = _cartItems.indexWhere((item) => item.id == cartItem.id);
          if (index != -1) _cartItems[index] = updatedItem;
          return true;
        } catch (_) {}
      }

      // Local fallback
      final index = _cartItems.indexWhere((item) => item.id == cartItem.id);
      if (index != -1) {
        _cartItems[index] = _cartItems[index].copyWith(
          quantity: quantity,
          totalPrice: _cartItems[index].product.price * quantity,
        );
      }
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    } finally {
      _isUpdating = false;
      notifyListeners();
    }
  }

  // Remove item from cart
  Future<bool> removeFromCart({
    required CartItem cartItem,
    String? authToken,
  }) async {
    _isUpdating = true;
    _error = null;
    notifyListeners();

    try {
      if (authToken != null && authToken.isNotEmpty && _hasApi) {
        await _apiService!.removeFromCart(cartItem.id);
      }
      _cartItems.removeWhere((item) => item.id == cartItem.id);
      developer.log('Removed ${cartItem.product.name} from cart');
      return true;
    } catch (e) {
      _error = e.toString();
      developer.log('Cart remove API error: $e');
      return false;
    } finally {
      _isUpdating = false;
      notifyListeners();
    }
  }

  // Clear entire cart
  Future<bool> clearCart(String? authToken) async {
    _isUpdating = true;
    _error = null;
    notifyListeners();

    try {
      if (authToken != null && authToken.isNotEmpty && _hasApi) {
        try {
          await _apiService!.clearCart();
        } catch (_) {}
      }
      _cartItems.clear();
      developer.log('Cleared cart');
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    } finally {
      _isUpdating = false;
      notifyListeners();
    }
  }

  CartItem? getCartItem({
    required int productId,
    String? size,
    String? color,
  }) {
    try {
      return _cartItems.firstWhere(
        (item) =>
            item.product.id == productId &&
            item.size == size &&
            item.color == color,
      );
    } catch (_) {
      return null;
    }
  }

  int getProductQuantity({required int productId, String? size, String? color}) {
    return getCartItem(productId: productId, size: size, color: color)?.quantity ?? 0;
  }

  bool isProductInCart({required int productId, String? size, String? color}) {
    return getCartItem(productId: productId, size: size, color: color) != null;
  }

  Future<bool> incrementQuantity({
    required CartItem cartItem,
    String? authToken,
  }) async {
    return updateItemQuantity(
      cartItem: cartItem,
      quantity: cartItem.quantity + 1,
      authToken: authToken,
    );
  }

  Future<bool> decrementQuantity({
    required CartItem cartItem,
    String? authToken,
  }) async {
    if (cartItem.quantity <= 1) {
      return removeFromCart(cartItem: cartItem, authToken: authToken);
    }
    return updateItemQuantity(
      cartItem: cartItem,
      quantity: cartItem.quantity - 1,
      authToken: authToken,
    );
  }

  void clearErrors() {
    _error = null;
    _loginRequired = false;
    notifyListeners();
  }

  void clearLocalCart() {
    _cartItems.clear();
    _error = null;
    notifyListeners();
  }

  Map<String, dynamic> getCartSummary() {
    return {
      'itemCount': itemCount,
      'subtotal': subtotal,
      'shippingCost': shippingCost,
      'total': total,
      'isEmpty': isEmpty,
      'items': cartItems
          .map((item) => {
                'id': item.id,
                'productId': item.product.id,
                'name': item.product.name,
                'price': item.product.price,
                'quantity': item.quantity,
                'subtotal': item.subtotal,
                'size': item.size,
                'color': item.color,
                'imageUrl': item.product.imageUrl,
              })
          .toList(),
    };
  }
}
