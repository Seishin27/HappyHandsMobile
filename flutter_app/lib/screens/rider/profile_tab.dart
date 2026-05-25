import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/constants/app_constants.dart';
import '../../providers/auth_provider.dart';
import '../../providers/rider_provider.dart';

class RiderProfileTab extends StatefulWidget {
  const RiderProfileTab({super.key});

  @override
  State<RiderProfileTab> createState() => _RiderProfileTabState();
}

class _RiderProfileTabState extends State<RiderProfileTab> {
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
      context.read<RiderProvider>().loadProfile();
    });
  }

  @override
  Widget build(BuildContext context) {
    context.watch<AuthProvider>();
    _scheduleLoad();
    final rider = context.watch<RiderProvider>();

    if (rider.loadingProfile && rider.profile == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (rider.profileError != null && rider.profile == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 48),
              const SizedBox(height: 12),
              Text(rider.profileError!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.read<RiderProvider>().loadProfile(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final p = rider.profile;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Avatar
        Center(
          child: Container(
            width: 80,
            height: 80,
            decoration: const BoxDecoration(color: AppTheme.primaryBlue, shape: BoxShape.circle),
            child: const Icon(FontAwesomeIcons.motorcycle, color: Colors.white, size: 32),
          ),
        ),
        const SizedBox(height: 12),
        Center(
          child: Text(
            p?.name ?? '—',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.darkBlue),
          ),
        ),
        Center(
          child: Text(p?.email ?? '—', style: const TextStyle(color: AppTheme.mediumGray)),
        ),
        const SizedBox(height: 4),
        Center(
          child: _StatusChip(status: p?.status ?? ''),
        ),
        const SizedBox(height: 24),

        // Info card
        _InfoCard(
          children: [
            _InfoRow(icon: FontAwesomeIcons.phone, label: 'Phone', value: p?.phone ?? '—'),
            _InfoRow(icon: FontAwesomeIcons.motorcycle, label: 'Vehicle', value: p?.vehicleType ?? '—'),
          ],
        ),
        const SizedBox(height: 16),

        ElevatedButton.icon(
          onPressed: () => _openEditSheet(context, p),
          icon: const Icon(Icons.edit_outlined, size: 18),
          label: const Text('Edit Profile'),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () => _openChangePassword(context),
          icon: const Icon(Icons.lock_outline, size: 18),
          label: const Text('Change Password'),
        ),
      ],
    );
  }

  void _openEditSheet(BuildContext context, profile) {
    final nameCtrl = TextEditingController(text: profile?.name ?? '');
    final phoneCtrl = TextEditingController(text: profile?.phone ?? '');
    String? vehicleType = profile?.vehicleType;
    const vehicles = ['Motorcycle', 'Car', 'Van'];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setS) {
          return Padding(
            padding: EdgeInsets.only(
              left: 20, right: 20, top: 20,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('Edit Profile', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(labelText: 'Full Name', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: phoneCtrl,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(labelText: 'Phone', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: vehicleType,
                  decoration: const InputDecoration(labelText: 'Vehicle Type', border: OutlineInputBorder()),
                  items: vehicles.map((v) => DropdownMenuItem(value: v, child: Text(v))).toList(),
                  onChanged: (v) => setS(() => vehicleType = v),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: () async {
                    final fields = <String, String>{};
                    if (nameCtrl.text.trim().isNotEmpty) fields['ridername'] = nameCtrl.text.trim();
                    if (phoneCtrl.text.trim().isNotEmpty) fields['phone'] = phoneCtrl.text.trim();
                    if (vehicleType != null) fields['vehicle_type'] = vehicleType!;
                    Navigator.pop(ctx);
                    final ok = await context.read<RiderProvider>().saveProfile(fields);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text(ok ? 'Profile updated' : context.read<RiderProvider>().profileError ?? 'Failed'),
                        backgroundColor: ok ? AppTheme.successGreen : AppTheme.errorRed,
                      ));
                    }
                  },
                  child: const Text('Save Changes'),
                ),
              ],
            ),
          );
        });
      },
    );
  }

  void _openChangePassword(BuildContext context) {
    final currentCtrl = TextEditingController();
    final newCtrl = TextEditingController();
    final confirmCtrl = TextEditingController();
    String? localError;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setS) {
          return Padding(
            padding: EdgeInsets.only(
              left: 20, right: 20, top: 20,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('Change Password', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                TextField(
                  controller: currentCtrl,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Current Password', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: newCtrl,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'New Password', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: confirmCtrl,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Confirm New Password', border: OutlineInputBorder()),
                ),
                if (localError != null) ...[
                  const SizedBox(height: 8),
                  Text(localError!, style: const TextStyle(color: AppTheme.errorRed, fontSize: 13)),
                ],
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: () async {
                    if (newCtrl.text != confirmCtrl.text) {
                      setS(() => localError = 'Passwords do not match');
                      return;
                    }
                    if (newCtrl.text.length < 6) {
                      setS(() => localError = 'At least 6 characters required');
                      return;
                    }
                    Navigator.pop(ctx);
                    final ok = await context.read<RiderProvider>().changePassword(
                      currentPassword: currentCtrl.text,
                      newPassword: newCtrl.text,
                    );
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text(ok ? 'Password changed' : context.read<RiderProvider>().profileError ?? 'Failed'),
                        backgroundColor: ok ? AppTheme.successGreen : AppTheme.errorRed,
                      ));
                    }
                  },
                  child: const Text('Update Password'),
                ),
              ],
            ),
          );
        });
      },
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  Color get _color {
    switch (status.toLowerCase()) {
      case 'active':
      case 'approved': return AppTheme.successGreen;
      case 'pending':  return Colors.orange;
      default:         return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        decoration: BoxDecoration(
          color: _color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          status.isEmpty ? 'Unknown' : status[0].toUpperCase() + status.substring(1),
          style: TextStyle(color: _color, fontWeight: FontWeight.w600, fontSize: 12),
        ),
      );
}

class _InfoCard extends StatelessWidget {
  final List<Widget> children;
  const _InfoCard({required this.children});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppConstants.radiusMD),
          boxShadow: [
            BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 8, offset: const Offset(0, 2)),
          ],
        ),
        child: Column(
          children: children
              .expand((w) => [w, const Divider(height: 16)])
              .take(children.length * 2 - 1)
              .toList(),
        ),
      );
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _InfoRow({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 14, color: AppTheme.mediumGray),
          const SizedBox(width: 10),
          Text(label, style: const TextStyle(color: AppTheme.mediumGray, fontSize: 13)),
          const Spacer(),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.darkBlue)),
        ],
      );
}
