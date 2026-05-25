import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/money.dart';
import '../../models/product.dart';
import '../../providers/auth_provider.dart';
import '../../providers/cart_provider.dart';
import '../../services/flask_api_service.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/primary_button.dart';

class ProductDetailScreen extends StatefulWidget {
  final int productId;

  const ProductDetailScreen({super.key, required this.productId});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  bool _loading = true;
  String? _error;
  Product? _product;
  int _qty = 1;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final api = context.read<FlaskApiService>();
      final p = await api.fetchProduct(widget.productId);
      if (!mounted) return;
      setState(() {
        _product = p;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Product')),
      body: Builder(
        builder: (_) {
          if (_loading) return const LoadingWidget(label: 'Loading product...');
          if (_error != null) {
            return ErrorView(message: _error!, onRetry: _load);
          }
          final product = _product;
          if (product == null) {
            return const ErrorView(message: 'Product not found');
          }
          final int maxQty = product.stock ?? 0;
          final bool outOfStock = maxQty <= 0;

          return RefreshIndicator(
            onRefresh: _load,
            child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              AspectRatio(
                aspectRatio: 1,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(18),
                  child: Container(
                    color: const Color(0xFFF2F2F6),
                    child: product.imageUrl == null || product.imageUrl!.isEmpty
                        ? const Icon(
                            Icons.image_not_supported_outlined,
                            size: 48,
                          )
                        : CachedNetworkImage(
                            imageUrl: product.imageUrl!,
                            fit: BoxFit.cover,
                            errorWidget: (context, url, error) => const Icon(
                              Icons.broken_image_outlined,
                              size: 48,
                            ),
                            placeholder: (context, url) => const Center(
                              child: CircularProgressIndicator(),
                            ),
                          ),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Text(
                product.name,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Text(
                formatMoney(product.price),
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                product.description.isEmpty
                    ? 'No description provided.'
                    : product.description,
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  IconButton(
                    onPressed: _qty <= 1
                        ? null
                        : () => setState(() => _qty -= 1),
                    icon: const Icon(Icons.remove_circle_outline),
                  ),
                  Text(
                    'Qty: $_qty',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  IconButton(
                    onPressed: (outOfStock || _qty >= maxQty)
                        ? null
                        : () => setState(() => _qty += 1),
                    icon: const Icon(Icons.add_circle_outline),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    outOfStock ? 'Out of stock' : 'Stock: $maxQty',
                    style: TextStyle(
                      color: outOfStock ? Colors.red : Colors.grey[700],
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              if (cart.error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text(
                    cart.error!,
                    style: const TextStyle(color: Colors.red),
                  ),
                ),
              PrimaryButton(
                text: outOfStock ? 'Out of stock' : 'Add to cart',
                isLoading: cart.isLoading,
                onPressed: outOfStock
                    ? null
                    : () async {
                        if (_qty > maxQty) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Only $maxQty in stock')),
                          );
                          return;
                        }
                        final authProvider = context.read<AuthProvider>();
                        final success = await context
                            .read<CartProvider>()
                            .addToCart(
                              product: product,
                              quantity: _qty,
                              authToken: authProvider.backendAccessToken,
                            );
                        if (!context.mounted) return;
                        if (success) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Added to cart')),
                          );
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                context.read<CartProvider>().error ??
                                    'Could not add to cart',
                              ),
                            ),
                          );
                        }
                      },
              ),
            ],
            ),
          );
        },
      ),
    );
  }
}
