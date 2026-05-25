import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/money.dart';
import '../../providers/products_provider.dart';
import '../../widgets/cross_platform_image.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';
import 'product_edit_screen.dart';

/// Products tab screen for seller dashboard.
///
/// Displays a paginated list of seller products with name, price, and thumbnail.
/// Includes a floating action button for creating new products and navigation
/// to product edit screen on tap.
///
/// Requirements: 3.1, 3.2, 3.3, 3.4, 3.11, 3.12
class ProductsTab extends StatefulWidget {
  const ProductsTab({super.key});

  @override
  State<ProductsTab> createState() => _ProductsTabState();
}

class _ProductsTabState extends State<ProductsTab> {
  @override
  void initState() {
    super.initState();
    // Fetch seller products on initial load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProductsProvider>().fetchSellerProducts();
    });
  }

  Future<void> _onRefresh() async {
    await context.read<ProductsProvider>().fetchSellerProducts();
  }

  void _navigateToCreateProduct() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const ProductEditScreen(productId: null),
      ),
    );
    // Refresh product list after returning from create/edit screen
    if (mounted) {
      context.read<ProductsProvider>().fetchSellerProducts();
    }
  }

  void _navigateToEditProduct(String productId) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ProductEditScreen(productId: productId),
      ),
    );
    // Refresh product list after returning from edit screen
    if (mounted) {
      context.read<ProductsProvider>().fetchSellerProducts();
    }
  }

  @override
  Widget build(BuildContext context) {
    final productsProvider = context.watch<ProductsProvider>();

    // Show loading indicator while fetching data
    if (productsProvider.isLoading && productsProvider.sellerProducts.isEmpty) {
      return const LoadingWidget(label: 'Loading products...');
    }

    // Show error message with retry button on failure
    if (productsProvider.error != null && productsProvider.sellerProducts.isEmpty) {
      return ErrorView(
        message: productsProvider.error!,
        onRetry: () => context.read<ProductsProvider>().fetchSellerProducts(),
      );
    }

    // Main products list with pull-to-refresh
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        child: productsProvider.sellerProducts.isEmpty
            ? _buildEmptyState()
            : _buildProductsList(productsProvider),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _navigateToCreateProduct,
        tooltip: 'Add Product',
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildEmptyState() {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 48),
        Icon(Icons.inventory_2_outlined, size: 80, color: Colors.grey[400]),
        const SizedBox(height: 16),
        Text(
          'No products yet',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Colors.grey[700],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Start adding products to your store',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 14,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }

  Widget _buildProductsList(ProductsProvider productsProvider) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: productsProvider.sellerProducts.length,
      itemBuilder: (context, index) {
        final product = productsProvider.sellerProducts[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: InkWell(
            onTap: () => _navigateToEditProduct(product.id.toString()),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Product thumbnail
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: product.images.isNotEmpty
                        ? CrossPlatformNetworkImage(
                            imageUrl: product.images.first,
                            width: 80,
                            height: 80,
                            fit: BoxFit.cover,
                            placeholder: Container(
                              width: 80,
                              height: 80,
                              color: Colors.grey[200],
                              child: const Center(
                                child: SizedBox(
                                  width: 24,
                                  height: 24,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                ),
                              ),
                            ),
                            errorWidget: _buildPlaceholderImage(),
                          )
                        : _buildPlaceholderImage(),
                  ),
                  const SizedBox(width: 12),
                  // Product details
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          product.name,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          product.category,
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Text(
                              formatMoney(product.price),
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: Colors.green,
                              ),
                            ),
                            const Spacer(),
                            _buildStockBadge(product.stockQuantity),
                          ],
                        ),
                      ],
                    ),
                  ),
                  // Edit icon
                  const SizedBox(width: 8),
                  Icon(
                    Icons.chevron_right,
                    color: Colors.grey[400],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildPlaceholderImage() {
    return Container(
      width: 80,
      height: 80,
      color: Colors.grey[200],
      child: Icon(
        Icons.image_outlined,
        size: 40,
        color: Colors.grey[400],
      ),
    );
  }

  Widget _buildStockBadge(int stockQuantity) {
    final isLowStock = stockQuantity < 10;
    final isOutOfStock = stockQuantity == 0;

    Color badgeColor;
    String badgeText;

    if (isOutOfStock) {
      badgeColor = Colors.red;
      badgeText = 'Out of stock';
    } else if (isLowStock) {
      badgeColor = Colors.orange;
      badgeText = 'Stock: $stockQuantity';
    } else {
      badgeColor = Colors.green;
      badgeText = 'Stock: $stockQuantity';
    }

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 8,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: badgeColor.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        badgeText,
        style: TextStyle(
          fontSize: 11,
          color: badgeColor,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
