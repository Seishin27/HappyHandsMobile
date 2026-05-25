import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';
import 'models/cart_item.dart';
import 'screens/home_screen.dart';
import 'screens/auth_screen.dart';
import 'screens/shell/seller_shell.dart';
import 'screens/shell/rider_shell.dart';
import 'screens/product_detail_screen.dart';
import 'screens/cart_screen.dart';
import 'screens/checkout_screen.dart';
import 'screens/about_screen.dart';
import 'screens/profile/profile_screen.dart';
import 'screens/seller/change_password_screen.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Happy Hands',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      initialRoute: '/',
      routes: {
        '/': (context) => const HomeScreen(),
        '/home': (context) => const HomeScreen(),
        '/auth': (context) => const AuthScreen(),
        '/user-dashboard': (context) => const HomeScreen(),
        '/seller-dashboard': (context) => const SellerShell(),
        '/rider-dashboard': (context) => const RiderShell(),
        '/seller/change-password': (context) => const ChangePasswordScreen(),
        '/product': (context) {
          final productId = ModalRoute.of(context)!.settings.arguments as int;
          return ProductDetailScreen(productId: productId);
        },
        '/cart': (context) => const CartScreen(),
        '/checkout': (context) {
          final args = ModalRoute.of(context)?.settings.arguments;
          final items = args is List<CartItem> ? args : <CartItem>[];
          return CheckoutScreen(selectedItems: items);
        },
        '/orders': (context) => ProfileScreen(initialTab: 1),
        '/profile': (context) {
          final initialTab =
              ModalRoute.of(context)?.settings.arguments as int? ?? 0;
          return ProfileScreen(initialTab: initialTab);
        },
        '/about': (context) => const AboutScreen(),
      },
      onGenerateRoute: (settings) {
        if (settings.name?.startsWith('/product/') == true) {
          final productId = int.tryParse(settings.name!.split('/')[2]) ?? 0;
          return MaterialPageRoute(
            builder: (context) => ProductDetailScreen(productId: productId),
            settings: settings,
          );
        }
        return null;
      },
    );
  }
}
