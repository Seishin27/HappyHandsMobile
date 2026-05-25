import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../rider/dashboard_tab.dart';
import '../rider/orders_tab.dart';
import '../rider/profile_tab.dart';
import '../rider/chat_tab.dart';

class RiderShell extends StatefulWidget {
  const RiderShell({super.key});

  @override
  State<RiderShell> createState() => _RiderShellState();
}

class _RiderShellState extends State<RiderShell> {
  int _index = 0;

  void _logout() async {
    await context.read<AuthProvider>().logout();
    if (!mounted) return;
    Navigator.pushNamedAndRemoveUntil(context, '/home', (route) => false);
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      Scaffold(
        appBar: AppBar(
          title: const Text('Rider Dashboard'),
          automaticallyImplyLeading: false,
          actions: [IconButton(tooltip: 'Logout', onPressed: _logout, icon: const Icon(Icons.logout))],
        ),
        body: const RiderDashboardTab(),
      ),
      Scaffold(
        appBar: AppBar(
          title: const Text('My Orders'),
          automaticallyImplyLeading: false,
          actions: [IconButton(tooltip: 'Logout', onPressed: _logout, icon: const Icon(Icons.logout))],
        ),
        body: const RiderOrdersTab(),
      ),
      Scaffold(
        appBar: AppBar(
          title: const Text('Messages'),
          automaticallyImplyLeading: false,
          actions: [IconButton(tooltip: 'Logout', onPressed: _logout, icon: const Icon(Icons.logout))],
        ),
        body: const RiderChatTab(),
      ),
      Scaffold(
        appBar: AppBar(
          title: const Text('My Profile'),
          automaticallyImplyLeading: false,
          actions: [IconButton(tooltip: 'Logout', onPressed: _logout, icon: const Icon(Icons.logout))],
        ),
        body: const RiderProfileTab(),
      ),
    ];

    return Scaffold(
      body: pages[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.local_shipping_outlined),
            selectedIcon: Icon(Icons.local_shipping),
            label: 'Orders',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: 'Chat',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
