import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../seller/dashboard_tab.dart';
import '../seller/orders_tab.dart';
import '../seller/products_tab.dart';
import '../seller/chat_tab.dart';
import '../seller/profile_tab.dart';

class SellerShell extends StatefulWidget {
  const SellerShell({super.key});

  @override
  State<SellerShell> createState() => _SellerShellState();
}

class _SellerShellState extends State<SellerShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('Seller Dashboard'),
          actions: [
            IconButton(
              tooltip: 'Logout',
              onPressed: () async {
                await context.read<AuthProvider>().logout();
                if (!context.mounted) return;
                Navigator.pushNamedAndRemoveUntil(
                  context,
                  '/home',
                  (route) => false,
                );
              },
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: const DashboardTab(),
      ),
      Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('Seller Orders'),
          actions: [
            IconButton(
              tooltip: 'Logout',
              onPressed: () async {
                await context.read<AuthProvider>().logout();
                if (!context.mounted) return;
                Navigator.pushNamedAndRemoveUntil(
                  context,
                  '/home',
                  (route) => false,
                );
              },
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: const OrdersTab(),
      ),
      Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('Seller Products'),
          actions: [
            IconButton(
              tooltip: 'Logout',
              onPressed: () async {
                await context.read<AuthProvider>().logout();
                if (!context.mounted) return;
                Navigator.pushNamedAndRemoveUntil(
                  context,
                  '/home',
                  (route) => false,
                );
              },
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: const ProductsTab(),
      ),
      Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('Seller Chat'),
          actions: [
            IconButton(
              tooltip: 'Logout',
              onPressed: () async {
                await context.read<AuthProvider>().logout();
                if (!context.mounted) return;
                Navigator.pushNamedAndRemoveUntil(
                  context,
                  '/home',
                  (route) => false,
                );
              },
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: const ChatTab(),
      ),
      Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('Seller Profile'),
          actions: [
            IconButton(
              tooltip: 'Logout',
              onPressed: () async {
                await context.read<AuthProvider>().logout();
                if (!context.mounted) return;
                Navigator.pushNamedAndRemoveUntil(
                  context,
                  '/home',
                  (route) => false,
                );
              },
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: const ProfileTab(),
      ),
    ];

    return Scaffold(
      body: pages[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: 'Orders'),
          NavigationDestination(icon: Icon(Icons.inventory_2_outlined), selectedIcon: Icon(Icons.inventory_2), label: 'Products'),
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline), selectedIcon: Icon(Icons.chat_bubble), label: 'Chat'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}


