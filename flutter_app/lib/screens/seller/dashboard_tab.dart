import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/money.dart';
import '../../providers/auth_provider.dart';
import '../../providers/seller_provider.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';

class DashboardTab extends StatefulWidget {
  const DashboardTab({super.key});

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab> {
  bool _initialFetchScheduled = false;

  /// Wait for the auth provider to finish restoring its session and have a
  /// JWT before issuing the first fetch. On a cold start, `AuthProvider` is
  /// briefly `isLoading=true` while reading SharedPreferences — firing the
  /// fetch during that window sends a request with no `Authorization` header
  /// and the user has to tap refresh manually. This avoids that race.
  void _scheduleInitialFetchWhenReady() {
    if (_initialFetchScheduled) return;
    final auth = context.read<AuthProvider>();
    final hasToken = (auth.backendAccessToken ?? '').isNotEmpty;
    if (auth.isLoading || !hasToken) return;
    _initialFetchScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<SellerProvider>().fetchDashboardStats();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Re-checks every time AuthProvider notifies (because we watch it below
    // via context.watch in build()), which covers the cold-start path where
    // the JWT only becomes available after a frame or two.
    _scheduleInitialFetchWhenReady();
  }

  Future<void> _onRefresh() async {
    await context.read<SellerProvider>().refresh();
  }

  @override
  Widget build(BuildContext context) {
    // Watching AuthProvider so didChangeDependencies re-fires once the
    // session restore completes and a token is available.
    context.watch<AuthProvider>();
    final seller = context.watch<SellerProvider>();

    // Show loading indicator while fetching data
    if (seller.isLoading && seller.sales.isEmpty && seller.recentOrders.isEmpty) {
      return const LoadingWidget(label: 'Loading dashboard...');
    }

    // Show error message with retry button on failure
    if (seller.error != null && seller.sales.isEmpty && seller.recentOrders.isEmpty) {
      return ErrorView(
        message: seller.error!,
        onRetry: () => context.read<SellerProvider>().fetchDashboardStats(),
      );
    }

    // Main dashboard content with pull-to-refresh
    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Sales Metrics Section
          const Text(
            'Sales Metrics',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 12),
          _buildSalesMetrics(seller),
          const SizedBox(height: 24),

          // Order Metrics Section
          const Text(
            'Order Metrics',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 12),
          _buildOrderMetrics(seller),
          const SizedBox(height: 24),

          // Recent Orders Section
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Recent Orders',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF1E293B),
                ),
              ),
              Text(
                '${seller.recentOrders.length} orders',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildRecentOrders(seller),
        ],
      ),
    );
  }

  Widget _buildSalesMetrics(SellerProvider seller) {
    // All-time earnings come from the server-side summary endpoint
    // (sums delivered seller_orders.total_amount). The daily sales series
    // is used for last-7-day and today derivations.
    final totalEarnings = seller.summary.totalEarnings;

    final todaySales = seller.sales.isNotEmpty
        ? seller.sales.last.totalSales
        : 0.0;

    final last7DaysSales = seller.sales.length > 7
        ? seller.sales
            .skip(seller.sales.length - 7)
            .fold<double>(0, (sum, point) => sum + point.totalSales)
        : seller.sales.fold<double>(0, (sum, point) => sum + point.totalSales);

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _buildMetricCard(
                title: 'Total Earnings',
                value: formatMoney(totalEarnings),
                icon: Icons.attach_money,
                color: Colors.green,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricCard(
                title: 'Total Products',
                value: '${seller.summary.totalProducts}',
                icon: Icons.inventory_2,
                color: Colors.purple,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildMetricCard(
                title: "Today's Sales",
                value: formatMoney(todaySales),
                icon: Icons.today,
                color: Colors.blue,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricCard(
                title: 'Last 7 Days',
                value: formatMoney(last7DaysSales),
                icon: Icons.calendar_view_week,
                color: Colors.orange,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildOrderMetrics(SellerProvider seller) {
    final s = seller.summary;
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _buildMetricCard(
                title: 'Total Orders',
                value: '${s.totalOrders}',
                icon: Icons.shopping_cart,
                color: Colors.indigo,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricCard(
                title: 'Pending',
                value: '${s.pendingOrders}',
                icon: Icons.pending,
                color: Colors.amber,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildMetricCard(
                title: 'Delivered',
                value: '${s.deliveredOrders}',
                icon: Icons.check_circle,
                color: Colors.teal,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricCard(
                title: 'Other',
                value: '${(s.totalOrders - s.pendingOrders - s.deliveredOrders).clamp(0, s.totalOrders)}',
                icon: Icons.more_horiz,
                color: Colors.blueGrey,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE5E7EB)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: Color(0xFF111827),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            title,
            style: const TextStyle(
              fontSize: 11,
              color: Color(0xFF6B7280),
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildRecentOrders(SellerProvider seller) {
    if (seller.recentOrders.isEmpty) {
      return Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE5E7EB)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.06),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Column(
              children: [
                Icon(Icons.inbox, size: 48, color: Colors.grey[400]),
                const SizedBox(height: 8),
                Text(
                  'No recent orders',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Column(
      children: seller.recentOrders.map((order) {
        final statusColor = _getStatusColor(order.status);
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE5E7EB)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.04),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left accent border
                  Container(width: 4, color: statusColor),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                      child: Row(
                        children: [
                          CircleAvatar(
                            backgroundColor: statusColor.withValues(alpha: 0.12),
                            radius: 20,
                            child: Icon(
                              _getStatusIcon(order.status),
                              color: statusColor,
                              size: 18,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  order.orderNumber.isEmpty
                                      ? 'Order #${order.sellerOrderId}'
                                      : order.orderNumber,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 14,
                                    color: Color(0xFF111827),
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  order.customerName.isEmpty ? 'Customer' : order.customerName,
                                  style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
                                ),
                                const SizedBox(height: 4),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: statusColor.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(999),
                                  ),
                                  child: Text(
                                    order.status.isEmpty ? 'pending' : order.status,
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: statusColor,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Text(
                            formatMoney(order.totalAmount),
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                              color: Color(0xFF111827),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return Colors.amber;
      case 'processing':
        return Colors.cyan;
      case 'completed':
      case 'delivered':
        return Colors.teal;
      case 'cancelled':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return Icons.pending;
      case 'processing':
        return Icons.sync;
      case 'completed':
      case 'delivered':
        return Icons.check_circle;
      case 'cancelled':
        return Icons.cancel;
      default:
        return Icons.shopping_bag;
    }
  }
}
