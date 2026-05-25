import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/rider_provider.dart';

class RiderDashboardTab extends StatefulWidget {
  const RiderDashboardTab({super.key});

  @override
  State<RiderDashboardTab> createState() => _RiderDashboardTabState();
}

class _RiderDashboardTabState extends State<RiderDashboardTab> {
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
      context.read<RiderProvider>().loadDashboard();
    });
  }

  @override
  Widget build(BuildContext context) {
    context.watch<AuthProvider>();
    _scheduleLoad();
    final rider = context.watch<RiderProvider>();
    final stats = rider.stats;

    return RefreshIndicator(
      onRefresh: () => context.read<RiderProvider>().loadDashboard(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (rider.statsError != null)
            _ErrorBanner(message: rider.statsError!, onRetry: () => context.read<RiderProvider>().loadStats()),
          _WelcomeBanner(),
          const SizedBox(height: 16),
          _SectionTitle('My Performance'),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _KpiCard(
                icon: Icons.local_shipping,
                color: AppTheme.primaryBlue,
                label: 'Total Deliveries',
                value: '${stats.totalDeliveries}',
                loading: rider.loadingStats,
              )),
              const SizedBox(width: 12),
              Expanded(child: _KpiCard(
                icon: Icons.pending_actions,
                color: Colors.orange,
                label: 'Active Orders',
                value: '${stats.activeOrders}',
                loading: rider.loadingStats,
              )),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _KpiCard(
                icon: Icons.check_circle_outline,
                color: AppTheme.successGreen,
                label: 'Done Today',
                value: '${stats.completedToday}',
                loading: rider.loadingStats,
              )),
              const SizedBox(width: 12),
              Expanded(child: _KpiCard(
                icon: Icons.account_balance_wallet_outlined,
                color: Colors.teal,
                label: 'Total Earnings',
                value: '₱${stats.totalEarnings.toStringAsFixed(0)}',
                loading: rider.loadingStats,
              )),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _KpiCard(
                icon: Icons.calendar_today_outlined,
                color: Colors.purple,
                label: 'This Week',
                value: '₱${stats.earningsWeek.toStringAsFixed(0)}',
                loading: rider.loadingStats,
              )),
              const SizedBox(width: 12),
              Expanded(child: _KpiCard(
                icon: Icons.calendar_month_outlined,
                color: Colors.indigo,
                label: 'This Month',
                value: '₱${stats.earningsMonth.toStringAsFixed(0)}',
                loading: rider.loadingStats,
              )),
            ],
          ),
        ],
      ),
    );
  }
}

class _WelcomeBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final name = auth.user?.displayName ?? 'Rider';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF2C5AA0), Color(0xFF1E3A5F)],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF2C5AA0).withValues(alpha: 0.3),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.motorcycle, color: Colors.white, size: 28),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Welcome back, $name!',
                    style: const TextStyle(
                        color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16)),
                const SizedBox(height: 3),
                const Text('Ready for your next delivery?',
                    style: TextStyle(color: Colors.white70, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: Color(0xFF1E293B),
        ),
      );
}

class _KpiCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  final String value;
  final bool loading;

  const _KpiCard({
    required this.icon,
    required this.color,
    required this.label,
    required this.value,
    required this.loading,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 12, offset: const Offset(0, 4)),
        ],
      ),
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
          loading
              ? const SizedBox(height: 20, width: 40, child: LinearProgressIndicator())
              : Text(value,
                  style: const TextStyle(
                      fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.darkBlue)),
          const SizedBox(height: 4),
          Text(label,
              style: const TextStyle(fontSize: 11, color: AppTheme.mediumGray),
              maxLines: 1,
              overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorBanner({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.errorRed.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.errorRed.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: const TextStyle(color: AppTheme.errorRed, fontSize: 13))),
          TextButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
