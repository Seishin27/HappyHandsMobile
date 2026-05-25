import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../providers/product_provider.dart';
import '../providers/cart_provider.dart';
import '../providers/auth_provider.dart';
import '../widgets/hero_carousel.dart';
import '../widgets/product_card.dart';
import '../widgets/loading_widget.dart';
import '../widgets/custom_app_bar.dart';
import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';
import '../models/product.dart';
import '../screens/product_detail_screen.dart';
import '../screens/home/categories_screen.dart';
import '../screens/cart_screen.dart';
import '../screens/auth_screen.dart';
import '../screens/auth/seller_auth_screen.dart';
import '../screens/auth/rider_auth_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _searchController = TextEditingController();
  bool _isSearching = false;

  @override
  void initState() {
    super.initState();
    _initializeData();
    _setupScrollListener();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _initializeData() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<ProductProvider>().loadFeaturedProducts(refresh: true);
      context.read<ProductProvider>().loadProducts(refresh: true);
      // Cart loading is handled automatically by ChangeNotifierProxyProvider2
      // in main.dart — no manual trigger needed here.
    });
  }

  void _setupScrollListener() {
    _scrollController.addListener(() {
      if (_scrollController.position.pixels >=
          _scrollController.position.maxScrollExtent - 200) {
        final productProvider = context.read<ProductProvider>();
        if (productProvider.hasMorePages && !productProvider.isLoading) {
          productProvider.loadMoreProducts();
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: CustomAppBar(
        title: 'Happy Hands',
        showSearch: true,
        searchController: _searchController,
        onSearchChanged: (query) {
          setState(() {
            _isSearching = query.isNotEmpty;
          });
          if (query.isNotEmpty) {
            context.read<ProductProvider>().searchProducts(query);
          } else {
            context.read<ProductProvider>().clearSearch();
          }
        },
        onCartTap: () => _navigateToCart(),
        onProfileTap: () => _navigateToProfile(),
      ),
      body: RefreshIndicator(
        onRefresh: _refreshData,
        color: AppTheme.primaryBlue,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isSearching) {
      return _buildSearchResults();
    }

    return SingleChildScrollView(
      controller: _scrollController,
      physics: const AlwaysScrollableScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Hero Carousel
          HeroCarousel(onShopNow: _scrollToProducts),

          // Featured Products Section
          _buildFeaturedSection(),

          // Categories Section
          _buildCategoriesSection(),

          // All Products Section (4-col grid + pagination)
          _buildAllProductsSection(),

          // Features Section (banner + feature cards)
          _buildFeaturesSection(),

          // Footer (Become a Seller / Rider)
          _buildFooter(),
        ],
      ),
    );
  }

  Widget _buildSearchResults() {
    return Consumer<ProductProvider>(
      builder: (context, productProvider, child) {
        if (productProvider.isLoadingSearch) {
          return const LoadingWidget();
        }

        if (productProvider.searchError != null) {
          return _buildErrorWidget(
            productProvider.searchError!,
            () => productProvider.searchProducts(_searchController.text),
          );
        }

        if (productProvider.searchResults.isEmpty) {
          return _buildEmptySearch();
        }

        return SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppConstants.spacingMD),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Search Results',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: AppTheme.darkBlue,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: AppConstants.spacingMD),
              _buildProductGrid(productProvider.searchResults),
            ],
          ),
        );
      },
    );
  }

  static const int _topPicksLimit = 8;

  Widget _buildFeaturedSection() {
    return Consumer<ProductProvider>(
      builder: (context, productProvider, child) {
        final topPicks =
            productProvider.featuredProducts.take(_topPicksLimit).toList();
        return Container(
          color: const Color(0xFFF8F9FA),
          padding: const EdgeInsets.fromLTRB(
            AppConstants.spacingMD,
            AppConstants.spacingLG,
            AppConstants.spacingMD,
            AppConstants.spacingLG,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Section Header — web: 2.5rem weight 700 color #333 centered
              Center(
                child: Text(
                  'Top picks for your little ones',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF333333),
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: AppConstants.spacingMD),

              // Featured Products Grid
              if (productProvider.isLoadingFeatured)
                const LoadingWidget(height: 200)
              else if (topPicks.isEmpty)
                _buildEmptyFeatured()
              else
                _buildProductGrid(topPicks),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCategoriesSection() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(
        AppConstants.spacingMD,
        AppConstants.spacingLG,
        AppConstants.spacingMD,
        AppConstants.spacingLG,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Web: h2 2.5rem weight 700 color #333 centered
          Text(
            'Shop by Category',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w700,
              color: const Color(0xFF333333),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppConstants.spacingXS),
          Text(
            'Our collections',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontSize: 15,
              color: const Color(0xFF666666),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppConstants.spacingXL),

          // Categories Grid
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              childAspectRatio: 1.0,
              crossAxisSpacing: AppConstants.spacingSM,
              mainAxisSpacing: AppConstants.spacingSM,
            ),
            itemCount: AppConstants.categories.length,
            itemBuilder: (context, index) {
              final category = AppConstants.categories[index];
              return _buildCategoryCard(category);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryCard(Map<String, String> category) {
    return GestureDetector(
      onTap: () => _navigateToCategory(category['id']!),
      child: Container(
        decoration: BoxDecoration(
          // Web: category-item bg #f8f9fa, border-radius 15px
          color: const Color(0xFFF8F9FA),
          borderRadius: BorderRadius.circular(15),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              category['icon'] ?? '📦',
              style: const TextStyle(fontSize: 28),
            ),
            const SizedBox(height: 4),
            Text(
              category['name'] ?? 'Category',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: Color(0xFF333333),
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  // ── All Products: 4-column grid + pagination + footer ────────────────────

  static const int _pageSize = 10; // 2 cols × 5 rows per page
  int _currentPage = 1;

  int get _totalPages {
    final provider = context.read<ProductProvider>();
    final total = provider.products.length;
    return (total / _pageSize).ceil().clamp(1, 999);
  }

  List<Product> get _pagedProducts {
    final provider = context.read<ProductProvider>();
    final all = provider.products;
    final start = (_currentPage - 1) * _pageSize;
    final end = (start + _pageSize).clamp(0, all.length);
    if (start >= all.length) return [];
    return all.sublist(start, end);
  }

  Widget _buildAllProductsSection() {
    return Consumer<ProductProvider>(
      builder: (context, productProvider, child) {
        return Container(
          // Web: featured-products section bg #f8f9fa
          color: const Color(0xFFF8F9FA),
          padding: const EdgeInsets.fromLTRB(
            AppConstants.spacingMD,
            AppConstants.spacingLG,
            AppConstants.spacingMD,
            0,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header — web: centered h2 2.5rem weight 700 #333
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'All Products',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF333333),
                    ),
                  ),
                  if (productProvider.products.isNotEmpty)
                    Text(
                      '${productProvider.products.length} items',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF666666),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: AppConstants.spacingMD),

              // ── Grid ────────────────────────────────────────────────────
              if (productProvider.isLoading && productProvider.products.isEmpty)
                const LoadingWidget(height: 300)
              else if (productProvider.products.isEmpty)
                _buildEmptyProducts()
              else
                _buildFourColumnGrid(_pagedProducts),

              // ── Pagination ───────────────────────────────────────────────
              if (productProvider.products.isNotEmpty) ...[
                const SizedBox(height: AppConstants.spacingLG),
                _buildPagination(productProvider),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildFourColumnGrid(List<Product> products) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisExtent: 270,
        crossAxisSpacing: AppConstants.spacingMD,
        mainAxisSpacing: AppConstants.spacingMD,
      ),
      itemCount: products.length,
      itemBuilder: (context, index) {
        final product = products[index];
        return ProductCard(
          product: product,
          onTap: () => _navigateToProductDetail(product),
          onAddToCart: () => _addToCart(product),
        );
      },
    );
  }

  Widget _buildPagination(ProductProvider productProvider) {
    final total = _totalPages;
    if (total <= 1) return const SizedBox.shrink();

    final List<int> pages = [];
    final start = (_currentPage - 2).clamp(1, total);
    final end = (_currentPage + 2).clamp(1, total);
    for (int i = start; i <= end; i++) {
      pages.add(i);
    }

    return Padding(
      padding: const EdgeInsets.only(top: 4, bottom: 12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Divider(height: 1, color: AppTheme.borderGray),
          const SizedBox(height: 12),
          // ── Horizontal row of buttons ──────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Prev
              if (_currentPage > 1)
                _pageButton('‹', () => setState(() => _currentPage--)),

              // Page numbers
              for (final p in pages)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: _pageButton(
                    '$p',
                    () => setState(() => _currentPage = p),
                    isActive: p == _currentPage,
                  ),
                ),

              // Next
              if (_currentPage < total)
                _pageButton('›', () => setState(() => _currentPage++)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Page $_currentPage of $total',
            style: const TextStyle(fontSize: 11, color: AppTheme.mediumGray),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  Widget _pageButton(String label, VoidCallback onTap, {bool isActive = false}) {
    return SizedBox(
      height: 44,
      child: isActive
          ? FilledButton(
              onPressed: onTap,
              style: FilledButton.styleFrom(
                backgroundColor: AppTheme.navBlue,
                minimumSize: const Size(44, 44),
                padding: const EdgeInsets.symmetric(horizontal: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
              ),
              child: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
            )
          : OutlinedButton(
              onPressed: onTap,
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.navBlue,
                side: const BorderSide(color: Color(0xFFDFE3EA), width: 1.5),
                minimumSize: const Size(44, 44),
                padding: const EdgeInsets.symmetric(horizontal: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
              ),
              child: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
            ),
    );
  }

  // ── Features section — matches web: gradient banner + white features grid ──

  Widget _buildFeaturesSection() {
    return Column(
      children: [
        // Features Banner — web: gradient bg #f8fafc→#e2e8f0, white card inside
        Container(
          width: double.infinity,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFFF8FAFC), Color(0xFFE2E8F0)],
            ),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppConstants.spacingMD,
            vertical: AppConstants.spacingLG,
          ),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppConstants.spacingMD),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x14000000),
                  blurRadius: 40,
                  offset: Offset(0, 10),
                ),
              ],
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final isNarrow = constraints.maxWidth < 500;
                final bannerLeft = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Bring Home Joyful Moments',
                      style: TextStyle(
                        fontSize: isNarrow ? 17 : 26,
                        fontWeight: FontWeight.w700,
                        color: const Color(0xFF1A202C),
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Curated baby essentials parents rave about.',
                      style: TextStyle(
                        fontSize: 13,
                        color: Color(0xFF4A5568),
                        height: 1.5,
                      ),
                    ),
                  ],
                );
                final ecoCard = Container(
                  padding: const EdgeInsets.all(AppConstants.spacingLG),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFFE8F5E8), Color(0xFFF0F9F0)],
                    ),
                    borderRadius: BorderRadius.circular(16),
                    border: const Border(
                      left: BorderSide(color: Color(0xFF48BB78), width: 4),
                    ),
                  ),
                  child: const Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('🌿', style: TextStyle(fontSize: 28)),
                      SizedBox(height: 8),
                      Text(
                        'Eco-Friendly',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF2D3748),
                        ),
                        textAlign: TextAlign.center,
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Safe materials for your little ones',
                        style: TextStyle(fontSize: 12, color: Color(0xFF4A5568)),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                );
                if (isNarrow) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      bannerLeft,
                      const SizedBox(height: AppConstants.spacingLG),
                      ecoCard,
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: bannerLeft),
                    const SizedBox(width: AppConstants.spacingXL),
                    ecoCard,
                  ],
                );
              },
            ),
          ),
        ),

        // Features Grid — web: white bg, 4 items, centered
        Container(
          color: Colors.white,
          padding: const EdgeInsets.symmetric(
            horizontal: AppConstants.spacingMD,
            vertical: AppConstants.spacingLG,
          ),
          child: GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 1.4,
              crossAxisSpacing: AppConstants.spacingMD,
              mainAxisSpacing: AppConstants.spacingMD,
            ),
            itemCount: AppConstants.features.length,
            itemBuilder: (context, index) {
              final feature = AppConstants.features[index];
              return _buildFeatureCard(feature);
            },
          ),
        ),
      ],
    );
  }

  /// 2-column grid used for featured products and search results.
  Widget _buildProductGrid(List<Product> products) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisExtent: 270,
        crossAxisSpacing: AppConstants.spacingMD,
        mainAxisSpacing: AppConstants.spacingMD,
      ),
      itemCount: products.length,
      itemBuilder: (context, index) {
        final product = products[index];
        return ProductCard(
          product: product,
          onTap: () => _navigateToProductDetail(product),
          onAddToCart: () => _addToCart(product),
        );
      },
    );
  }

  Widget _buildFeatureCard(Map<String, String> feature) {
    return Container(
      padding: const EdgeInsets.all(AppConstants.spacingSM),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(feature['icon'] ?? '📦', style: const TextStyle(fontSize: 24)),
          const SizedBox(height: 4),
          Text(
            feature['title'] ?? 'Feature',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w700,
              color: const Color(0xFF333333),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 2),
          Text(
            feature['subtitle'] ?? '',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontSize: 10,
              color: const Color(0xFF666666),
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  // ── Footer ────────────────────────────────────────────────────────────────

  Widget _buildFooter() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        AppConstants.spacingMD,
        AppConstants.spacingLG,
        AppConstants.spacingMD,
        AppConstants.spacingXL,
      ),
      // Web: baby-footer bg #f3f4f6, border-top 2px solid #2c5aa0
      decoration: const BoxDecoration(
        color: Color(0xFFF3F4F6),
        border: Border(
          top: BorderSide(color: Color(0xFF2C5AA0), width: 2),
        ),
      ),
      child: Column(
        children: [
          // Partner CTA row
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 500;

              final sellerBtn = _buildFooterPartnerButton(
                icon: Icons.storefront_outlined,
                label: 'Become a Seller',
                sublabel: 'Join our marketplace and reach thousands of parents',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => SellerAuthScreen()),
                ),
                isSeller: true,
              );

              final riderBtn = _buildFooterPartnerButton(
                icon: Icons.delivery_dining_outlined,
                label: 'Become a Rider',
                sublabel: 'Deliver joy to families and earn with flexible hours',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => RiderAuthScreen()),
                ),
                isSeller: false,
              );

              if (isWide) {
                return Row(
                  children: [
                    Expanded(child: sellerBtn),
                    const SizedBox(width: AppConstants.spacingMD),
                    Expanded(child: riderBtn),
                  ],
                );
              }
              return Column(
                children: [
                  sellerBtn,
                  const SizedBox(height: AppConstants.spacingMD),
                  riderBtn,
                ],
              );
            },
          ),

          const SizedBox(height: AppConstants.spacingXL),
          const Divider(color: Color(0xFFE0E6ED)),
          const SizedBox(height: AppConstants.spacingMD),

          // Brand — web: brand-name #2c5aa0 weight 700, tagline #666
          const Text(
            'HappyHands',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: Color(0xFF2C5AA0),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          const Text(
            'Creating magical moments for little ones',
            style: TextStyle(fontSize: 12, color: Color(0xFF666666)),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppConstants.spacingMD),
          // Copyright — web: footer-bottom
          const Text(
            '© 2025 HappyHands. Made with 💖 for families',
            style: TextStyle(fontSize: 11, color: Color(0xFF666666)),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildFooterPartnerButton({
    required IconData icon,
    required String label,
    required String sublabel,
    required VoidCallback onTap,
    bool isSeller = true,
  }) {
    // Web: seller card = #ffeaa7 bg, border-left 4px #fdcb6e
    //      rider card  = #d4f4dd bg, border-left 4px #27ae60
    final bgColor = isSeller ? const Color(0xFFFFEAA7) : const Color(0xFFD4F4DD);
    final borderColor = isSeller ? const Color(0xFFFDCB6E) : const Color(0xFF27AE60);
    final labelColor = isSeller ? const Color(0xFF2C5AA0) : const Color(0xFF27AE60);
    final btnColor = isSeller ? const Color(0xFF2C5AA0) : const Color(0xFF27AE60);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Ink(
          padding: const EdgeInsets.all(AppConstants.spacingSM),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
            border: Border(left: BorderSide(color: borderColor, width: 4)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: labelColor,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                sublabel,
                style: const TextStyle(fontSize: 11, color: Color(0xFF555555)),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: btnColor,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  isSeller ? 'Start Selling' : 'Start Riding',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptySearch() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(FontAwesomeIcons.magnifyingGlass, size: 64, color: AppTheme.mediumGray),
            const SizedBox(height: AppConstants.spacingMD),
            Text(
              'No products found',
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(color: AppTheme.mediumGray),
            ),
            const SizedBox(height: AppConstants.spacingSM),
            Text(
              'Try searching with different keywords',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppTheme.mediumGray),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyFeatured() {
    return Container(
      height: 200,
      decoration: BoxDecoration(
        color: AppTheme.lightGray,
        borderRadius: BorderRadius.circular(AppConstants.radiusMD),
        border: Border.all(color: AppTheme.borderGray.withValues(alpha: 0.3)),
      ),
      child: const Center(child: Text('No featured products available yet.')),
    );
  }

  Widget _buildEmptyProducts() {
    return Container(
      height: 300,
      decoration: BoxDecoration(
        color: AppTheme.lightGray,
        borderRadius: BorderRadius.circular(AppConstants.radiusMD),
        border: Border.all(color: AppTheme.borderGray.withValues(alpha: 0.3)),
      ),
      child: const Center(child: Text('No products available yet.')),
    );
  }

  Widget _buildErrorWidget(String error, VoidCallback onRetry) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              FontAwesomeIcons.triangleExclamation,
              size: 64,
              color: AppTheme.errorRed,
            ),
            const SizedBox(height: AppConstants.spacingMD),
            Text(
              'Something went wrong',
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(color: AppTheme.errorRed),
            ),
            const SizedBox(height: AppConstants.spacingSM),
            Text(
              error,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppTheme.mediumGray),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppConstants.spacingLG),
            ElevatedButton(
              onPressed: onRetry,
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

  Future<void> _refreshData() async {
    await Future.wait([
      context.read<ProductProvider>().refreshProducts(),
      context.read<ProductProvider>().loadFeaturedProducts(refresh: true),
    ]);
  }

  void _scrollToProducts() {
    // Scroll to products section
    // This would need to be implemented with a GlobalKey
  }

  void _navigateToProductDetail(Product product) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ProductDetailScreen(productId: product.id),
      ),
    );
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

  void _navigateToCategory(String categoryId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CategoriesScreen(initialSlug: categoryId),
      ),
    );
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
        SnackBar(
          content: Text(AppConstants.successAddedToCart),
          backgroundColor: AppTheme.successGreen,
          duration: const Duration(seconds: 2),
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
}
