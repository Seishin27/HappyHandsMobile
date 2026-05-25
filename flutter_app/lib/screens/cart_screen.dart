import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../providers/cart_provider.dart';
import '../widgets/loading_widget.dart';
import '../widgets/custom_app_bar.dart';
import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';
import '../core/config/app_config.dart';
import '../models/cart_item.dart';
import '../screens/checkout_screen.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  // IDs of cart items the user has checked for checkout
  final Set<int> _selectedIds = {};
  bool _initialized = false;

  // Resolve relative image paths to full URLs
  String _imageUrl(String? raw) {
    if (raw == null || raw.isEmpty) return '';
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    final clean = raw.startsWith('/') ? raw.substring(1) : raw;
    return '${AppConfig.uploadsBaseUrl}/$clean';
  }

  void _initSelection(List<CartItem> items) {
    if (_initialized) return;
    _initialized = true;
    _selectedIds.addAll(items.map((e) => e.id));
  }

  bool get _allSelected => _selectedIds.isNotEmpty &&
      _selectedIds.containsAll(_currentItems.map((e) => e.id));

  List<CartItem> _currentItems = [];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: CustomAppBar(
        title: 'Shopping Cart',
        onCartTap: () => Navigator.pop(context),
        onProfileTap: () => _navigateToProfile(),
      ),
      body: Consumer<CartProvider>(
        builder: (context, cartProvider, child) {
          if (cartProvider.isLoading) {
            return const LoadingWidget();
          }

          if (cartProvider.error != null) {
            return _buildErrorWidget(cartProvider.error!);
          }

          if (cartProvider.isEmpty) {
            return _buildEmptyCart();
          }

          _currentItems = cartProvider.cartItems.toList();
          _initSelection(_currentItems);

          // Keep _selectedIds in sync — remove IDs no longer in cart
          _selectedIds.removeWhere(
            (id) => !_currentItems.any((e) => e.id == id),
          );

          return _buildCartContent(cartProvider);
        },
      ),
    );
  }

  Widget _buildEmptyCart() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(FontAwesomeIcons.cartShopping, size: 64, color: AppTheme.mediumGray),
            const SizedBox(height: AppConstants.spacingMD),
            Text(
              'Your cart is empty',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                color: AppTheme.darkBlue,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppConstants.spacingSM),
            Text(
              'Add some products to your cart to get started.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppTheme.mediumGray),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppConstants.spacingXL),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryBlue,
                foregroundColor: AppTheme.white,
                padding: const EdgeInsets.symmetric(
                  horizontal: AppConstants.spacingXL,
                  vertical: AppConstants.spacingMD,
                ),
              ),
              child: const Text('Continue Shopping'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorWidget(String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(FontAwesomeIcons.triangleExclamation, size: 64, color: AppTheme.errorRed),
            const SizedBox(height: AppConstants.spacingMD),
            Text(
              'Error loading cart',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: AppTheme.errorRed),
            ),
            const SizedBox(height: AppConstants.spacingSM),
            Text(
              error,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mediumGray),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppConstants.spacingLG),
            ElevatedButton(
              onPressed: () => context.read<CartProvider>().loadCart(null),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryBlue,
                foregroundColor: AppTheme.white,
              ),
              child: const Text('Try Again'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCartContent(CartProvider cartProvider) {
    final selected = _currentItems.where((e) => _selectedIds.contains(e.id)).toList();
    final selectedSubtotal = selected.fold(0.0, (s, e) => s + e.subtotal);
    final selectedQty = selected.fold(0, (s, e) => s + e.quantity);
    final selectedShipping = selectedQty > 0 ? 36.0 : 0.0; // minimum ₱36 shipping
    final selectedTotal = selectedSubtotal + selectedShipping;

    return Column(
      children: [
        // Select-all bar
        Container(
          color: AppTheme.lightGray,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: Row(
            children: [
              Checkbox(
                value: _allSelected,
                activeColor: AppTheme.primaryBlue,
                onChanged: (v) {
                  setState(() {
                    if (v == true) {
                      _selectedIds.addAll(_currentItems.map((e) => e.id));
                    } else {
                      _selectedIds.clear();
                    }
                  });
                },
              ),
              const Text(
                'Select All',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.darkBlue),
              ),
              const Spacer(),
              Text(
                '${_selectedIds.length} of ${_currentItems.length} selected',
                style: const TextStyle(fontSize: 12, color: AppTheme.mediumGray),
              ),
            ],
          ),
        ),

        // Cart Items
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(AppConstants.spacingMD),
            itemCount: _currentItems.length,
            itemBuilder: (context, index) {
              final cartItem = _currentItems[index];
              return _buildCartItem(cartItem, cartProvider);
            },
          ),
        ),

        // Cart Summary and Checkout
        _buildCartSummary(
          cartProvider: cartProvider,
          selectedItems: selected,
          selectedSubtotal: selectedSubtotal,
          selectedQty: selectedQty,
          selectedShipping: selectedShipping,
          selectedTotal: selectedTotal,
        ),
      ],
    );
  }

  Widget _buildCartItem(CartItem cartItem, CartProvider cartProvider) {
    final isChecked = _selectedIds.contains(cartItem.id);
    final rawUrl = cartItem.product.imageUrl ??
        (cartItem.product.imageUrls.isNotEmpty ? cartItem.product.imageUrls.first : null);
    final imgUrl = _imageUrl(rawUrl);

    return Container(
      margin: const EdgeInsets.only(bottom: AppConstants.spacingMD),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(AppConstants.radiusMD),
        border: Border.all(
          color: isChecked
              ? AppTheme.primaryBlue.withValues(alpha: 0.35)
              : AppTheme.borderGray.withValues(alpha: 0.3),
          width: isChecked ? 1.5 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Checkbox
          Checkbox(
            value: isChecked,
            activeColor: AppTheme.primaryBlue,
            onChanged: (v) {
              setState(() {
                if (v == true) {
                  _selectedIds.add(cartItem.id);
                } else {
                  _selectedIds.remove(cartItem.id);
                }
              });
            },
          ),

          // Product Image
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppConstants.radiusMD),
              border: Border.all(color: AppTheme.borderGray.withValues(alpha: 0.3)),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(AppConstants.radiusMD),
              child: imgUrl.isEmpty
                  ? Container(
                      color: AppTheme.lightGray,
                      child: const Icon(FontAwesomeIcons.image, color: AppTheme.mediumGray, size: 24),
                    )
                  : CachedNetworkImage(
                      imageUrl: imgUrl,
                      fit: BoxFit.cover,
                      placeholder: (context, url) => Container(
                        color: AppTheme.lightGray,
                        child: const Center(
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primaryBlue),
                          ),
                        ),
                      ),
                      errorWidget: (context, url, error) => Container(
                        color: AppTheme.lightGray,
                        child: const Icon(FontAwesomeIcons.image, color: AppTheme.mediumGray, size: 24),
                      ),
                    ),
            ),
          ),

          const SizedBox(width: 10),

          // Product Info
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    cartItem.product.name,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppTheme.darkBlue,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (cartItem.size != null || cartItem.color != null) ...[
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        if (cartItem.size != null)
                          _VariantChip('Size: ${cartItem.size}'),
                        if (cartItem.size != null && cartItem.color != null)
                          const SizedBox(width: 4),
                        if (cartItem.color != null)
                          _VariantChip('Color: ${cartItem.color}'),
                      ],
                    ),
                  ],
                  const SizedBox(height: 4),
                  Text(
                    '₱${cartItem.product.price.toStringAsFixed(2)}',
                    style: const TextStyle(
                      color: AppTheme.primaryBlue,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Quantity Controls and Remove
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Remove Button
                GestureDetector(
                  onTap: cartProvider.isUpdating
                      ? null
                      : () => _removeFromCart(cartItem, cartProvider),
                  child: const Icon(FontAwesomeIcons.trash, color: AppTheme.errorRed, size: 14),
                ),

                const SizedBox(height: 8),

                // Quantity Controls
                Container(
                  decoration: BoxDecoration(
                    border: Border.all(color: AppTheme.borderGray),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _QtyButton(
                        icon: Icons.remove,
                        onTap: cartProvider.isUpdating
                            ? null
                            : () => _decrementQuantity(cartItem, cartProvider),
                      ),
                      Container(
                        width: 32,
                        height: 28,
                        alignment: Alignment.center,
                        child: Text(
                          '${cartItem.quantity}',
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppTheme.darkBlue,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      _QtyButton(
                        icon: Icons.add,
                        onTap: cartProvider.isUpdating
                            ? null
                            : () => _incrementQuantity(cartItem, cartProvider),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCartSummary({
    required CartProvider cartProvider,
    required List<CartItem> selectedItems,
    required double selectedSubtotal,
    required int selectedQty,
    required double selectedShipping,
    required double selectedTotal,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppConstants.spacingLG),
      decoration: BoxDecoration(
        color: AppTheme.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 8,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Subtotal ($selectedQty item${selectedQty == 1 ? '' : 's'})',
                style: Theme.of(context)
                    .textTheme
                    .bodyLarge
                    ?.copyWith(color: AppTheme.mediumGray),
              ),
              Text(
                '₱${selectedSubtotal.toStringAsFixed(2)}',
                style: Theme.of(context)
                    .textTheme
                    .bodyLarge
                    ?.copyWith(color: AppTheme.darkBlue, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: AppConstants.spacingSM),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Shipping',
                  style: Theme.of(context)
                      .textTheme
                      .bodyLarge
                      ?.copyWith(color: AppTheme.mediumGray)),
              Text(
                '₱${selectedShipping.toStringAsFixed(2)}',
                style: Theme.of(context)
                    .textTheme
                    .bodyLarge
                    ?.copyWith(color: AppTheme.darkBlue, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const Divider(height: AppConstants.spacingLG),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Total',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: AppTheme.darkBlue, fontWeight: FontWeight.w700)),
              Text(
                '₱${selectedTotal.toStringAsFixed(2)}',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: AppTheme.primaryBlue, fontWeight: FontWeight.w800),
              ),
            ],
          ),
          const SizedBox(height: AppConstants.spacingLG),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: (cartProvider.isUpdating || selectedItems.isEmpty)
                  ? null
                  : () => _proceedToCheckout(selectedItems),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryBlue,
                foregroundColor: AppTheme.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppConstants.radiusLG),
                ),
              ),
              child: cartProvider.isUpdating
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(AppTheme.white),
                      ),
                    )
                  : Text(
                      selectedItems.isEmpty
                          ? 'Select items to checkout'
                          : 'Checkout (${selectedItems.length} item${selectedItems.length == 1 ? '' : 's'})',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _incrementQuantity(CartItem cartItem, CartProvider cartProvider) async {
    await cartProvider.incrementQuantity(cartItem: cartItem);
  }

  Future<void> _decrementQuantity(CartItem cartItem, CartProvider cartProvider) async {
    await cartProvider.decrementQuantity(cartItem: cartItem);
  }

  Future<void> _removeFromCart(CartItem cartItem, CartProvider cartProvider) async {
    final shouldRemove = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Item'),
        content: Text(
            'Remove ${cartItem.product.name} from your cart?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Remove', style: TextStyle(color: AppTheme.errorRed)),
          ),
        ],
      ),
    );

    if (shouldRemove == true) {
      if (!mounted) return;
      _selectedIds.remove(cartItem.id);
      await cartProvider.removeFromCart(cartItem: cartItem);
    }
  }

  void _proceedToCheckout(List<CartItem> selectedItems) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CheckoutScreen(selectedItems: selectedItems),
      ),
    );
  }

  void _navigateToProfile() {
    Navigator.pushNamed(context, '/auth');
  }
}

// ── Small reusable widgets ─────────────────────────────────────────────────

class _VariantChip extends StatelessWidget {
  final String label;
  const _VariantChip(this.label);

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: AppTheme.lightGray,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(label,
            style: const TextStyle(fontSize: 10, color: AppTheme.mediumGray)),
      );
}

class _QtyButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  const _QtyButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: SizedBox(
          width: 28,
          height: 28,
          child: Icon(icon, size: 14,
              color: onTap == null ? AppTheme.borderGray : AppTheme.darkBlue),
        ),
      );
}
