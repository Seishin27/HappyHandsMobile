import 'package:flutter/foundation.dart';

class AppConfig {
  /// Base URL for your Flask API, ending with `/api`.
  ///
  /// Example (same Wi-Fi phone + PC):
  /// - http://192.168.1.12:5500/api
  ///
  /// You can override at runtime:
  /// `flutter run --dart-define=API_BASE_URL=http://192.168.1.12:5500/api`
  static String get apiBaseUrl {
    const overrideUrl = String.fromEnvironment('API_BASE_URL');
    if (overrideUrl.isNotEmpty) {
      return overrideUrl;
    }

    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5500/api';
    }

    // Flutter Web and iOS simulator — use localhost for local dev.
    // For a physical device on the same Wi-Fi, pass the LAN IP at build time:
    //   flutter run --dart-define=API_BASE_URL=http://192.168.x.x:5500/api
    return 'http://127.0.0.1:5500/api';
  }

  static String get staticBaseUrl {
    final base = apiBaseUrl.replaceAll(RegExp(r'/api/?$'), '');
    return '$base/static';
  }

  static String get uploadsBaseUrl {
    final base = apiBaseUrl.replaceAll(RegExp(r'/api/?$'), '');
    return '$base/uploads';
  }

  static const Duration connectTimeout = Duration(seconds: 8);
  static const Duration requestTimeout = Duration(seconds: 20);

  // Pagination
  static const int defaultPageSize = 12;
  static const int maxPageSize = 100;

  // Cache settings
  static const Duration cacheExpiration = Duration(hours: 1);
  static const int maxCacheSize = 100;

  // App settings
  static const String appName = 'Happy Hands';
  static const String appVersion = '1.0.0';

  // Debug settings
  static const bool enableLogging = true;
  static const bool enableNetworkLogging = true;
}
