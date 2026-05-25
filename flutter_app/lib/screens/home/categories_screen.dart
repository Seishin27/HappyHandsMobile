import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/network/api_client.dart';
import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../models/category.dart';
import '../../models/product.dart';
import '../../models/api_response.dart';
import '../../services/flask_api_service.dart';
import '../../providers/cart_provider.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/product_card.dart';
import '../../widgets/custom_app_bar.dart';
import '../product_detail_screen.dart';
import '../cart_screen.dart';
import '../auth_screen.dart';

class CategoriesScreen extends StatefulWidget {
  final String initialSlug;

  const CategoriesScreen({super.key, required this.initialSlug});

  @override
  State<CategoriesScreen> createState() => _CategoriesScreenState();
}

class _CategoriesScreenState extends State<CategoriesScreen> {
  final _scaffoldKey = GlobalKey<ScaffoldState>();
  bool _loading = true;
  String? _error;
  String _slug = '';
  List<Category> _categories = const [];
  List<Product> _products = const [];

  @override
  void initState() {
    super.initState();
    _slug = widget.initialSlug;
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      Future<String?> tokenProvider() async => null;
      final api = FlaskApiService(
        ApiClient(tokenProvider: tokenProvider),
        tokenProvider: tokenProvider,
      );
      final res = await api.fetchCategory(_slug);
      if (!mounted) return;
      setState(() {
        _categories = res.categories;
        _products = res.products;
        _loading = false;
      });
    } catch (e) {
      try {
        final api = ApiClient(tokenProvider: () async => null);
        final response = await api.getJson(
          '/products',
          query: {'page': '1', 'page_size': '24', 'category': _slug},
        );

        final parsed = ApiResponse.fromJson<Map<String, dynamic>>(response, (
          data,
        ) {
          return (data as Map<String, dynamic>?) ?? <String, dynamic>{};
        });

        final dynamic responseData = response['data'];
        final dynamic payload = parsed.data ?? responseData ?? response;
        final List<dynamic> productsRaw = payload is Map<String, dynamic>
            ? (payload['items'] as List<dynamic>? ??
                  payload['products'] as List<dynamic>? ??
                  const [])
            : payload is List<dynamic>
            ? payload
            : const [];
        final products = productsRaw
            .whereType<Map<String, dynamic>>()
            .map(Product.fromJson)
            .toList();

        if (!mounted) return;
        setState(() {
          _categories = AppConstants.categories
              .map(
                (entry) => Category(
                  slug: entry['id'] ?? '',
                  name: entry['name'] ?? '',
                ),
              )
              .toList();
          _products = products;
          _loading = false;
          _error = products.isEmpty
              ? 'No products found for this category.'
              : null;
        });
      } catch (fallbackError) {
        if (!mounted) return;
        setState(() {
          _error = fallbackError.toString();
          _loading = false;
        });
      }
    }
  }

  void _navigateToCart() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const CartScreen()),
    );
  }

  void _navigateToProfile() {
    final authProvider = context.read<AuthProvider>();
    if (authProvider.user == null) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => const AuthScreen()),
      );
    } else {
      Navigator.pushNamed(context, '/profile');
    }
  }

  void _addToCart(Product product) async {
    final cartProvider = context.read<CartProvider>();
    final authProvider = context.read<AuthProvider>();

    final success = await cartProvider.addToCart(
      product: product,
      quantity: 1,
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
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(cartProvider.error ?? AppConstants.errorGeneral),
          backgroundColor: AppTheme.errorRed,
          duration: const Duration(seconds: 3),
        ),
      );
    }
  }

  Widget _buildCategoryDrawer() {
    return Drawer(
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [AppTheme.navBlue, AppTheme.heroDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: const Text(
                'Categories',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Expanded(
              child: ListView.builder(
                padding: EdgeInsets.zero,
                itemCount: _categories.length,
                itemBuilder: (context, index) {
                  final c = _categories[index];
                  final selected = c.slug == _slug;
                  return ListTile(
                    leading: Icon(
                      Icons.label_rounded,
                      color: selected ? AppTheme.primaryBlue : AppTheme.mediumGray,
                      size: 20,
                    ),
                    title: Text(
                      c.name,
                      style: TextStyle(
                        color: selected ? AppTheme.primaryBlue : AppTheme.darkBlue,
                        fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                        fontSize: 14,
                      ),
                    ),
                    tileColor: selected
                        ? AppTheme.primaryBlue.withValues(alpha: 0.08)
                        : null,
                    onTap: () {
                      Navigator.pop(context);
                      if (_slug != c.slug) {
                        setState(() => _slug = c.slug);
                        _load();
                      }
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGrid() {
    if (_products.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.search_off_rounded, size: 56, color: AppTheme.mediumGray),
            const SizedBox(height: 12),
            Text(
              'No products in this category',
              style: TextStyle(color: AppTheme.mediumGray, fontSize: 15),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: GridView.builder(
        padding: const EdgeInsets.all(AppConstants.spacingMD),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: AppConstants.spacingMD,
          mainAxisSpacing: AppConstants.spacingMD,
          mainAxisExtent: 270,
        ),
        itemCount: _products.length,
        itemBuilder: (context, index) {
          final p = _products[index];
          return ProductCard(
            product: p,
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ProductDetailScreen(productId: p.id),
                ),
              );
            },
            onAddToCart: () => _addToCart(p),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: AppTheme.white,
      drawer: _buildCategoryDrawer(),
      appBar: CustomAppBar(
        title: 'Shop by Category',
        showBackButton: true,
        onCartTap: _navigateToCart,
        onProfileTap: _navigateToProfile,
        actions: [
          IconButton(
            icon: const Icon(Icons.category_rounded, color: AppTheme.darkBlue, size: 20),
            onPressed: () => _scaffoldKey.currentState?.openDrawer(),
            tooltip: 'Browse categories',
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
          ),
        ],
      ),
      body: Builder(
        builder: (_) {
          if (_loading) {
            return const LoadingWidget(label: 'Loading category...');
          }
          if (_error != null) {
            return ErrorView(message: _error!, onRetry: _load);
          }

          return Column(
            children: [
              SizedBox(
                height: 56,
                child: ListView.separated(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppConstants.spacingLG,
                    vertical: AppConstants.spacingSM,
                  ),
                  scrollDirection: Axis.horizontal,
                  itemCount: _categories.length,
                  separatorBuilder: (context, index) =>
                      const SizedBox(width: AppConstants.spacingSM),
                  itemBuilder: (context, index) {
                    final c = _categories[index];
                    final selected = c.slug == _slug;
                    return ChoiceChip(
                      label: Text(c.name),
                      selected: selected,
                      onSelected: (_) {
                        setState(() => _slug = c.slug);
                        _load();
                      },
                      selectedColor: AppTheme.primaryBlue.withValues(alpha: 0.1),
                      labelStyle: TextStyle(
                        color: selected ? AppTheme.primaryBlue : AppTheme.darkBlue,
                        fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppConstants.radiusMD),
                        side: BorderSide(
                          color: selected ? AppTheme.primaryBlue : AppTheme.borderGray,
                        ),
                      ),
                      backgroundColor: AppTheme.white,
                    );
                  },
                ),
              ),
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  child: KeyedSubtree(
                    key: ValueKey(_slug),
                    child: _buildGrid(),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
