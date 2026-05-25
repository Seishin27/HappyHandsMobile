import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/utils/money.dart';
import '../../models/order_line_item.dart';
import '../../models/seller_order.dart';
import '../../providers/orders_provider.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';
import '../order_tracking_screen.dart';

/// Order detail screen for seller dashboard.
///
/// Matches the Flask web order detail modal with:
/// - Order header (number, date, status badge)
/// - Customer details
/// - Line items with product info
/// - Shipping address, contact, payment method
/// - Rider info
/// - Total amount
/// - Update Status action (dropdown + notes, matching Flask modal)
/// - Request Rider action (rider selection)
class OrderDetailScreen extends StatefulWidget {
  final String orderId;

  const OrderDetailScreen({
    super.key,
    required this.orderId,
  });

  @override
  State<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends State<OrderDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<OrdersProvider>().fetchOrderDetails(widget.orderId);
    });
  }

  @override
  void dispose() {
    context.read<OrdersProvider>().clearSelectedOrder();
    super.dispose();
  }

  // ── Valid status transitions matching Flask web ─────────────────────────
  // Seller can set: pending, packing, packed
  // Other statuses (assigned_to_rider, picked_up, on_the_way, delivered)
  // are set by the rider or system.

  List<String> _getSellerAllowedStatuses() {
    return ['pending', 'packing', 'packed'];
  }

  bool _canUpdateStatus(String currentStatus) {
    // Terminal statuses cannot be updated
    return currentStatus != 'delivered' && currentStatus != 'cancelled';
  }

  // ── Update Status Dialog (matching Flask modal) ─────────────────────────

  void _showUpdateStatusDialog(SellerOrder order) {
    if (!_canUpdateStatus(order.status)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Cannot update a ${_prettyStatus(order.status)} order'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    final allowedStatuses = _getSellerAllowedStatuses();
    String selectedStatus = allowedStatuses.contains(order.status)
        ? order.status
        : allowedStatuses.first;
    final notesController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              Icon(Icons.edit_note, color: const Color(0xFF2c5aa0)),
              const SizedBox(width: 8),
              const Text('Update Order Status'),
            ],
          ),
          content: Column(
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
                initialValue: selectedStatus,
                decoration: InputDecoration(
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                items: allowedStatuses.map((s) {
                  return DropdownMenuItem(
                    value: s,
                    child: Row(
                      children: [
                        Icon(_getStatusIcon(s), size: 16, color: _getStatusColor(s)),
                        const SizedBox(width: 8),
                        Text(_prettyStatus(s)),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (v) {
                  if (v != null) setDialogState(() => selectedStatus = v);
                },
              ),
              const SizedBox(height: 16),
              const Text('Notes (Optional):', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              TextField(
                controller: notesController,
                maxLines: 3,
                decoration: InputDecoration(
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  hintText: 'Add any additional notes...',
                ),
              ),
            ],
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
                        widget.orderId,
                        selectedStatus,
                        notes: notesController.text.trim().isNotEmpty
                            ? notesController.text.trim()
                            : null,
                      );
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Status updated to ${_prettyStatus(selectedStatus)}'),
                        backgroundColor: Colors.green,
                      ),
                    );
                    // Refresh details
                    context.read<OrdersProvider>().fetchOrderDetails(widget.orderId);
                    context.read<OrdersProvider>().fetchOrders();
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
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

  // ── Request Rider Dialog ────────────────────────────────────────────────

  void _showRequestRiderDialog(SellerOrder order) {
    final provider = context.read<OrdersProvider>();
    provider.fetchAvailableRiders();
    int? selectedRiderId;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                Icon(Icons.delivery_dining, color: const Color(0xFF2563eb)),
                const SizedBox(width: 8),
                const Text('Request Rider'),
              ],
            ),
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
                      child: Text(
                        'No active riders available right now.',
                        style: TextStyle(color: Colors.grey),
                        textAlign: TextAlign.center,
                      ),
                    );
                  }
                  return Column(
                    mainAxisSize: MainAxisSize.min,
                    children: prov.availableRiders.map((rider) {
                      return ListTile(
                        leading: Radio<int>(
                          value: rider.riderID,
                          groupValue: selectedRiderId,
                          onChanged: (v) => setDialogState(() => selectedRiderId = v),
                        ),
                        title: Text(rider.ridername, style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: Text(
                          [
                            if (rider.phone != null && rider.phone!.isNotEmpty) rider.phone!,
                            if (rider.rideremail != null && rider.rideremail!.isNotEmpty) rider.rideremail!,
                          ].join(' • '),
                          style: const TextStyle(fontSize: 12),
                        ),
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
                          await provider.assignRider(widget.orderId, selectedRiderId!);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Rider requested successfully'),
                                backgroundColor: Colors.green,
                              ),
                            );
                            provider.fetchOrderDetails(widget.orderId);
                            provider.fetchOrders();
                          }
                        } catch (e) {
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
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

  // ── Build ───────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final ordersProvider = context.watch<OrdersProvider>();

    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: const Text('Order Details'),
        actions: [
          if (ordersProvider.selectedOrder != null) ...[
            IconButton(
              icon: const Icon(Icons.edit_note),
              tooltip: 'Update Status',
              onPressed: () => _showUpdateStatusDialog(ordersProvider.selectedOrder!),
            ),
            IconButton(
              icon: const Icon(Icons.delivery_dining),
              tooltip: 'Request Rider',
              onPressed: () => _showRequestRiderDialog(ordersProvider.selectedOrder!),
            ),
          ],
        ],
      ),
      body: _buildBody(ordersProvider),
    );
  }

  Widget _buildBody(OrdersProvider ordersProvider) {
    if (ordersProvider.isLoading && ordersProvider.selectedOrder == null) {
      return const LoadingWidget(label: 'Loading order details...');
    }

    if (ordersProvider.error != null && ordersProvider.selectedOrder == null) {
      return ErrorView(
        message: ordersProvider.error!,
        onRetry: () => context.read<OrdersProvider>().fetchOrderDetails(widget.orderId),
      );
    }

    if (ordersProvider.selectedOrder == null) {
      return const ErrorView(message: 'Order not found');
    }

    final order = ordersProvider.selectedOrder!;

    return RefreshIndicator(
      onRefresh: () => context.read<OrdersProvider>().fetchOrderDetails(widget.orderId),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildOrderHeader(order),
            const SizedBox(height: 16),
            _buildCustomerDetails(order),
            const SizedBox(height: 16),
            _buildLineItems(order),
            const SizedBox(height: 16),
            _buildShippingDetails(order),
            const SizedBox(height: 16),
            _buildRiderInfo(order),
            const SizedBox(height: 16),
            _buildTotalAmount(order),
            const SizedBox(height: 16),
            _buildActionButtons(order, ordersProvider),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  // ── Order Header ────────────────────────────────────────────────────────

  Widget _buildOrderHeader(SellerOrder order) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          gradient: const LinearGradient(
            colors: [Color(0xFF2c5aa0), Color(0xFF1e3a5f)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        padding: const EdgeInsets.all(20),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Order #${order.orderNumber}',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _formatDateFull(order.orderDate),
                    style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.85)),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    order.customerName,
                    style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.85)),
                  ),
                ],
              ),
            ),
            _buildStatusBadge(order.status),
          ],
        ),
      ),
    );
  }

  // ── Customer Details ────────────────────────────────────────────────────

  Widget _buildCustomerDetails(SellerOrder order) {
    return _buildDetailCard(
      title: 'Customer Details',
      icon: Icons.person_outline,
      children: [
        _buildDetailRow(Icons.person, 'Name', order.customerName),
        if (order.contactNumber != null && order.contactNumber!.isNotEmpty)
          _buildDetailRow(Icons.phone, 'Contact', order.contactNumber!),
      ],
    );
  }

  // ── Line Items ──────────────────────────────────────────────────────────

  Widget _buildLineItems(SellerOrder order) {
    return _buildDetailCard(
      title: 'Order Items',
      icon: Icons.shopping_bag_outlined,
      children: [
        if (order.lineItems.isEmpty)
          Text('No items in this order', style: TextStyle(color: Colors.grey[600]))
        else
          ...order.lineItems.map((item) => _buildLineItem(item)),
      ],
    );
  }

  Widget _buildLineItem(OrderLineItem item) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.inventory_2_outlined, color: Colors.grey, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.productName,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 3),
                Text(
                  'Qty: ${item.quantity} × ${formatMoney(item.price)}',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
          Text(
            formatMoney(item.totalPrice),
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  // ── Shipping / Contact / Payment Details ─────────────────────────────────

  Widget _buildShippingDetails(SellerOrder order) {
    return _buildDetailCard(
      title: 'Delivery Details',
      icon: Icons.local_shipping_outlined,
      children: [
        if (order.shippingAddress != null && order.shippingAddress!.isNotEmpty)
          _buildDetailRow(Icons.location_on, 'Shipping Address', order.shippingAddress!),
        if (order.contactNumber != null && order.contactNumber!.isNotEmpty)
          _buildDetailRow(Icons.phone, 'Contact', order.contactNumber!),
        if (order.paymentMethod != null && order.paymentMethod!.isNotEmpty)
          _buildDetailRow(Icons.credit_card, 'Payment Method',
              _prettyStatus(order.paymentMethod!)),
        if ((order.shippingAddress == null || order.shippingAddress!.isEmpty) &&
            (order.paymentMethod == null || order.paymentMethod!.isEmpty))
          Text('No delivery details available', style: TextStyle(color: Colors.grey[600])),
      ],
    );
  }

  // ── Rider Info ──────────────────────────────────────────────────────────

  Widget _buildRiderInfo(SellerOrder order) {
    final isOnTheWay = order.status == 'on_the_way';
    return _buildDetailCard(
      title: 'Rider',
      icon: Icons.delivery_dining,
      children: [
        if (order.riderName != null && order.riderName!.isNotEmpty)
          _buildDetailRow(Icons.person, 'Assigned Rider', order.riderName!)
        else
          Row(
            children: [
              Icon(Icons.info_outline, size: 16, color: Colors.orange[700]),
              const SizedBox(width: 8),
              Text('No rider assigned', style: TextStyle(color: Colors.orange[700])),
            ],
          ),
        if (isOnTheWay) ...[
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              icon: const Icon(Icons.map_outlined),
              label: const Text('Track Rider'),
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => OrderTrackingScreen(
                    orderId: order.id,
                    pickupAddress: '',
                    deliveryAddress: order.shippingAddress ?? '',
                  ),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }

  // ── Total Amount ────────────────────────────────────────────────────────

  Widget _buildTotalAmount(SellerOrder order) {
    return Card(
      color: Colors.green.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Total Amount', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Text(
              formatMoney(order.totalAmount),
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.green),
            ),
          ],
        ),
      ),
    );
  }

  // ── Action Buttons ──────────────────────────────────────────────────────

  Widget _buildActionButtons(SellerOrder order, OrdersProvider ordersProvider) {
    if (!_canUpdateStatus(order.status)) {
      return Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(
                order.status == 'delivered' ? Icons.check_circle : Icons.cancel,
                color: order.status == 'delivered' ? Colors.green : Colors.red,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'This order is ${_prettyStatus(order.status)} and cannot be updated.',
                  style: TextStyle(color: Colors.grey[600]),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: ordersProvider.isLoading ? null : () => _showUpdateStatusDialog(order),
            icon: const Icon(Icons.edit_note),
            label: const Text('Update Status'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF2c5aa0),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: ElevatedButton.icon(
            onPressed: ordersProvider.isLoading ? null : () => _showRequestRiderDialog(order),
            icon: const Icon(Icons.delivery_dining),
            label: const Text('Request Rider'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF2563eb),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
        ),
      ],
    );
  }

  // ── Reusable Widgets ────────────────────────────────────────────────────

  Widget _buildDetailCard({
    required String title,
    required IconData icon,
    required List<Widget> children,
  }) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 18, color: const Color(0xFF2c5aa0)),
                const SizedBox(width: 8),
                Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 12),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: Colors.grey[500]),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: TextStyle(fontSize: 11, color: Colors.grey[500], fontWeight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text(value, style: const TextStyle(fontSize: 14)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        _prettyStatus(status),
        style: TextStyle(
          fontSize: 12,
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'pending':     return Colors.orange;
      case 'packing':     return Colors.blue;
      case 'packed':      return const Color(0xFF3b82f6);
      case 'assigned_to_rider': return const Color(0xFF60a5fa);
      case 'picked_up':   return const Color(0xFF2563eb);
      case 'on_the_way':  return Colors.indigo;
      case 'delivered':   return const Color(0xFF1e40af);
      case 'cancelled':   return Colors.red;
      default:            return Colors.grey;
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'pending':     return Icons.schedule;
      case 'packing':     return Icons.inventory;
      case 'packed':      return Icons.check_box;
      case 'assigned_to_rider': return Icons.person_pin;
      case 'picked_up':   return Icons.local_shipping;
      case 'on_the_way':  return Icons.delivery_dining;
      case 'delivered':   return Icons.check_circle;
      case 'cancelled':   return Icons.cancel;
      default:            return Icons.help_outline;
    }
  }

  String _prettyStatus(String status) {
    return status.replaceAll('_', ' ').split(' ').map((w) {
      if (w.isEmpty) return w;
      return w[0].toUpperCase() + w.substring(1).toLowerCase();
    }).join(' ');
  }

  String _formatDateFull(DateTime date) {
    final months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    final hour = date.hour > 12 ? date.hour - 12 : (date.hour == 0 ? 12 : date.hour);
    final ampm = date.hour >= 12 ? 'PM' : 'AM';
    return '${months[date.month - 1]} ${date.day}, ${date.year} at ${hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')} $ampm';
  }
}
