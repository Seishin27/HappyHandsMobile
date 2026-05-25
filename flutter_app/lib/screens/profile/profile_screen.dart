import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../../providers/auth_provider.dart';
import '../../providers/user_orders_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../core/constants/app_constants.dart';
import '../../core/config/app_config.dart';
import '../../widgets/custom_app_bar.dart';
import '../auth_screen.dart';
import '../order_tracking_screen.dart';

class ProfileScreen extends StatefulWidget {
  final int initialTab;
  const ProfileScreen({super.key, this.initialTab = 0});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  int _selectedTab = 0;
  bool _ordersFetched = false;

  @override
  void initState() {
    super.initState();
    _selectedTab = widget.initialTab;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Wait until auth is fully loaded and token is available before fetching
    final auth = context.read<AuthProvider>();
    if (!_ordersFetched && !auth.isLoading && (auth.backendAccessToken ?? '').isNotEmpty) {
      _ordersFetched = true;
      context.read<UserOrdersProvider>().fetchOrders();
    }
  }

  final List<_ProfileTab> _tabs = const [
    _ProfileTab(icon: FontAwesomeIcons.user, label: 'Edit Profile'),
    _ProfileTab(icon: FontAwesomeIcons.bagShopping, label: 'My Orders'),
    _ProfileTab(icon: FontAwesomeIcons.commentDots, label: 'Messages'),
    _ProfileTab(icon: FontAwesomeIcons.gear, label: 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;

    // Trigger order fetch once auth is ready (handles late session restore)
    if (!_ordersFetched && !auth.isLoading && (auth.backendAccessToken ?? '').isNotEmpty) {
      _ordersFetched = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.read<UserOrdersProvider>().fetchOrders();
      });
    }

    if (user == null) {
      return Scaffold(
        backgroundColor: AppTheme.white,
        appBar: CustomAppBar(title: 'Profile', showBackButton: true),
        body: _buildNotLoggedIn(),
      );
    }

    final screenWidth = MediaQuery.of(context).size.width;
    final isWide = screenWidth >= 768;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      backgroundColor: const Color(0xFFF9FAFB),
      appBar: CustomAppBar(
        title: 'Happy Hands',
        showBackButton: true,
        onBackTap: () =>
            Navigator.pushNamedAndRemoveUntil(context, '/home', (r) => false),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppConstants.spacingLG),
        child: isWide
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(width: 260, child: _buildSidebar(user, auth)),
                  const SizedBox(width: AppConstants.spacingLG),
                  Expanded(child: _buildContent(user)),
                ],
              )
            : Column(
                children: [
                  _buildSidebar(user, auth),
                  const SizedBox(height: AppConstants.spacingLG),
                  _buildContent(user),
                ],
              ),
      ),
    );
  }

  Widget _buildSidebar(dynamic user, AuthProvider auth) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.borderGray),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 6,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(AppConstants.spacingLG),
      child: Column(
        children: [
          // Avatar
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppTheme.lightGray,
              border: Border.all(color: AppTheme.borderGray, width: 3),
            ),
            child: const Center(
              child: Icon(Icons.person, size: 48, color: AppTheme.mediumGray),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            user.displayName,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: AppTheme.darkBlue,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Text(
            user.email,
            style: const TextStyle(fontSize: 13, color: AppTheme.mediumGray),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppConstants.spacingLG),
          const Divider(color: AppTheme.borderGray),
          const SizedBox(height: AppConstants.spacingSM),
          // Nav buttons
          ...List.generate(_tabs.length, (i) {
            final tab = _tabs[i];
            final active = _selectedTab == i;
            return Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Material(
                color: active
                    ? AppTheme.primaryBlue.withValues(alpha: 0.08)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
                child: InkWell(
                  borderRadius: BorderRadius.circular(10),
                  onTap: () => setState(() => _selectedTab = i),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          tab.icon,
                          size: 16,
                          color: active
                              ? AppTheme.primaryBlue
                              : AppTheme.mediumGray,
                        ),
                        const SizedBox(width: 12),
                        Text(
                          tab.label,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: active
                                ? FontWeight.w600
                                : FontWeight.w400,
                            color: active
                                ? AppTheme.primaryBlue
                                : AppTheme.darkBlue,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
          const SizedBox(height: AppConstants.spacingMD),
          const Divider(color: AppTheme.borderGray),
          const SizedBox(height: AppConstants.spacingSM),
          // Logout
          Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () async {
                await context.read<AuthProvider>().logout();
                if (!mounted) return;
                Navigator.pushNamedAndRemoveUntil(
                  context,
                  '/home',
                  (r) => false,
                );
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12,
                ),
                child: Row(
                  children: [
                    Icon(
                      FontAwesomeIcons.rightFromBracket,
                      size: 16,
                      color: AppTheme.errorRed,
                    ),
                    const SizedBox(width: 12),
                    const Text(
                      'Logout',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.errorRed,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(dynamic user) {
    switch (_selectedTab) {
      case 0:
        return _buildEditProfile(user);
      case 1:
        return _buildMyOrders();
      case 2:
        return _buildMessages();
      case 3:
        return _buildSettings();
      default:
        return _buildEditProfile(user);
    }
  }

  Widget _buildEditProfile(dynamic user) {
    return _ProfileCard(
      title: 'Edit Profile',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ProfileField(label: 'Username', value: user.username ?? ''),
          const SizedBox(height: AppConstants.spacingMD),
          _ProfileField(label: 'Email', value: user.email),
          const SizedBox(height: AppConstants.spacingMD),
          _ProfileField(label: 'User ID', value: '#${user.id}', readOnly: true),
          const SizedBox(height: AppConstants.spacingLG),
          SizedBox(
            width: double.infinity,
            height: 46,
            child: ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryBlue,
                foregroundColor: AppTheme.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppConstants.radiusLG),
                ),
              ),
              child: const Text(
                'Save Changes',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMyOrders() {
    return Consumer<UserOrdersProvider>(
      builder: (context, ordersProvider, _) {
        if (ordersProvider.isLoading) {
          return _ProfileCard(
            title: 'My Orders',
            child: const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 40),
                child: CircularProgressIndicator(),
              ),
            ),
          );
        }

        if (ordersProvider.error != null) {
          return _ProfileCard(
            title: 'My Orders',
            child: Column(
              children: [
                const SizedBox(height: AppConstants.spacingXL),
                const Icon(Icons.error_outline, size: 48, color: AppTheme.errorRed),
                const SizedBox(height: AppConstants.spacingMD),
                Text(ordersProvider.error!, style: const TextStyle(fontSize: 14, color: AppTheme.errorRed), textAlign: TextAlign.center),
                const SizedBox(height: AppConstants.spacingMD),
                ElevatedButton(
                  onPressed: () => ordersProvider.fetchOrders(),
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryBlue, foregroundColor: AppTheme.white),
                  child: const Text('Retry'),
                ),
                const SizedBox(height: AppConstants.spacingXL),
              ],
            ),
          );
        }

        if (ordersProvider.filteredOrders.isEmpty) {
          return _ProfileCard(
            title: 'My Orders',
            child: Column(
              children: [
                const SizedBox(height: AppConstants.spacingXL),
                Icon(FontAwesomeIcons.bagShopping, size: 48, color: AppTheme.mediumGray),
                const SizedBox(height: AppConstants.spacingMD),
                const Text('No orders yet', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppTheme.darkBlue)),
                const SizedBox(height: 6),
                const Text('Your order history will appear here.', style: TextStyle(fontSize: 13, color: AppTheme.mediumGray)),
                const SizedBox(height: AppConstants.spacingMD),
                ElevatedButton(
                  onPressed: () => ordersProvider.fetchOrders(),
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryBlue, foregroundColor: AppTheme.white),
                  child: const Text('Refresh'),
                ),
                const SizedBox(height: AppConstants.spacingXL),
              ],
            ),
          );
        }

        return _ProfileCard(
          title: 'My Orders',
          child: ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: ordersProvider.filteredOrders.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final order = ordersProvider.filteredOrders[index];
              return _OrderCard(order: order, provider: ordersProvider);
            },
          ),
        );
      },
    );
  }

  Widget _buildMessages() {
    return _ProfileCard(
      title: 'Messages',
      child: Column(
        children: [
          const SizedBox(height: AppConstants.spacingXL),
          Icon(
            FontAwesomeIcons.commentDots,
            size: 48,
            color: AppTheme.mediumGray,
          ),
          const SizedBox(height: AppConstants.spacingMD),
          const Text(
            'No messages',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: AppTheme.darkBlue,
            ),
          ),
          const SizedBox(height: AppConstants.spacingXL),
        ],
      ),
    );
  }

  Widget _buildSettings() {
    return _ProfileCard(
      title: 'Settings',
      child: Column(
        children: [
          _SettingsTile(
            icon: FontAwesomeIcons.bell,
            label: 'Notifications',
            onTap: () {},
          ),
          _SettingsTile(
            icon: FontAwesomeIcons.lock,
            label: 'Change Password',
            onTap: () {},
          ),
          _SettingsTile(
            icon: FontAwesomeIcons.shieldHalved,
            label: 'Privacy',
            onTap: () {},
          ),
        ],
      ),
    );
  }

  Widget _buildNotLoggedIn() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              FontAwesomeIcons.userLock,
              size: 64,
              color: AppTheme.mediumGray,
            ),
            const SizedBox(height: AppConstants.spacingMD),
            const Text(
              'Sign in to view your profile',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppTheme.darkBlue,
              ),
            ),
            const SizedBox(height: AppConstants.spacingXL),
            SizedBox(
              width: 200,
              height: 46,
              child: ElevatedButton(
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const AuthScreen()),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: AppTheme.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(AppConstants.radiusLG),
                  ),
                ),
                child: const Text('Login'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileTab {
  final IconData icon;
  final String label;
  const _ProfileTab({required this.icon, required this.label});
}

// ── Order Card (matches web design) ──────────────────────────────────────────

class _OrderCard extends StatefulWidget {
  final Map<String, dynamic> order;
  final UserOrdersProvider provider;
  const _OrderCard({required this.order, required this.provider});

  @override
  State<_OrderCard> createState() => _OrderCardState();
}

class _OrderCardState extends State<_OrderCard> {
  bool _confirmingReceived = false;
  String? _podImageUrl; // fetched separately if not in order data

  @override
  void initState() {
    super.initState();
    // Always fetch fresh POD status for delivered/confirmed orders
    final rawStatus = (widget.order['status']?.toString() ?? '').toLowerCase();
    final isDelivered = rawStatus == 'delivered' || rawStatus == 'confirmed';
    if (isDelivered) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _fetchPod());
    }
  }

  Future<void> _fetchPod() async {
    final rawId = widget.order['sellerOrderID'] ?? widget.order['id'];
    final id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '') ?? 0;
    if (id == 0 || !mounted) return;
    try {
      final provider = context.read<UserOrdersProvider>();
      final result = await provider.fetchPodForOrder(id);
      if (mounted && result != null && result.isNotEmpty) {
        setState(() => _podImageUrl = result);
      }
    } catch (_) {}
  }

  Map<String, dynamic> get o => widget.order;

  String get orderNumber => o['order_number']?.toString() ?? '#${o['id'] ?? ''}';
  String get status => (o['status']?.toString() ?? 'pending').toLowerCase();
  // Treat 'confirmed' (user_pending_orders) as 'delivered' for display/logic
  String get normalizedStatus => status == 'confirmed' ? 'delivered' : status;
  String get displayStatus {
    switch (normalizedStatus) {
      case 'delivered':         return 'DELIVERED';
      case 'on_the_way':        return 'ON THE WAY';
      case 'assigned_to_rider': return 'ASSIGNED';
      case 'picked_up':         return 'PICKED UP';
      case 'packing':           return 'PACKING';
      case 'packed':            return 'PACKED';
      case 'pending':           return 'PENDING';
      case 'cancelled':         return 'CANCELLED';
      default:                  return status.replaceAll('_', ' ').toUpperCase();
    }
  }
  double get total => (o['totalAmount'] ?? o['total'] ?? 0.0).toDouble();
  bool get buyerReceived => o['buyer_received'] == true;
  String? get podImageUrl => o['pod_image_url']?.toString().isNotEmpty == true
      ? o['pod_image_url']?.toString()
      : _podImageUrl;
  String get createdAt => o['orderDate']?.toString() ?? o['created_at']?.toString() ?? '';
  List<dynamic> get items => (o['items'] as List<dynamic>? ?? []);
  int get sellerOrderId {
    final rawId = o['sellerOrderID'] ?? o['id'];
    return rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '') ?? 0;
  }

  Color get statusColor {
    switch (normalizedStatus) {
      case 'delivered':         return AppTheme.successGreen;
      case 'on_the_way':        return const Color(0xFF3B82F6);
      case 'packing':
      case 'packed':
      case 'assigned_to_rider':
      case 'picked_up':         return const Color(0xFFF59E0B);
      case 'cancelled':         return AppTheme.errorRed;
      default:                  return AppTheme.mediumGray;
    }
  }

  Future<void> _confirmReceived() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Confirm Receipt'),
        content: const Text('Have you received your order? This will release payment to the seller.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryBlue, foregroundColor: Colors.white),
            child: const Text('Yes, I received it'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _confirmingReceived = true);
    final ok = await widget.provider.confirmOrderReceived(sellerOrderId);
    if (!mounted) return;
    setState(() => _confirmingReceived = false);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(ok ? 'Order confirmed as received!' : (widget.provider.error ?? 'Failed to confirm.')),
      backgroundColor: ok ? AppTheme.successGreen : AppTheme.errorRed,
    ));
  }

  void _viewPod() {
    if (podImageUrl == null || podImageUrl!.isEmpty) return;
    final fullUrl = _resolveUrl(podImageUrl!);
    Navigator.push(context, MaterialPageRoute(builder: (_) => _PodViewerPage(url: fullUrl)));
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderGray),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 4, offset: const Offset(0, 2))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header ──────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Order #$orderNumber',
                          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.darkBlue),
                          overflow: TextOverflow.ellipsis),
                      if (createdAt.isNotEmpty)
                        Text(_formatDate(createdAt),
                            style: const TextStyle(fontSize: 11, color: AppTheme.mediumGray)),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                  ),
                  child: Text(displayStatus,
                      style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: statusColor)),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppTheme.borderGray),

          // ── Product items table ──────────────────────────────────────────
          if (items.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Column(
                children: [
                  // Table header
                  Row(
                    children: const [
                      Expanded(flex: 5, child: Text('PRODUCT', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.mediumGray))),
                      Expanded(flex: 2, child: Text('QTY', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.mediumGray), textAlign: TextAlign.center)),
                      Expanded(flex: 3, child: Text('TOTAL', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.mediumGray), textAlign: TextAlign.right)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ...items.map<Widget>((item) {
                    final m = item is Map<String, dynamic> ? item : <String, dynamic>{};
                    final name = m['name']?.toString() ?? 'Product';
                    final qty = (m['quantity'] ?? 1) as int;
                    final price = (m['price'] ?? 0.0).toDouble();
                    final imgPath = m['image_path']?.toString() ?? '';
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            flex: 5,
                            child: Row(
                              children: [
                                if (imgPath.isNotEmpty)
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(4),
                                    child: Image.network(
                                      imgPath.startsWith('http') ? imgPath : _resolveUrl(imgPath),
                                      width: 36, height: 36, fit: BoxFit.cover,
                                      errorBuilder: (_, __, ___) => Container(width: 36, height: 36, color: AppTheme.lightGray,
                                          child: const Icon(Icons.image_not_supported_outlined, size: 16, color: AppTheme.mediumGray)),
                                    ),
                                  )
                                else
                                  Container(width: 36, height: 36, decoration: BoxDecoration(color: AppTheme.lightGray, borderRadius: BorderRadius.circular(4)),
                                      child: const Icon(Icons.image_outlined, size: 16, color: AppTheme.mediumGray)),
                                const SizedBox(width: 8),
                                Expanded(child: Text(name, style: const TextStyle(fontSize: 12, color: AppTheme.darkBlue), maxLines: 2, overflow: TextOverflow.ellipsis)),
                              ],
                            ),
                          ),
                          Expanded(flex: 2, child: Text('$qty', style: const TextStyle(fontSize: 12, color: AppTheme.darkBlue), textAlign: TextAlign.center)),
                          Expanded(flex: 3, child: Text('₱${(price * qty).toStringAsFixed(2)}',
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.darkBlue), textAlign: TextAlign.right)),
                        ],
                      ),
                    );
                  }),
                  const SizedBox(height: 6),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      const Text('Total  ', style: TextStyle(fontSize: 13, color: AppTheme.mediumGray)),
                      Text('₱${total.toStringAsFixed(2)}',
                          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.darkBlue)),
                    ],
                  ),
                ],
              ),
            ),

          const Divider(height: 1, color: AppTheme.borderGray),

          // ── Footer: note + action buttons ────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Note text
                if (normalizedStatus == 'delivered') ...[
                  if (buyerReceived)
                    const Text('✓ You confirmed receipt. Thanks for letting us know!',
                        style: TextStyle(fontSize: 12, color: AppTheme.successGreen))
                  else
                    const Text('Please confirm once you have received your items so we can release the payment to the seller.',
                        style: TextStyle(fontSize: 12, color: AppTheme.mediumGray)),
                  const SizedBox(height: 10),
                ],

                // Action buttons row
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    // Track Order button — visible while rider is on the way
                    if (normalizedStatus == 'on_the_way')
                      ElevatedButton.icon(
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => OrderTrackingScreen(
                              orderId: sellerOrderId,
                              pickupAddress: '',
                              deliveryAddress: o['shipping_address']?.toString() ?? '',
                            ),
                          ),
                        ),
                        icon: const Icon(Icons.map_outlined, size: 14),
                        label: const Text('Track Order', style: TextStyle(fontSize: 12)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.teal,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          elevation: 0,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),

                    // Order Received button
                    if (normalizedStatus == 'delivered' && !buyerReceived)
                      ElevatedButton.icon(
                        onPressed: _confirmingReceived ? null : _confirmReceived,
                        icon: _confirmingReceived
                            ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.check, size: 14),
                        label: const Text('Order Received', style: TextStyle(fontSize: 12)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.darkBlue,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          elevation: 0,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),

                    // View Proof of Delivery button
                    if (normalizedStatus == 'delivered' && podImageUrl != null && podImageUrl!.isNotEmpty)
                      OutlinedButton.icon(
                        onPressed: _viewPod,
                        icon: const Icon(Icons.camera_alt_outlined, size: 14),
                        label: const Text('View Proof of Delivery', style: TextStyle(fontSize: 12)),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.primaryBlue,
                          side: const BorderSide(color: AppTheme.primaryBlue),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),

                    // Report Issue button
                    if (normalizedStatus == 'delivered' && !buyerReceived)
                      OutlinedButton.icon(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Report Issue feature coming soon.')),
                          );
                        },
                        icon: const Icon(Icons.flag_outlined, size: 14),
                        label: const Text('Report Issue', style: TextStyle(fontSize: 12)),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.errorRed,
                          side: const BorderSide(color: AppTheme.errorRed),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(String raw) {
    try {
      final dt = DateTime.parse(raw);
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      final h = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
      final ampm = dt.hour >= 12 ? 'PM' : 'AM';
      final m = dt.minute.toString().padLeft(2, '0');
      return '${months[dt.month - 1]} ${dt.day}, ${dt.year} at $h:$m $ampm';
    } catch (_) {
      return raw.split('T')[0];
    }
  }

  String _resolveUrl(String path) {
    if (path.startsWith('http')) return path;
    // Strip leading /uploads/ and use AppConfig.uploadsBaseUrl
    final stripped = path.startsWith('/uploads/')
        ? path.substring('/uploads/'.length)
        : path.startsWith('/')
            ? path.substring(1)
            : path;
    return '${AppConfig.uploadsBaseUrl}/$stripped';
  }
}

// ── POD Viewer Page ───────────────────────────────────────────────────────────

class _PodViewerPage extends StatelessWidget {
  final String url;
  const _PodViewerPage({required this.url});

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
            loadingBuilder: (_, child, progress) => progress == null
                ? child
                : const Center(child: CircularProgressIndicator(color: Colors.white)),
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

class _ProfileCard extends StatelessWidget {
  final String title;
  final Widget child;
  const _ProfileCard({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.borderGray),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 6,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(AppConstants.spacingLG),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w700,
              color: AppTheme.darkBlue,
            ),
          ),
          const SizedBox(height: AppConstants.spacingMD),
          const Divider(color: AppTheme.borderGray),
          const SizedBox(height: AppConstants.spacingMD),
          child,
        ],
      ),
    );
  }
}

class _ProfileField extends StatelessWidget {
  final String label;
  final String value;
  final bool readOnly;
  const _ProfileField({
    required this.label,
    required this.value,
    this.readOnly = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: AppTheme.mediumGray,
          ),
        ),
        const SizedBox(height: 6),
        TextFormField(
          initialValue: value,
          readOnly: readOnly,
          decoration: InputDecoration(
            filled: true,
            fillColor: readOnly ? const Color(0xFFF9FAFB) : AppTheme.white,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 12,
            ),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppTheme.borderGray),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppTheme.borderGray),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppTheme.primaryBlue),
            ),
          ),
          style: TextStyle(
            fontSize: 14,
            color: readOnly ? AppTheme.mediumGray : AppTheme.darkBlue,
          ),
        ),
      ],
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _SettingsTile({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
          child: Row(
            children: [
              Icon(icon, size: 18, color: AppTheme.primaryBlue),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 14,
                    color: AppTheme.darkBlue,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const Icon(
                Icons.chevron_right,
                size: 20,
                color: AppTheme.mediumGray,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
