import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'core/network/api_client.dart';
import 'providers/auth_provider.dart';
import 'providers/role_provider.dart';
import 'providers/product_provider.dart';
import 'providers/cart_provider.dart';
import 'providers/products_provider.dart';
import 'providers/orders_provider.dart';
import 'providers/user_orders_provider.dart';
import 'providers/seller_provider.dart';
import 'providers/profile_provider.dart';
import 'providers/chat_provider.dart';
import 'providers/rider_provider.dart';
import 'providers/rider_chat_provider.dart';
import 'services/flask_api_service.dart';
import 'services/location_service.dart';
import 'firebase_options.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase is initialized for legacy reasons (some platform plumbing
  // expects it). Authentication AND product data both flow through Flask.
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  runApp(
    MultiProvider(
      providers: [
        // MySQL/Flask auth — no Firebase Auth
        ChangeNotifierProvider(create: (_) => AuthProvider()),

        // Flask API client — uses JWT from AuthProvider, auto-refreshes on 401
        ProxyProvider<AuthProvider, ApiClient>(
          update: (context, authProvider, previous) =>
              ApiClient(
                tokenProvider: () async => authProvider.getIdToken(),
                onRefresh: () async => authProvider.refreshToken(),
              ),
        ),

        // Flask API service
        ProxyProvider2<ApiClient, AuthProvider, FlaskApiService>(
          update: (context, apiClient, authProvider, previous) =>
              FlaskApiService(
                apiClient,
                tokenProvider: () async => authProvider.getIdToken(),
              ),
        ),

        // Products via Flask/MySQL
        ChangeNotifierProxyProvider<FlaskApiService, ProductsProvider>(
          create: (context) =>
              ProductsProvider(context.read<FlaskApiService>()),
          update: (context, api, previous) => previous ?? ProductsProvider(api),
        ),

        // Orders via Flask/MySQL
        ChangeNotifierProxyProvider<FlaskApiService, OrdersProvider>(
          create: (context) => OrdersProvider(context.read<FlaskApiService>()),
          update: (context, api, previous) => previous ?? OrdersProvider(api),
        ),

        // User Orders via Flask/MySQL
        ChangeNotifierProxyProvider<FlaskApiService, UserOrdersProvider>(
          create: (context) =>
              UserOrdersProvider(context.read<FlaskApiService>()),
          update: (context, api, previous) =>
              previous ?? UserOrdersProvider(api),
        ),

        // Product detail provider — bind FlaskApiService when available
        ChangeNotifierProxyProvider<FlaskApiService, ProductProvider>(
          create: (_) => ProductProvider(),
          update: (context, api, previous) {
            final provider = previous ?? ProductProvider();
            provider.bindApi(api);
            return provider;
          },
        ),

        // Cart provider — auto-loads when auth state changes (login/restore/logout)
        ChangeNotifierProxyProvider2<
          FlaskApiService,
          AuthProvider,
          CartProvider
        >(
          create: (_) => CartProvider(),
          update: (context, api, auth, previous) {
            final provider = previous ?? CartProvider();
            provider.bindApi(api);
            provider.onAuthChanged(
              token: auth.isLoading ? null : auth.backendAccessToken,
              isLoading: auth.isLoading,
            );
            return provider;
          },
        ),

        ChangeNotifierProvider(
          create: (context) => SellerProvider(context.read<FlaskApiService>()),
        ),

        ChangeNotifierProvider(
          create: (context) => ProfileProvider(context.read<FlaskApiService>()),
        ),

        ChangeNotifierProvider(
          create: (context) => ChatProvider(context.read<FlaskApiService>()),
        ),

        ChangeNotifierProvider(
          create: (context) => RiderProvider(context.read<FlaskApiService>()),
        ),

        ChangeNotifierProvider(
          create: (context) => RiderChatProvider(context.read<FlaskApiService>()),
        ),

        ChangeNotifierProvider(create: (_) => RoleProvider()),

        ChangeNotifierProvider(create: (_) => LocationService()),
      ],
      child: const App(),
    ),
  );
}
