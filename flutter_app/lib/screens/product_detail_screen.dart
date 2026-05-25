import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../providers/product_provider.dart';
import '../providers/cart_provider.dart';
import '../providers/auth_provider.dart';
import '../widgets/loading_widget.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/product_card.dart';
import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';
import '../core/config/app_config.dart';
import '../models/product.dart';
import 'auth_screen.dart';
import 'cart_screen.dart';

class ProductDetailScreen extends StatefulWidget {
  final int productId;

  const ProductDetailScreen({super.key, required this.productId});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  final PageController _pageController = PageController();
  int _currentImageIndex = 0;
  int _selectedQuantity = 1;
  bool _isAddingToCart = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProductProvider>().loadProductById(widget.productId);
    });
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: CustomAppBar(
        title: 'Product Details',
        showBackButton: false,
        onCartTap: _navigateToCart,
        onProfileTap: _navigateToProfile,
      ),
      body: Consumer<ProductProvider>(
        builder: (context, productProvider, child) {
          final product = productProvider.selectedProduct;

          if (productProvider.isLoadingProduct) {
            return const LoadingWidget();
          }

          if (productProvider.productError != null) {
            return _buildErrorWidget(productProvider.productError!);
          }

          if (product == null) {
            return _buildEmptyWidget();
          }

          return _buildProductDetails(product);
        },
      ),
    );
  }

  Widget _buildProductDetails(Product product) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Back-link breadcrumb ────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppConstants.spacingLG,
              AppConstants.spacingSM,
              AppConstants.spacingLG,
              0,
            ),
            child: GestureDetector(
              onTap: () => Navigator.maybePop(context),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.arrow_back,
                    size: 16,
                    color: AppTheme.primaryBlue,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'Back to Shop',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppTheme.primaryBlue,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ],
              ),
            ),
          ),

          // ── Image gallery (main + thumbnails) ───────────────────────────────
          _buildProductImages(product),

          // ── Product info ────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.all(AppConstants.spacingMD),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildProductHeader(product),
                const SizedBox(height: AppConstants.spacingMD),
                _buildQuantitySelector(product),
                const SizedBox(height: AppConstants.spacingMD),
                _buildActionButtons(product),
                const SizedBox(height: AppConstants.spacingLG),
                _buildProductDescription(product),
                const SizedBox(height: AppConstants.spacingLG),
                _buildRelatedProducts(product),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── Image gallery ─────────────────────────────────────────────────────────
  Widget _buildProductImages(Product product) {
    final images = product.imageUrls;
    final hasMultiple = images.length > 1;

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppConstants.spacingMD,
        AppConstants.spacingSM,
        AppConstants.spacingMD,
        0,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Main image stage
          Container(
            height: MediaQuery.of(context).size.height * 0.35,
            constraints: const BoxConstraints(minHeight: 200, maxHeight: 320),
            decoration: BoxDecoration(
              color: AppTheme.lightGray,
              borderRadius: BorderRadius.circular(AppConstants.radiusLG),
              border: Border.all(
                color: AppTheme.borderGray.withValues(alpha: 0.5),
              ),
            ),
            clipBehavior: Clip.antiAlias,
            child: PageView.builder(
              controller: _pageController,
              onPageChanged: (index) =>
                  setState(() => _currentImageIndex = index),
              itemCount: images.isNotEmpty ? images.length : 1,
              itemBuilder: (context, index) {
                if (images.isEmpty) return _buildImagePlaceholder();
                return _buildNetworkImage(images[index], BoxFit.contain);
              },
            ),
          ),

          // Thumbnail strip — visible whenever there's at least one image
          if (images.isNotEmpty) ...[
            const SizedBox(height: AppConstants.spacingMD),
            SizedBox(
              height: 64,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: images.length,
                separatorBuilder: (_, __) =>
                    const SizedBox(width: AppConstants.spacingSM),
                itemBuilder: (context, index) {
                  final isActive = _currentImageIndex == index;
                  return GestureDetector(
                    onTap: () {
                      _pageController.animateToPage(
                        index,
                        duration: const Duration(milliseconds: 220),
                        curve: Curves.easeOut,
                      );
                    },
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      width: 64,
                      decoration: BoxDecoration(
                        color: AppTheme.lightGray,
                        borderRadius:
                            BorderRadius.circular(AppConstants.radiusMD),
                        border: Border.all(
                          color: isActive
                              ? AppTheme.primaryBlue
                              : AppTheme.borderGray.withValues(alpha: 0.5),
                          width: isActive ? 2 : 1,
                        ),
                      ),
                      clipBehavior: Clip.antiAlias,
                      child: _buildNetworkImage(images[index], BoxFit.cover),
                    ),
                  );
                },
              ),
            ),
            if (hasMultiple) ...[
              const SizedBox(height: 6),
              Center(
                child: Text(
                  '${_currentImageIndex + 1} / ${images.length}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppTheme.mediumGray,
                  ),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildNetworkImage(String imageUrl, BoxFit fit) {
    final fullUrl = imageUrl.startsWith('http')
        ? imageUrl
        : '${AppConfig.uploadsBaseUrl}/$imageUrl';
    return CachedNetworkImage(
      imageUrl: fullUrl,
      fit: fit,
      placeholder: (context, url) => Container(
        color: AppTheme.lightGray,
        child: const Center(
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primaryBlue),
          ),
        ),
      ),
      errorWidget: (context, url, error) => _buildImagePlaceholder(),
    );
  }

  Widget _buildImagePlaceholder() {
    return Container(
      color: AppTheme.lightGray,
      child: const Center(
        child: Icon(
          FontAwesomeIcons.image,
          size: 40,
          color: AppTheme.mediumGray,
        ),
      ),
    );
  }

  // ── Header (name + price + stock badge + rating) ─────────────────────────
  Widget _buildProductHeader(Product product) {
    final stock = product.stock ?? 0;
    final inStock = stock > 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          product.name,
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                color: AppTheme.darkBlue,
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: AppConstants.spacingXS),
        Text(
          '₱${product.price.toStringAsFixed(2)}',
          style: Theme.of(context).textTheme.displaySmall?.copyWith(
                color: AppTheme.primaryBlue,
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: AppConstants.spacingMD),
        Wrap(
          spacing: AppConstants.spacingSM,
          runSpacing: AppConstants.spacingSM,
          children: [
            // Stock chip
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppConstants.spacingMD,
                vertical: AppConstants.spacingSM,
              ),
              decoration: BoxDecoration(
                color: inStock
                    ? AppTheme.successGreen.withValues(alpha: 0.1)
                    : AppTheme.errorRed.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppConstants.radiusSM),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    inStock ? FontAwesomeIcons.box : FontAwesomeIcons.boxOpen,
                    size: 14,
                    color: inStock
                        ? AppTheme.successGreen
                        : AppTheme.errorRed,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    inStock ? 'In Stock · $stock left' : 'Out of stock',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: inStock
                          ? AppTheme.successGreen
                          : AppTheme.errorRed,
                    ),
                  ),
                ],
              ),
            ),
            // Rating chip (if available)
            if (product.rating != null)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppConstants.spacingMD,
                  vertical: AppConstants.spacingSM,
                ),
                decoration: BoxDecoration(
                  color: AppTheme.lightGray,
                  borderRadius: BorderRadius.circular(AppConstants.radiusSM),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      FontAwesomeIcons.solidStar,
                      size: 14,
                      color: Colors.amber,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      product.rating!.toStringAsFixed(1),
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.darkBlue,
                      ),
                    ),
                    if (product.reviewCount != null) ...[
                      const SizedBox(width: 4),
                      Text(
                        '(${product.reviewCount})',
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppTheme.mediumGray,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
          ],
        ),
      ],
    );
  }

  // ── Description ──────────────────────────────────────────────────────────
  Widget _buildProductDescription(Product product) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Product Description',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: AppTheme.darkBlue,
                fontWeight: FontWeight.w700,
                fontSize: 16,
              ),
        ),
        const SizedBox(height: AppConstants.spacingSM),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppConstants.spacingMD),
          decoration: BoxDecoration(
            color: AppTheme.lightGray.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(AppConstants.radiusMD),
            border: Border.all(
              color: AppTheme.borderGray.withValues(alpha: 0.4),
            ),
          ),
          child: Text(
            product.description.isEmpty
                ? 'No description available.'
                : product.description,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppTheme.darkBlue,
                  height: 1.55,
                ),
          ),
        ),
      ],
    );
  }

  // ── Quantity selector ────────────────────────────────────────────────────
  Widget _buildQuantitySelector(Product product) {
    final stock = product.stock ?? 0;
    final inStock = stock > 0;
    final maxQuantity = inStock ? stock : 1;
    // Clamp current selection if stock dropped below it.
    if (_selectedQuantity > maxQuantity) {
      _selectedQuantity = maxQuantity;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quantity',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: AppTheme.darkBlue,
                fontWeight: FontWeight.w600,
              ),
        ),
        const SizedBox(height: AppConstants.spacingSM),
        Row(
          children: [
            _qtyButton(
              icon: Icons.remove,
              enabled: inStock && _selectedQuantity > 1,
              onTap: () => setState(() => _selectedQuantity--),
            ),
            Container(
              width: 64,
              height: 40,
              decoration: BoxDecoration(
                border: Border.all(color: AppTheme.borderGray),
                borderRadius: BorderRadius.circular(AppConstants.radiusMD),
              ),
              alignment: Alignment.center,
              child: Text(
                '$_selectedQuantity',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.darkBlue,
                ),
              ),
            ),
            _qtyButton(
              icon: Icons.add,
              enabled: inStock && _selectedQuantity < maxQuantity,
              onTap: () => setState(() => _selectedQuantity++),
            ),
          ],
        ),
      ],
    );
  }

  Widget _qtyButton({
    required IconData icon,
    required bool enabled,
    required VoidCallback onTap,
  }) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Material(
        color: enabled ? AppTheme.white : AppTheme.lightGray,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: AppTheme.borderGray),
          borderRadius: BorderRadius.circular(AppConstants.radiusMD),
        ),
        child: InkWell(
          onTap: enabled ? onTap : null,
          borderRadius: BorderRadius.circular(AppConstants.radiusMD),
          child: SizedBox(
            width: 40,
            height: 40,
            child: Icon(
              icon,
              size: 16,
              color: enabled ? AppTheme.darkBlue : AppTheme.mediumGray,
            ),
          ),
        ),
      ),
    );
  }

  // ── Action buttons ───────────────────────────────────────────────────────
  Widget _buildActionButtons(Product product) {
    final stock = product.stock ?? 0;
    final inStock = stock > 0;
    final isSignedIn = context.watch<AuthProvider>().user != null;

    String primaryLabel;
    IconData primaryIcon;
    if (!inStock) {
      primaryLabel = 'Out of stock';
      primaryIcon = FontAwesomeIcons.boxOpen;
    } else if (!isSignedIn) {
      primaryLabel = 'Login to Add to Cart';
      primaryIcon = FontAwesomeIcons.rightToBracket;
    } else {
      primaryLabel = 'Add to Cart';
      primaryIcon = FontAwesomeIcons.cartShopping;
    }

    return Column(
      children: [
        // Primary CTA
        SizedBox(
          width: double.infinity,
          height: 50,
          child: ElevatedButton(
            onPressed: !inStock || _isAddingToCart
                ? null
                : () => isSignedIn
                    ? _addToCart(product)
                    : _promptLogin(),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryBlue,
              foregroundColor: AppTheme.white,
              disabledBackgroundColor: AppTheme.lightGray,
              disabledForegroundColor: AppTheme.mediumGray,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppConstants.radiusLG),
              ),
            ),
            child: _isAddingToCart
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor:
                          AlwaysStoppedAnimation<Color>(AppTheme.white),
                    ),
                  )
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(primaryIcon, size: 16),
                      const SizedBox(width: AppConstants.spacingSM),
                      Text(
                        primaryLabel,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: AppConstants.spacingMD),
        // Buy Now
        SizedBox(
          width: double.infinity,
          height: 50,
          child: OutlinedButton(
            onPressed: inStock
                ? () => isSignedIn ? _buyNow(product) : _promptLogin()
                : null,
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.primaryBlue,
              side: BorderSide(
                color: inStock
                    ? AppTheme.primaryBlue
                    : AppTheme.borderGray,
                width: 2,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppConstants.radiusLG),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  FontAwesomeIcons.bolt,
                  size: 16,
                  color: inStock
                      ? AppTheme.primaryBlue
                      : AppTheme.mediumGray,
                ),
                const SizedBox(width: AppConstants.spacingSM),
                Text(
                  'Buy Now',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: inStock
                        ? AppTheme.primaryBlue
                        : AppTheme.mediumGray,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // ── You may also like ────────────────────────────────────────────────────
  Widget _buildRelatedProducts(Product product) {
    return Consumer<ProductProvider>(
      builder: (context, productProvider, child) {
        final relatedProducts = productProvider.products
            .where((p) => p.id != product.id)
            .take(4)
            .toList();

        if (relatedProducts.isEmpty) {
          return const SizedBox.shrink();
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'You May Also Like',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: AppTheme.darkBlue,
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                  ),
            ),
            const SizedBox(height: AppConstants.spacingMD),
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisExtent: 270,
                crossAxisSpacing: AppConstants.spacingMD,
                mainAxisSpacing: AppConstants.spacingMD,
              ),
              itemCount: relatedProducts.length,
              itemBuilder: (context, index) {
                final relatedProduct = relatedProducts[index];
                return ProductCard(
                  product: relatedProduct,
                  onTap: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (_) =>
                            ProductDetailScreen(productId: relatedProduct.id),
                      ),
                    );
                  },
                  onAddToCart: () => _addToCart(relatedProduct),
                );
              },
            ),
          ],
        );
      },
    );
  }

  // ── Error / empty states ─────────────────────────────────────────────────
  Widget _buildErrorWidget(String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              FontAwesomeIcons.triangleExclamation,
              size: 64,
              color: AppTheme.errorRed,
            ),
            const SizedBox(height: AppConstants.spacingMD),
            Text(
              'Error loading product',
              style: Theme.of(context)
                  .textTheme
                  .headlineMedium
                  ?.copyWith(color: AppTheme.errorRed),
            ),
            const SizedBox(height: AppConstants.spacingSM),
            Text(
              error,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: AppTheme.mediumGray),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppConstants.spacingLG),
            ElevatedButton(
              onPressed: () {
                context
                    .read<ProductProvider>()
                    .loadProductById(widget.productId);
              },
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

  Widget _buildEmptyWidget() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              FontAwesomeIcons.boxOpen,
              size: 64,
              color: AppTheme.mediumGray,
            ),
            const SizedBox(height: AppConstants.spacingMD),
            Text(
              'Product not found',
              style: Theme.of(context)
                  .textTheme
                  .headlineMedium
                  ?.copyWith(color: AppTheme.mediumGray),
            ),
            const SizedBox(height: AppConstants.spacingSM),
            Text(
              'The product you are looking for does not exist.',
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: AppTheme.mediumGray),
            ),
          ],
        ),
      ),
    );
  }

  // ── Actions ──────────────────────────────────────────────────────────────
  Future<void> _addToCart(Product product) async {
    setState(() => _isAddingToCart = true);

    try {
      final authProvider = context.read<AuthProvider>();
      final cartProvider = context.read<CartProvider>();
      final success = await cartProvider.addToCart(
        product: product,
        quantity: _selectedQuantity,
        authToken: authProvider.backendAccessToken,
      );

      if (!mounted) return;

      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(AppConstants.successAddedToCart),
            backgroundColor: AppTheme.successGreen,
            duration: Duration(seconds: 2),
          ),
        );
      } else if (cartProvider.loginRequired) {
        _promptLogin();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(cartProvider.error ?? AppConstants.errorGeneral),
            backgroundColor: AppTheme.errorRed,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isAddingToCart = false);
    }
  }

  void _buyNow(Product product) {
    _addToCart(product).then((_) {
      if (!mounted) return;
      Navigator.pushNamed(context, '/checkout');
    });
  }

  void _promptLogin() {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Please log in to add items to your cart.'),
        backgroundColor: AppTheme.darkBlue,
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: 'Log in',
          textColor: AppTheme.white,
          onPressed: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const AuthScreen()),
            );
          },
        ),
      ),
    );
  }

  void _navigateToCart() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const CartScreen()),
    );
  }

  void _navigateToProfile() {
    final authProvider = context.read<AuthProvider>();
    if (authProvider.user == null) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const AuthScreen()),
      );
    }
  }
}
