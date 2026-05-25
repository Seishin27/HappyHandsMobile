import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../models/rider_models.dart';
import '../../providers/auth_provider.dart';
import '../../providers/rider_provider.dart';
import '../../services/flask_api_service.dart';
import '../../services/location_service.dart';
import '../order_tracking_screen.dart';

class RiderOrdersTab extends StatefulWidget {
  const RiderOrdersTab({super.key});

  @override
  State<RiderOrdersTab> createState() => _RiderOrdersTabState();
}

class _RiderOrdersTabState extends State<RiderOrdersTab> {
  bool _fetchScheduled = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _scheduleLoad();
  }

  void _scheduleLoad() {
    if (_fetchScheduled) return;
    final auth = context.read<AuthProvider>();
    if (auth.isLoading || (auth.backendAccessToken ?? '').isEmpty) return;
    _fetchScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<RiderProvider>().loadActiveOrders();
      context.read<RiderProvider>().loadDeliveredOrders();
    });
  }

  @override
  Widget build(BuildContext context) {
    context.watch<AuthProvider>();
    _scheduleLoad();

    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          Container(
            color: Colors.white,
            child: TabBar(
              labelColor: AppTheme.primaryBlue,
              unselectedLabelColor: Colors.grey[600],
              indicatorColor: AppTheme.primaryBlue,
              tabs: const [
                Tab(text: 'Active'),
                Tab(text: 'Delivered'),
              ],
            ),
          ),
          const Expanded(
            child: TabBarView(
              children: [
                _ActiveOrdersView(),
                _DeliveredOrdersView(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ActiveOrdersView extends StatelessWidget {
  const _ActiveOrdersView();

  @override
  Widget build(BuildContext context) {
    final rider = context.watch<RiderProvider>();

    if (rider.loadingOrders && rider.activeOrders.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (rider.ordersError != null && rider.activeOrders.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 48),
              const SizedBox(height: 12),
              Text(rider.ordersError!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.read<RiderProvider>().loadActiveOrders(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => context.read<RiderProvider>().loadActiveOrders(),
      child: rider.activeOrders.isEmpty
          ? ListView(
              padding: const EdgeInsets.symmetric(vertical: 80, horizontal: 32),
              children: [
                const Icon(Icons.local_shipping_outlined, size: 72, color: Colors.grey),
                const SizedBox(height: 16),
                const Text('No active orders', textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.grey)),
                const SizedBox(height: 8),
                const Text('Orders assigned to you will appear here.',
                    textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
              ],
            )
          : ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: rider.activeOrders.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _OrderCard(order: rider.activeOrders[i]),
            ),
    );
  }
}

class _DeliveredOrdersView extends StatelessWidget {
  const _DeliveredOrdersView();

  @override
  Widget build(BuildContext context) {
    final rider = context.watch<RiderProvider>();

    if (rider.loadingDeliveredOrders && rider.deliveredOrders.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (rider.deliveredOrdersError != null && rider.deliveredOrders.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 48),
              const SizedBox(height: 12),
              Text(rider.deliveredOrdersError!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.read<RiderProvider>().loadDeliveredOrders(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => context.read<RiderProvider>().loadDeliveredOrders(),
      child: rider.deliveredOrders.isEmpty
          ? ListView(
              padding: const EdgeInsets.symmetric(vertical: 80, horizontal: 32),
              children: [
                const Icon(Icons.check_circle_outline, size: 72, color: Colors.grey),
                const SizedBox(height: 16),
                const Text('No delivered orders', textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.grey)),
                const SizedBox(height: 8),
                const Text('Orders you have successfully delivered will appear here.',
                    textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
              ],
            )
          : ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: rider.deliveredOrders.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _OrderCard(order: rider.deliveredOrders[i]),
            ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  final RiderOrder order;
  const _OrderCard({required this.order});

  @override
  Widget build(BuildContext context) {
    final status = order.status.toLowerCase();
    final isAssigned = status == 'assigned_to_rider';
    final isOnTheWay = status == 'on_the_way';
    final isDelivered = status == 'delivered';

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                Expanded(
                  child: Text(
                    order.orderNumber.isNotEmpty ? '#${order.orderNumber}' : '#${order.sellerOrderId}',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.darkBlue),
                  ),
                ),
                _StatusChip(status: order.displayStatus, raw: status),
              ],
            ),
            const Divider(height: 16),
            _InfoRow(icon: Icons.store_outlined, label: order.shopName),
            const SizedBox(height: 4),
            _InfoRow(icon: Icons.person_outline, label: order.userName),
            const SizedBox(height: 4),
            if (order.pickupAddress.isNotEmpty)
              _InfoRow(icon: Icons.location_on_outlined, label: 'Pickup: ${order.pickupAddress}'),
            if (order.deliveryAddress.isNotEmpty) ...[
              const SizedBox(height: 4),
              _InfoRow(icon: Icons.flag_outlined, label: 'Deliver: ${order.deliveryAddress}'),
            ],
            const SizedBox(height: 8),
            Row(
              children: [
                Text('₱${order.totalAmount.toStringAsFixed(2)}',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primaryBlue, fontSize: 16)),
                const Spacer(),
                if (isAssigned) ...[
                  _ActionButton(
                    label: 'Accept',
                    color: AppTheme.successGreen,
                    onTap: () => _respond(context, order.sellerOrderId, 'accept'),
                  ),
                  const SizedBox(width: 8),
                  _ActionButton(
                    label: 'Decline',
                    color: AppTheme.errorRed,
                    outlined: true,
                    onTap: () => _respond(context, order.sellerOrderId, 'decline'),
                  ),
                ] else if (isOnTheWay) ...[
                  _ActionButton(
                    label: 'My Route',
                    color: Colors.teal,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => OrderTrackingScreen(
                          orderId: order.sellerOrderId,
                          pickupAddress: order.pickupAddress,
                          deliveryAddress: order.deliveryAddress,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  _ActionButton(
                    label: 'Delivered',
                    color: AppTheme.successGreen,
                    onTap: () => _updateStatus(context, order.sellerOrderId, 'delivered'),
                  ),
                ] else if (status == 'picked_up' || status == 'packed') ...[
                  _ActionButton(
                    label: 'On the Way',
                    color: AppTheme.primaryBlue,
                    onTap: () => _updateStatus(context, order.sellerOrderId, 'on_the_way'),
                  ),
                ],
              ],
            ),

            // ── Proof of Delivery section (delivered orders only) ──────────
            if (isDelivered) ...[
              const SizedBox(height: 12),
              const Divider(height: 1),
              const SizedBox(height: 12),
              _PodSection(orderId: order.sellerOrderId),
            ],
          ],
        ),
      ),
    );
  }

  void _respond(BuildContext context, int orderId, String action) async {
    final ok = await context.read<RiderProvider>().respondToOrder(orderId, action);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(ok ? 'Order ${action}ed' : 'Failed to $action order'),
        backgroundColor: ok ? AppTheme.successGreen : AppTheme.errorRed,
      ));
    }
  }

  void _updateStatus(BuildContext context, int orderId, String status) async {
    final label = status == 'on_the_way' ? 'On the Way' : 'Delivered';
    final ok = await context.read<RiderProvider>().updateOrderStatus(orderId, status);
    if (ok && context.mounted) {
      final locationSvc = context.read<LocationService>();
      final api = context.read<FlaskApiService>();
      if (status == 'on_the_way') {
        locationSvc.startTracking(orderId, api);
      } else if (status == 'delivered') {
        locationSvc.stopTracking();
      }
    }
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(ok ? 'Marked as $label' : 'Failed to update status'),
        backgroundColor: ok ? AppTheme.successGreen : AppTheme.errorRed,
      ));
    }
  }
}

// ── POD Section Widget ────────────────────────────────────────────────────────

class _PodSection extends StatefulWidget {
  final int orderId;
  const _PodSection({required this.orderId});

  @override
  State<_PodSection> createState() => _PodSectionState();
}

class _PodSectionState extends State<_PodSection> {
  XFile? _pickedFile;
  Uint8List? _pickedBytes;
  bool _uploading = false;

  static const _allowedExtensions = ['jpg', 'jpeg', 'png'];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final rp = context.read<RiderProvider>();
      if (rp.podUrlFor(widget.orderId) == null) {
        rp.loadPodStatus(widget.orderId);
      }
    });
  }

  Future<void> _pickImage(ImageSource source) async {
    final picker = ImagePicker();
    XFile? file;
    try {
      file = await picker.pickImage(source: source, imageQuality: 85);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Permission denied. Please allow access in Settings.'),
          backgroundColor: AppTheme.errorRed,
        ));
      }
      return;
    }
    if (file == null) return;

    final ext = file.name.split('.').last.toLowerCase();
    if (!_allowedExtensions.contains(ext)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Only JPG, JPEG, and PNG files are accepted.'),
          backgroundColor: AppTheme.errorRed,
        ));
      }
      return;
    }

    // Read bytes once — works on both web and mobile
    final bytes = await file.readAsBytes();

    if (!mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => _PodPreviewDialog(bytes: bytes),
    );
    if (confirmed == true) {
      setState(() {
        _pickedFile = file;
        _pickedBytes = bytes;
      });
    }
  }

  void _showSourcePicker() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 8),
            Container(
              width: 40, height: 4,
              decoration: BoxDecoration(color: Colors.grey[300], borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.camera_alt_outlined, color: AppTheme.primaryBlue),
              title: const Text('Take Photo'),
              onTap: () { Navigator.pop(context); _pickImage(ImageSource.camera); },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined, color: AppTheme.primaryBlue),
              title: const Text('Choose from Gallery'),
              onTap: () { Navigator.pop(context); _pickImage(ImageSource.gallery); },
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  Future<void> _upload() async {
    if (_pickedFile == null || _pickedBytes == null) return;
    setState(() => _uploading = true);
    final rp = context.read<RiderProvider>();
    final ok = await rp.uploadPod(
      orderId: widget.orderId,
      bytes: _pickedBytes!,
      fileName: _pickedFile!.name,
    );
    if (!mounted) return;
    setState(() {
      _uploading = false;
      if (ok) {
        _pickedFile = null;
        _pickedBytes = null;
      }
    });
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok
          ? 'Proof of delivery uploaded successfully.'
          : (rp.podUploadError ?? 'Upload failed.')),
      backgroundColor: ok ? AppTheme.successGreen : AppTheme.errorRed,
    ));
  }

  @override
  Widget build(BuildContext context) {
    final rp = context.watch<RiderProvider>();
    final existingUrl = rp.podUrlFor(widget.orderId);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.camera_alt_outlined, size: 16, color: AppTheme.primaryBlue),
            const SizedBox(width: 6),
            const Text(
              'Proof of Delivery',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.darkBlue),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // Existing uploaded POD — show thumbnail only (no replace option)
        if (existingUrl != null && existingUrl.isNotEmpty) ...[
          _PodThumbnail(url: existingUrl),
        ] else ...[
          // Preview of newly picked image (web-safe: Image.memory)
          if (_pickedBytes != null) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.memory(
                _pickedBytes!,
                height: 160,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(height: 8),
          ],

          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _uploading ? null : _showSourcePicker,
                  icon: const Icon(Icons.add_a_photo_outlined, size: 16),
                  label: Text(
                    _pickedFile == null ? 'Upload Proof of Delivery' : 'Change Photo',
                    style: const TextStyle(fontSize: 12),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
              if (_pickedFile != null) ...[
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _uploading ? null : _upload,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.successGreen,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: _uploading
                      ? const SizedBox(
                          width: 16, height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Submit', style: TextStyle(fontSize: 12)),
                ),
              ],
            ],
          ),
        ],
      ],
    );
  }
}

// ── POD Thumbnail (tappable fullscreen) ───────────────────────────────────────

class _PodThumbnail extends StatelessWidget {
  final String url;
  const _PodThumbnail({required this.url});

  String _fullUrl(String path) {
    if (path.startsWith('http')) return path;
    // Resolve relative /uploads/... path against the API base
    try {
      final base = Uri.parse(
        const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:5500/api'),
      );
      final root = base.replace(path: '');
      return '$root$path';
    } catch (_) {
      return path;
    }
  }

  @override
  Widget build(BuildContext context) {
    final fullUrl = _fullUrl(url);
    return GestureDetector(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => _FullscreenImagePage(url: fullUrl)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Image.network(
          fullUrl,
          height: 160,
          width: double.infinity,
          fit: BoxFit.cover,
          loadingBuilder: (_, child, progress) => progress == null
              ? child
              : Container(
                  height: 160,
                  color: Colors.grey[100],
                  child: const Center(child: CircularProgressIndicator()),
                ),
          errorBuilder: (_, __, ___) => Container(
            height: 80,
            color: Colors.grey[100],
            child: const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.broken_image_outlined, color: Colors.grey),
                  SizedBox(height: 4),
                  Text('Image could not be loaded.', style: TextStyle(fontSize: 11, color: Colors.grey)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Fullscreen image viewer ───────────────────────────────────────────────────

class _FullscreenImagePage extends StatelessWidget {
  final String url;
  const _FullscreenImagePage({required this.url});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        iconTheme: const IconThemeData(color: Colors.white),
        title: const Text('Proof of Delivery', style: TextStyle(color: Colors.white)),
      ),
      body: Center(
        child: InteractiveViewer(
          child: Image.network(
            url,
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => const Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.broken_image_outlined, color: Colors.white54, size: 64),
                SizedBox(height: 8),
                Text('Image could not be loaded.', style: TextStyle(color: Colors.white54)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── POD Preview Dialog ────────────────────────────────────────────────────────

class _PodPreviewDialog extends StatelessWidget {
  final Uint8List bytes;
  const _PodPreviewDialog({required this.bytes});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Preview'),
      content: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Image.memory(bytes, fit: BoxFit.cover),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Retake'),
        ),
        ElevatedButton(
          onPressed: () => Navigator.pop(context, true),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primaryBlue,
            foregroundColor: Colors.white,
          ),
          child: const Text('Use This Photo'),
        ),
      ],
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  final String raw;
  const _StatusChip({required this.status, required this.raw});

  Color get _color {
    switch (raw) {
      case 'assigned_to_rider': return Colors.orange;
      case 'on_the_way':        return AppTheme.primaryBlue;
      case 'delivered':         return AppTheme.successGreen;
      case 'packed':            return Colors.purple;
      default:                  return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(status, style: TextStyle(color: _color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  const _InfoRow({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: AppTheme.mediumGray),
          const SizedBox(width: 6),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 12, color: AppTheme.mediumGray))),
        ],
      );
}

class _ActionButton extends StatelessWidget {
  final String label;
  final Color color;
  final bool outlined;
  final VoidCallback onTap;

  const _ActionButton({
    required this.label,
    required this.color,
    required this.onTap,
    this.outlined = false,
  });

  @override
  Widget build(BuildContext context) {
    if (outlined) {
      return OutlinedButton(
        onPressed: onTap,
        style: OutlinedButton.styleFrom(
          foregroundColor: color,
          side: BorderSide(color: color),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          minimumSize: Size.zero,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: Text(label, style: const TextStyle(fontSize: 12)),
      );
    }
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: Text(label, style: const TextStyle(fontSize: 12)),
    );
  }
}
