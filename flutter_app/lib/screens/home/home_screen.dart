import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../providers/products_provider.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/product_card.dart';
import '../../core/theme/app_theme.dart';
import '../../core/constants/app_constants.dart';
import 'categories_screen.dart';
import '../auth/rider_auth_screen.dart';
import '../auth/seller_auth_screen.dart';
import '../product/product_detail_screen.dart';
import '../role_selection_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProductsProvider>().fetch();
    });
  }

  @override
  Widget build(BuildContext context) {
    final products = context.watch<ProductsProvider>();

    return Scaffold(
      resizeToAvoidBottomInset: false,
      appBar: AppBar(
        title: const Text('HappyHands'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(110),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                child: TextField(
                  readOnly: true,
                  decoration: InputDecoration(
                    hintText: 'Search products (coming soon)',
                    prefixIcon: const Icon(Icons.search),
                    contentPadding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
              SizedBox(
                height: 44,
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  scrollDirection: Axis.horizontal,
                  children: [
                    _CategoryChip(
                      label: 'Baby Clothes',
                      slug: 'baby-clothes',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const CategoriesScreen(
                            initialSlug: 'baby-clothes',
                          ),
                        ),
                      ),
                    ),
                    _CategoryChip(
                      label: 'Comfort Toys',
                      slug: 'comfort-toys',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const CategoriesScreen(
                            initialSlug: 'comfort-toys',
                          ),
                        ),
                      ),
                    ),
                    _CategoryChip(
                      label: 'Educational',
                      slug: 'educational-toys',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const CategoriesScreen(
                            initialSlug: 'educational-toys',
                          ),
                        ),
                      ),
                    ),
                    _CategoryChip(
                      label: 'Stroller Gear',
                      slug: 'stroller-gear',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const CategoriesScreen(
                            initialSlug: 'stroller-gear',
                          ),
                        ),
                      ),
                    ),
                    _CategoryChip(
                      label: 'Safety',
                      slug: 'safety-and-health',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const CategoriesScreen(
                            initialSlug: 'safety-and-health',
                          ),
                        ),
                      ),
                    ),
                    _CategoryChip(
                      label: 'Nursery',
                      slug: 'nursery-furniture',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const CategoriesScreen(
                            initialSlug: 'nursery-furniture',
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 10),
            ],
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Logout',
            icon: const Icon(Icons.logout, color: AppTheme.darkBlue),
            onPressed: () async {
              final navigator = Navigator.of(context);
              await context.read<AuthProvider>().logout();
              if (!mounted) return;
              navigator.pushNamedAndRemoveUntil(
                '/home',
                (route) => false,
              );
            },
          ),
        ],
      ),
      body: Builder(
        builder: (_) {
          if (products.isLoading) {
            return const LoadingWidget(label: 'Loading products...');
          }
          if (products.error != null) {
            return ErrorView(
              message: products.error!,
              onRetry: () => context.read<ProductsProvider>().fetch(),
            );
          }

          final items = products.items;
          return RefreshIndicator(
            onRefresh: () => context.read<ProductsProvider>().fetch(),
            child: CustomScrollView(
              slivers: [
                // Join Platform Section - AT TOP
                SliverToBoxAdapter(
                  child: Container(
                    margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: AppTheme.lightGray,
                      borderRadius: BorderRadius.circular(
                        AppConstants.radiusXL,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        LayoutBuilder(
                          builder: (context, constraints) {
                            final isNarrow = constraints.maxWidth < 380;

                            final copy = Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Join Our Platform',
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: Theme.of(context).textTheme.titleLarge
                                      ?.copyWith(
                                        color: AppTheme.darkBlue,
                                        fontWeight: FontWeight.w700,
                                      ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Become a partner today',
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: Theme.of(context).textTheme.bodyMedium
                                      ?.copyWith(color: AppTheme.mediumGray),
                                ),
                              ],
                            );

                            final actionButton = ElevatedButton(
                              onPressed: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) =>
                                      const RoleSelectionScreen(),
                                ),
                              ),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppTheme.primaryBlue,
                                foregroundColor: AppTheme.white,
                                elevation: 0,
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(
                                    AppConstants.radiusLG,
                                  ),
                                ),
                              ),
                              child: const Text('Join Now'),
                            );

                            if (isNarrow) {
                              return Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  copy,
                                  const SizedBox(height: 12),
                                  actionButton,
                                ],
                              );
                            }

                            return Row(
                              children: [
                                Expanded(child: copy),
                                const SizedBox(width: 12),
                                actionButton,
                              ],
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                ),

                // Products Section Header
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Featured Products',
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(
                                color: AppTheme.darkBlue,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                        Text(
                          '${items.length} items',
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: AppTheme.mediumGray),
                        ),
                      ],
                    ),
                  ),
                ),

                // Products Grid (or empty state)
                if (items.isEmpty)
                  SliverToBoxAdapter(
                    child: Container(
                      height: 200,
                      alignment: Alignment.center,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.shopping_bag_outlined,
                            size: 48,
                            color: AppTheme.mediumGray.withValues(alpha: 0.5),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'No products available',
                            style: Theme.of(context).textTheme.bodyLarge
                                ?.copyWith(color: AppTheme.mediumGray),
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.all(12),
                    sliver: SliverGrid.builder(
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            crossAxisSpacing: 12,
                            mainAxisSpacing: 12,
                            mainAxisExtent: 270,
                          ),
                      itemCount: items.length,
                      itemBuilder: (context, index) {
                        final p = items[index];
                        return ProductCard(
                          product: p,
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) =>
                                    ProductDetailScreen(productId: p.id),
                              ),
                            );
                          },
                        );
                      },
                    ),
                  ),

                // Footer Section
                SliverToBoxAdapter(child: _buildFooterSection(context)),

                // Bottom padding
                const SliverToBoxAdapter(child: SizedBox(height: 24)),
              ],
            ),
          );
        },
      ),
    );
  }

  // ── Footer helpers (moved from extension to state) ──────────────────────

  Widget _buildFooterSection(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppTheme.darkBlue, AppTheme.primaryBlue],
        ),
        borderRadius: BorderRadius.circular(AppConstants.radiusXL),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final isNarrow = constraints.maxWidth < 440;

              final copy = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Grow with Happy Hands',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: AppTheme.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Join our seller and rider network. Start selling products or delivering orders with a clean, simple onboarding flow.',
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppTheme.white.withValues(alpha: 0.82),
                      height: 1.45,
                    ),
                  ),
                ],
              );

              final iconBlock = Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppTheme.white.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(AppConstants.radiusMD),
                ),
                child: const Icon(
                  Icons.storefront_outlined,
                  color: AppTheme.white,
                ),
              );

              if (isNarrow) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [copy, const SizedBox(height: 12), iconBlock],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: copy),
                  const SizedBox(width: 12),
                  iconBlock,
                ],
              );
            },
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 620;
              final sellerCard = Expanded(
                child: _buildFooterActionCard(
                  context,
                  icon: Icons.storefront_outlined,
                  title: 'Become a Seller',
                  description: 'List baby essentials and reach more customers.',
                  buttonText: 'Start Selling',
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const SellerAuthScreen()),
                  ),
                ),
              );
              final riderCard = Expanded(
                child: _buildFooterActionCard(
                  context,
                  icon: Icons.delivery_dining_outlined,
                  title: 'Become a Rider',
                  description: 'Deliver orders and earn flexible income.',
                  buttonText: 'Start Delivering',
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const RiderAuthScreen()),
                  ),
                ),
              );

              if (isWide) {
                return Row(
                  children: [sellerCard, const SizedBox(width: 12), riderCard],
                );
              }

              return Column(
                children: [
                  _buildFooterActionCard(
                    context,
                    icon: Icons.storefront_outlined,
                    title: 'Become a Seller',
                    description:
                        'List baby essentials and reach more customers.',
                    buttonText: 'Start Selling',
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const SellerAuthScreen(),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  _buildFooterActionCard(
                    context,
                    icon: Icons.delivery_dining_outlined,
                    title: 'Become a Rider',
                    description: 'Deliver orders and earn flexible income.',
                    buttonText: 'Start Delivering',
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const RiderAuthScreen(),
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildFooterActionCard(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String description,
    required String buttonText,
    required VoidCallback onPressed,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppConstants.radiusLG),
        border: Border.all(color: AppTheme.white.withValues(alpha: 0.16)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppTheme.white.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(AppConstants.radiusMD),
            ),
            child: Icon(icon, color: AppTheme.white),
          ),
          const SizedBox(height: 14),
          Text(
            title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: AppTheme.white,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            description,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: AppTheme.white.withValues(alpha: 0.82),
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: onPressed,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.white,
                foregroundColor: AppTheme.darkBlue,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 13),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppConstants.radiusLG),
                ),
              ),
              child: Text(
                buttonText,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 14,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  final String label;
  final String slug;
  final VoidCallback onTap;

  const _CategoryChip({
    required this.label,
    required this.slug,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ActionChip(label: Text(label), onPressed: onTap),
    );
  }
}
