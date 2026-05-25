import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/money.dart';
import '../../models/seller_order.dart';
import '../../providers/auth_provider.dart';
import '../../providers/orders_provider.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';
import 'order_detail_screen.dart';

/// Orders tab screen for seller dashboard.
///
/// Matches the Flask web seller_orders.html with:
/// - 8 correct status filter chips with counts
/// - Search bar for order # / customer name
/// - Action buttons per order: View, Update Status, Request Rider
/// - Rider name display
class OrdersTab extends StatefulWidget {
  const OrdersTab({super.key});

  @override
  State<OrdersTab> createState() => _OrdersTabState();
}

class _OrdersTabState extends State<OrdersTab> {
  final TextEditingController _searchController = TextEditingController();
  bool _initialFetchScheduled = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  /// Mirrors `DashboardTab._scheduleInitialFetchWhenReady`: only fire the first
  /// fetch once `AuthProvider` has finished restoring the JWT, otherwise the
  /// request goes out without an `Authorization` header and Flask returns 401,
  /// which `ApiClient` surfaces as an `ApiException`.
  void _scheduleInitialFetchWhenReady() {
    if (_initialFetchScheduled) return;
    final auth = context.read<AuthProvider>();
    final hasToken = (auth.backendAccessToken ?? '').isNotEmpty;
    if (auth.isLoading || !hasToken) return;
    _initialFetchScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<OrdersProvider>().fetchOrders();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _scheduleInitialFetchWhenReady();
  }

  Future<void> _onRefresh() async {
    await context.read<OrdersProvider>().fetchOrders();
  }

  void _navigateToOrderDetail(String orderId) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => OrderDetailScreen(orderId: orderId),
      ),
    );
  }

  void _onFilterSelected(String? status) {
    context.read<OrdersProvider>().setStatusFilter(status);
  }

  void _onSearchChanged(String query) {
    context.read<OrdersProvider>().setSearchQuery(query);
  }

  // ── Status Update Dialog (matching Flask modal) ──────────────────────────

  void _showUpdateStatusDialog(SellerOrder order) {
    String selectedStatus = order.status;
    final notesController = TextEditingController();

    // Seller can set: pending, packing, packed (matching Flask web dropdown)
    final allowedStatuses = ['pending', 'packing', 'packed'];

    // Don't allow changes on terminal statuses
    if (order.status == 'delivered' || order.status == 'cancelled') {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Cannot update a ${_prettyStatus(order.status)} order'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Update Order Status'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Order #${order.orderNumber}',
                  style: TextStyle(color: Colors.grey[600], fontSize: 13),
                ),
                const SizedBox(height: 16),
                const Text('New Status:', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: allowedStatuses.contains(selectedStatus) ? selectedStatus : allowedStatuses.first,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: allowedStatuses.map((s) {
                    return DropdownMenuItem(
                      value: s,
                      child: Text(_prettyStatus(s)),
                    );
                  }).toList(),
                  onChanged: (v) {
                    if (v != null) {
                      setDialogState(() => selectedStatus = v);
                    }
                  },
                ),
                const SizedBox(height: 16),
                const Text('Notes (Optional):', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                TextField(
                  controller: notesController,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    hintText: 'Add any additional notes...',
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                Navigator.pop(ctx);
                try {
                  await context.read<OrdersProvider>().updateOrderStatus(
                        order.id.toString(),
                        selectedStatus,
                        notes: notesController.text.trim().isNotEmpty
                            ? notesController.text.trim()
                            : null,
                      );
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Order status updated to ${_prettyStatus(selectedStatus)}'),
                        backgroundColor: Colors.green,
                      ),
                    );
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Failed: $e'),
                        backgroundColor: Colors.red,
                      ),
                    );
                  }
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2c5aa0),
                foregroundColor: Colors.white,
              ),
              child: const Text('Update Status'),
            ),
          ],
        ),
      ),
    );
  }

  // ── Request Rider Dialog (matching Flask modal) ──────────────────────────

  void _showRequestRiderDialog(SellerOrder order) {
    final provider = context.read<OrdersProvider>();
    provider.fetchAvailableRiders();
    int? selectedRiderId;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            title: const Text('Request Rider'),
            content: SizedBox(
              width: double.maxFinite,
              child: Consumer<OrdersProvider>(
                builder: (_, prov, __) {
                  if (prov.isLoadingRiders) {
                    return const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  if (prov.availableRiders.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(
                        child: Text(
                          'No active riders available right now.',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ),
                    );
                  }
                  return Column(
                    mainAxisSize: MainAxisSize.min,
                    children: prov.availableRiders.map((rider) {
                      final isSelected = selectedRiderId == rider.riderID;
                      return ListTile(
                        leading: Radio<int>(
                          value: rider.riderID,
                          groupValue: selectedRiderId,
                          onChanged: (v) => setDialogState(() => selectedRiderId = v),
                        ),
                        title: Text(rider.ridername),
                        subtitle: Text(
                          [
                            if (rider.phone != null && rider.phone!.isNotEmpty) rider.phone!,
                            if (rider.rideremail != null && rider.rideremail!.isNotEmpty) rider.rideremail!,
                          ].join(' • '),
                          style: const TextStyle(fontSize: 12),
                        ),
                        selected: isSelected,
                        onTap: () => setDialogState(() => selectedRiderId = rider.riderID),
                      );
                    }).toList(),
                  );
                },
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: selectedRiderId == null
                    ? null
                    : () async {
                        Navigator.pop(ctx);
                        try {
                          await provider.assignRider(
                            order.id.toString(),
                            selectedRiderId!,
                          );
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Rider requested successfully'),
                                backgroundColor: Colors.green,
                              ),
                            );
                          }
                        } catch (e) {
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('Failed: $e'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        }
                      },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2563eb),
                  foregroundColor: Colors.white,
                ),
                child: const Text('Request'),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Watching AuthProvider so didChangeDependencies re-fires once the
    // session restore completes and a token is available.
    context.watch<AuthProvider>();
    final ordersProvider = context.watch<OrdersProvider>();

    if (ordersProvider.isLoading && ordersProvider.orders.isEmpty) {
      return const LoadingWidget(label: 'Loading orders...');
    }

    if (ordersProvider.error != null && ordersProvider.orders.isEmpty) {
      return ErrorView(
        message: ordersProvider.error!,
        onRetry: () => context.read<OrdersProvider>().fetchOrders(),
      );
    }

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: Column(
        children: [
          _buildSearchBar(),
          _buildFilterChips(ordersProvider),
          Expanded(
            child: ordersProvider.filteredOrders.isEmpty
                ? _buildEmptyState(ordersProvider.statusFilter)
                : _buildOrdersList(ordersProvider),
          ),
        ],
      ),
    );
  }

  // ── Search Bar ───────────────────────────────────────────────────────────

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: TextField(
        controller: _searchController,
        onChanged: _onSearchChanged,
        decoration: InputDecoration(
          hintText: 'Search order # or customer...',
          prefixIcon: const Icon(Icons.search, size: 20),
          suffixIcon: _searchController.text.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear, size: 18),
                  onPressed: () {
                    _searchController.clear();
                    _onSearchChanged('');
                  },
                )
              : null,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
          filled: true,
          fillColor: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
        ),
      ),
    );
  }

  // ── Filter Chips (8 statuses matching Flask) ─────────────────────────────

  Widget _buildFilterChips(OrdersProvider ordersProvider) {
    final counts = ordersProvider.statusCounts;

    final filters = <({String label, String? value})>[
      (label: 'All', value: null),
      (label: 'Pending', value: 'pending'),
      (label: 'Packing', value: 'packing'),
      (label: 'Packed', value: 'packed'),
      (label: 'Assigned', value: 'assigned_to_rider'),
      (label: 'Picked Up', value: 'picked_up'),
      (label: 'On the Way', value: 'on_the_way'),
      (label: 'Delivered', value: 'delivered'),
      (label: 'Cancelled', value: 'cancelled'),
    ];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: filters.map((filter) {
            final isSelected = ordersProvider.statusFilter == filter.value;
            final count = filter.value == null
                ? counts['all'] ?? 0
                : counts[filter.value] ?? 0;

            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilterChip(
                label: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(filter.label),
                    const SizedBox(width: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? Colors.white.withValues(alpha: 0.3)
                            : Colors.grey.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '$count',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: isSelected ? Colors.white : Colors.grey[700],
                        ),
                      ),
                    ),
                  ],
                ),
                selected: isSelected,
                selectedColor: _getStatusColor(filter.value ?? 'all'),
                checkmarkColor: Colors.white,
                labelStyle: TextStyle(
                  color: isSelected ? Colors.white : null,
                ),
                onSelected: (_) => _onFilterSelected(filter.value),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  // ── Empty State ──────────────────────────────────────────────────────────

  Widget _buildEmptyState(String? statusFilter) {
    final message = statusFilter != null
        ? 'No ${_prettyStatus(statusFilter)} orders'
        : 'No orders yet';
    final subtitle = statusFilter != null
        ? 'Try selecting a different filter'
        : 'Orders will appear here when customers place them';

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 48),
        Icon(Icons.receipt_long_outlined, size: 80, color: Colors.grey[400]),
        const SizedBox(height: 16),
        Text(
          message,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Colors.grey[700],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          subtitle,
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 14, color: Colors.grey[600]),
        ),
      ],
    );
  }

  // ── Orders List ──────────────────────────────────────────────────────────

  Widget _buildOrdersList(OrdersProvider ordersProvider) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: ordersProvider.filteredOrders.length,
      itemBuilder: (context, index) {
        final order = ordersProvider.filteredOrders[index];
        return _buildOrderCard(order);
      },
    );
  }

  Widget _buildOrderCard(SellerOrder order) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () => _navigateToOrderDetail(order.id.toString()),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top row: order number + status badge
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '#${order.orderNumber}',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${order.customerName} • ${_formatDate(order.orderDate)}',
                          style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  ),
                  _buildStatusBadge(order.status),
                ],
              ),
              const SizedBox(height: 12),

              // Middle row: total + rider
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    formatMoney(order.totalAmount),
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                  if (order.riderName != null && order.riderName!.isNotEmpty)
                    Row(
                      children: [
                        Icon(Icons.delivery_dining, size: 16, color: Colors.blue[700]),
                        const SizedBox(width: 4),
                        Text(
                          order.riderName!,
                          style: TextStyle(fontSize: 12, color: Colors.blue[700], fontWeight: FontWeight.w500),
                        ),
                      ],
                    )
                  else
                    Text('Unassigned', style: TextStyle(fontSize: 12, color: Colors.grey[400])),
                ],
              ),

              // Action buttons row (Wrap prevents overflow on narrow screens)
              const SizedBox(height: 12),
              Wrap(
                alignment: WrapAlignment.end,
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildActionButton(
                    label: 'View',
                    icon: Icons.visibility_outlined,
                    color: const Color(0xFF2c5aa0),
                    onPressed: () => _navigateToOrderDetail(order.id.toString()),
                  ),
                  _buildActionButton(
                    label: 'Update',
                    icon: Icons.edit_outlined,
                    color: const Color(0xFF1e3a5f),
                    onPressed: () => _showUpdateStatusDialog(order),
                  ),
                  _buildActionButton(
                    label: 'Rider',
                    icon: Icons.delivery_dining,
                    color: const Color(0xFF2563eb),
                    onPressed: () => _showRequestRiderDialog(order),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onPressed,
  }) {
    return SizedBox(
      height: 32,
      child: ElevatedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 14),
        label: Text(label, style: const TextStyle(fontSize: 12)),
        style: ElevatedButton.styleFrom(
          backgroundColor: color,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          elevation: 1,
        ),
      ),
    );
  }

  // ── Status Badge ─────────────────────────────────────────────────────────

  Widget _buildStatusBadge(String status) {
    final color = _getStatusColor(status);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        _prettyStatus(status),
        style: TextStyle(
          fontSize: 11,
          color: color,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return Colors.orange;
      case 'packing':
        return Colors.blue;
      case 'packed':
        return const Color(0xFF3b82f6);
      case 'assigned_to_rider':
        return const Color(0xFF60a5fa);
      case 'picked_up':
        return const Color(0xFF2563eb);
      case 'on_the_way':
        return Colors.indigo;
      case 'delivered':
        return const Color(0xFF1e40af);
      case 'cancelled':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _prettyStatus(String status) {
    return status.replaceAll('_', ' ').split(' ').map((w) {
      if (w.isEmpty) return w;
      return w[0].toUpperCase() + w.substring(1).toLowerCase();
    }).join(' ');
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);
    if (difference.inDays == 0) return 'Today';
    if (difference.inDays == 1) return 'Yesterday';
    if (difference.inDays < 7) return '${difference.inDays} days ago';
    final months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return '${months[date.month - 1]} ${date.day}, ${date.year}';
  }
}
