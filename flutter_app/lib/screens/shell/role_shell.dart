import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/role_provider.dart';
import '../../models/role.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_view.dart';
import 'main_shell.dart';
import 'seller_shell.dart';
import 'rider_shell.dart';

class RoleShell extends StatefulWidget {
  const RoleShell({super.key});

  @override
  State<RoleShell> createState() => _RoleShellState();
}

class _RoleShellState extends State<RoleShell> {
  bool _initialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_initialized) return;
    _initialized = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<RoleProvider>().refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final role = context.watch<RoleProvider>();
    if (role.isLoading) {
      return const Scaffold(body: LoadingWidget(label: 'Loading roles...'));
    }
    if (role.error != null) {
      return Scaffold(
        body: ErrorView(
          message: role.error!,
          onRetry: () => context.read<RoleProvider>().refresh(),
        ),
      );
    }

    // If user has multiple roles, show a simple picker once.
    final available = role.availableRoles;
    if (available.length > 1) {
      return Scaffold(
        appBar: AppBar(title: const Text('Choose role')),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text('This account can access multiple roles.'),
            const SizedBox(height: 12),
            ...available.map((r) {
              final selected = r == role.selectedRole;
              return Card(
                child: ListTile(
                  title: Text(r.key.toUpperCase()),
                  trailing: selected ? const Icon(Icons.check_circle) : null,
                  onTap: () => context.read<RoleProvider>().select(r),
                ),
              );
            }),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => setState(() {}),
              child: const Text('Continue'),
            ),
          ],
        ),
      );
    }

    // Single role → route directly.
    return switch (role.selectedRole) {
      // User/customer shell (existing)
      AppRole.user => const MainShell(),
      AppRole.seller => const SellerShell(),
      AppRole.rider => const RiderShell(),
    };
  }
}
