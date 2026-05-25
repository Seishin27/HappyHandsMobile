import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config/app_config.dart';

/// Represents a logged-in user from the MySQL/Flask backend.
class MysqlUser {
  final int id;
  final String username;
  final String email;
  final String? name;

  const MysqlUser({
    required this.id,
    required this.username,
    required this.email,
    this.name,
  });

  String get displayName => name ?? username;
  String? get photoURL => null;

  factory MysqlUser.fromJson(Map<String, dynamic> json) {
    return MysqlUser(
      id: (json['id'] as num?)?.toInt() ??
          (json['user_id'] as num?)?.toInt() ??
          0,
      username: (json['username'] ?? json['name'] ?? '').toString(),
      email: (json['email'] ?? '').toString(),
      name: json['name']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'email': email,
        'name': name,
      };
}

/// Talks to POST /api/register and POST /api/login on the Flask backend.
/// Persists the JWT and user info in SharedPreferences.
class MysqlAuthService {
  static const _keyToken = 'mysql_auth_token';
  static const _keyRefreshToken = 'mysql_auth_refresh_token';
  static const _keyUser = 'mysql_auth_user';
  static const _keyRole = 'mysql_auth_role';

  // ── Persistence ──────────────────────────────────────────────────────────

  Future<void> _persist(String token, MysqlUser user, {String role = 'user', String? refreshToken}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyToken, token);
    await prefs.setString(_keyUser, jsonEncode(user.toJson()));
    await prefs.setString(_keyRole, role);
    if (refreshToken != null && refreshToken.isNotEmpty) {
      await prefs.setString(_keyRefreshToken, refreshToken);
    }
  }

  Future<void> _clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyToken);
    await prefs.remove(_keyRefreshToken);
    await prefs.remove(_keyUser);
    await prefs.remove(_keyRole);
  }

  Future<String?> getSavedToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyToken);
  }

  Future<String?> getSavedRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyRefreshToken);
  }

  Future<String?> getSavedRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyRole);
  }

  Future<MysqlUser?> getSavedUser() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_keyUser);
    if (raw == null) return null;
    try {
      return MysqlUser.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  /// Calls POST /api/refresh with the stored refresh token.
  /// Returns the new access token, or null on failure.
  Future<String?> refreshAccessToken() async {
    final refreshToken = await getSavedRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return null;
    try {
      final uri = Uri.parse('${AppConfig.apiBaseUrl}/refresh');
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': 'Bearer $refreshToken',
        },
      ).timeout(AppConfig.requestTimeout);
      final body = _decodeBody(response);
      if (response.statusCode == 200 && body['status'] == 'success') {
        final data = (body['data'] as Map<String, dynamic>?) ?? {};
        final newToken = data['access_token']?.toString() ?? '';
        if (newToken.isNotEmpty) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString(_keyToken, newToken);
          developer.log('MysqlAuthService: token refreshed');
          return newToken;
        }
      }
    } catch (e) {
      developer.log('MysqlAuthService: token refresh failed: $e');
    }
    return null;
  }

  // ── API calls ─────────────────────────────────────────────────────────────

  Future<({MysqlUser user, String token})> register({
    required String username,
    required String email,
    required String password,
    String region = '',
    String province = '',
    String city = '',
    String barangay = '',
    String homeAddress = '',
    String contactNumber = '',
  }) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/register');
    developer.log('MysqlAuthService.register → $uri');

    final http.Response response = await _post(uri, {
      'username': username,
      'email': email,
      'password': password,
      'region': region,
      'province': province,
      'city': city,
      'barangay': barangay,
      'home_address': homeAddress,
      'contact_number': contactNumber,
    });

    final body = _decodeBody(response);
    developer.log('register response ${response.statusCode}: ${response.body}');

    if (response.statusCode == 200 || body['status'] == 'success') {
      final data = (body['data'] as Map<String, dynamic>?) ?? {};
      final token = (data['access_token'] ?? '').toString();
      final userJson = (data['user'] as Map<String, dynamic>?) ??
          {'id': data['id'], 'username': username, 'email': email};
      final user = MysqlUser.fromJson(userJson);
      await _persist(token, user, role: 'user');
      developer.log('Registered: ${user.email}');
      return (user: user, token: token);
    }

    throw _extractError(body, 'Registration failed');
  }

  Future<({MysqlUser user, String token})> login({
    required String email,
    required String password,
  }) async {
    return _loginAt(
      path: '/login',
      payload: {
        'username': email, // Flask accepts email in the username field
        'email': email,
        'password': password,
      },
      fallbackError: 'Invalid email or password',
      role: 'user',
    );
  }

  Future<({MysqlUser user, String token})> loginAsSeller({
    required String email,
    required String password,
  }) async {
    return _loginAt(
      path: '/seller/login',
      payload: {'email': email, 'password': password},
      fallbackError: 'Invalid seller credentials',
      role: 'seller',
    );
  }

  Future<({MysqlUser user, String token})> loginAsRider({
    required String email,
    required String password,
  }) async {
    return _loginAt(
      path: '/rider/login',
      payload: {'email': email, 'password': password},
      fallbackError: 'Invalid rider credentials',
      role: 'rider',
    );
  }

  Future<({MysqlUser user, String token})> _loginAt({
    required String path,
    required Map<String, dynamic> payload,
    required String fallbackError,
    String role = 'user',
  }) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}$path');
    developer.log('MysqlAuthService.login → $uri');

    final http.Response response = await _post(uri, payload);
    final body = _decodeBody(response);
    developer.log('login response ${response.statusCode}: ${response.body}');

    if (response.statusCode == 200 && body['status'] == 'success') {
      final data = (body['data'] as Map<String, dynamic>?) ?? {};
      final token = (data['access_token'] ?? '').toString();
      final refresh = data['refresh_token']?.toString();
      final email = (payload['email'] ?? payload['username'] ?? '').toString();
      final userJson = (data['user'] as Map<String, dynamic>?) ??
          {'id': data['user_id'], 'username': email, 'email': email};
      final user = MysqlUser.fromJson(userJson);
      await _persist(token, user, role: role, refreshToken: refresh);
      developer.log('Logged in: ${user.email}');
      return (user: user, token: token);
    }

    throw _extractError(body, fallbackError);
  }

  Future<void> logout() async {
    await _clear();
    developer.log('MysqlAuthService: logged out');
  }

  /// POST /api/mobile/forgot-password
  /// Throws on network error or server error response.
  Future<void> forgotPassword(String email) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/mobile/forgot-password');
    final response = await _post(uri, {'email': email.trim().toLowerCase()});
    final body = _decodeBody(response);
    if (body['status'] != 'success') {
      throw Exception(_extractError(body, 'Failed to send OTP'));
    }
  }

  /// GET /api/otp_status?email=...
  /// Returns: "none" | "pending" | "sent" | "error"
  Future<String> checkOtpStatus(String email) async {
    final uri = Uri.parse(
        '${AppConfig.apiBaseUrl}/otp_status?email=${Uri.encodeComponent(email)}');
    try {
      final response = await http
          .get(uri, headers: const {'Accept': 'application/json'})
          .timeout(AppConfig.requestTimeout);
      final body = _decodeBody(response);
      return (body['status'] as String?) ?? 'none';
    } on TimeoutException {
      throw 'Request timed out. Make sure the Flask server is running at ${AppConfig.apiBaseUrl}';
    } on SocketException catch (e) {
      throw 'Cannot reach server at ${AppConfig.apiBaseUrl}.\n(Detail: ${e.message})';
    } on http.ClientException catch (e) {
      throw 'Connection failed: ${e.message}';
    } catch (e) {
      if (kIsWeb) {
        throw 'Cannot reach server at ${AppConfig.apiBaseUrl}.\n(Detail: $e)';
      }
      throw 'Unexpected error: $e';
    }
  }

  /// POST /api/mobile/verify-otp
  /// Returns reset_token on success, throws on failure.
  Future<String> verifyOtp(String email, String otp) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/mobile/verify-otp');
    final response = await _post(uri, {
      'email': email.trim().toLowerCase(),
      'otp': otp.trim(),
    });
    final body = _decodeBody(response);
    if (body['status'] != 'success') {
      throw Exception(_extractError(body, 'Invalid OTP'));
    }
    final token = body['reset_token'] as String?;
    if (token == null || token.isEmpty) throw Exception('No reset token received');
    return token;
  }

  /// POST /api/mobile/reset-password
  /// Throws on failure.
  Future<void> resetPasswordWithOtp(String resetToken, String newPassword) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/mobile/reset-password');
    final response = await _post(uri, {
      'reset_token': resetToken,
      'new_password': newPassword,
    });
    final body = _decodeBody(response);
    if (body['status'] != 'success') {
      throw Exception(_extractError(body, 'Failed to reset password'));
    }
  }

  // ── HTTP helper ───────────────────────────────────────────────────────────

  Future<http.Response> _post(
    Uri uri,
    Map<String, dynamic> body,
  ) async {
    try {
      return await http
          .post(
            uri,
            headers: const {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: jsonEncode(body),
          )
          .timeout(AppConfig.requestTimeout);
    } on TimeoutException {
      throw 'Request timed out. Make sure the Flask server is running at ${AppConfig.apiBaseUrl}';
    } on SocketException catch (e) {
      throw 'Cannot reach server at ${AppConfig.apiBaseUrl}.\n'
          'Make sure Flask is running and you passed the correct IP with:\n'
          '--dart-define=API_BASE_URL=http://YOUR_PC_IP:5500/api\n'
          '(Detail: ${e.message})';
    } on http.ClientException catch (e) {
      throw 'Connection failed: ${e.message}';
    } catch (e) {
      // On web, SocketException is not thrown — CORS or network errors
      // surface as generic exceptions.
      if (kIsWeb) {
        throw 'Cannot reach server at ${AppConfig.apiBaseUrl}.\n'
            'Make sure Flask is running and you used:\n'
            '--dart-define=API_BASE_URL=http://YOUR_PC_IP:5500/api\n'
            '(Detail: $e)';
      }
      throw 'Unexpected error: $e';
    }
  }

  // ── Decode helpers ────────────────────────────────────────────────────────

  Map<String, dynamic> _decodeBody(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) return decoded;
    } catch (_) {}
    return {};
  }

  String _extractError(Map<String, dynamic> body, String fallback) {
    final msg = body['message']?.toString().trim() ??
        body['error']?.toString().trim() ??
        body['msg']?.toString().trim();
    if (msg != null && msg.isNotEmpty) return msg;
    return fallback;
  }
}
