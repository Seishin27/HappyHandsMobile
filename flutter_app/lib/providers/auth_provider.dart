import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';

import '../services/mysql_auth_service.dart';

/// Drop-in replacement for the Firebase-based AuthProvider.
/// Uses the Flask/MySQL backend exclusively — no Firebase Auth.
class AuthProvider extends ChangeNotifier {
  final MysqlAuthService _service;

  bool _isLoading = true; // true on startup while restoring session
  MysqlUser? _user;
  String? _error;
  String? _backendAccessToken;
  String? _activeRole;
  String? _resetToken;
  String? _resetEmail;

  AuthProvider({MysqlAuthService? service})
      : _service = service ?? MysqlAuthService() {
    _restoreSession();
  }

  // ── Getters (same surface as the old Firebase-based provider) ─────────────

  bool get isLoading => _isLoading;

  /// Returns a non-null value when the user is signed in.
  /// Typed as dynamic so existing code that accesses `.displayName`,
  /// `.email`, `.photoURL`, `.uid` still compiles — MysqlUser exposes all of
  /// those.
  MysqlUser? get user => _user;

  String? get error => _error;
  String? get backendAccessToken => _backendAccessToken;
  String? get activeRole => _activeRole;
  String? get resetToken => _resetToken;
  String? get resetEmail => _resetEmail;

  // ── Session restore ───────────────────────────────────────────────────────

  Future<void> _restoreSession() async {
    try {
      final savedUser = await _service.getSavedUser();
      final savedToken = await _service.getSavedToken();
      final savedRole = await _service.getSavedRole();
      if (savedUser != null && savedToken != null && savedToken.isNotEmpty) {
        _user = savedUser;
        _backendAccessToken = savedToken;
        _activeRole = _normalizeRole(savedRole ?? 'user');
        developer.log('Session restored: ${savedUser.email} as $_activeRole');
      }
    } catch (e) {
      developer.log('Session restore error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // ── Auth actions ──────────────────────────────────────────────────────────

  Future<void> register({
    required String email,
    required String password,
    String? displayName,
    String? role,
    String region = '',
    String province = '',
    String city = '',
    String barangay = '',
    String homeAddress = '',
    String contactNumber = '',
  }) async {
    _error = null;
    _isLoading = true;
    _activeRole = _normalizeRole(role ?? 'user');
    notifyListeners();

    try {
      final result = await _service.register(
        username: displayName?.trim().isNotEmpty == true
            ? displayName!.trim()
            : email.split('@').first,
        email: email.trim(),
        password: password,
        region: region.trim(),
        province: province.trim(),
        city: city.trim(),
        barangay: barangay.trim(),
        homeAddress: homeAddress.trim(),
        contactNumber: contactNumber.trim(),
      );
      _user = result.user;
      _backendAccessToken = result.token;
      developer.log('Registered: ${_user?.email}');
    } catch (e) {
      _error = e.toString();
      developer.log('Register error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> login({
    required String email,
    required String password,
    String? role,
  }) async {
    _error = null;
    _isLoading = true;
    _activeRole = _normalizeRole(role ?? 'user');
    notifyListeners();

    try {
      final trimmedEmail = email.trim();
      final result = switch (_activeRole) {
        'seller' => await _service.loginAsSeller(
            email: trimmedEmail,
            password: password,
          ),
        'rider' => await _service.loginAsRider(
            email: trimmedEmail,
            password: password,
          ),
        _ => await _service.login(
            email: trimmedEmail,
            password: password,
          ),
      };
      _user = result.user;
      _backendAccessToken = result.token;
      developer.log('Logged in as $_activeRole: ${_user?.email}');
    } catch (e) {
      _error = e.toString();
      developer.log('Login error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await _service.logout();
    _user = null;
    _backendAccessToken = null;
    _activeRole = null;
    _error = null;
    _resetToken = null;
    _resetEmail = null;
    notifyListeners();
  }

  /// Not applicable without Firebase — kept for API compatibility.
  Future<void> resetPassword(String email) async {
    _error = 'Password reset is not available in this version. '
        'Please use the web app to reset your password.';
    notifyListeners();
  }

  Future<void> forgotPassword(String email) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      await _service.forgotPassword(email);
      _resetEmail = email;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Returns reset_token on success, null on failure (error set in provider).
  Future<String?> verifyOtp(String email, String otp) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final token = await _service.verifyOtp(email, otp);
      _resetToken = token;
      return token;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> resetPasswordWithOtp(String resetToken, String newPassword) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      await _service.resetPasswordWithOtp(resetToken, newPassword);
      _resetToken = null;
      _resetEmail = null;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Returns the JWT for API calls.
  Future<String?> getIdToken() async => _backendAccessToken;

  /// Silently refreshes the access token using the stored refresh token.
  /// Updates [_backendAccessToken] on success and returns the new token.
  Future<String?> refreshToken() async {
    final newToken = await _service.refreshAccessToken();
    if (newToken != null) {
      _backendAccessToken = newToken;
      notifyListeners();
    }
    return newToken;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  String _normalizeRole(String role) {
    final r = role.trim().toLowerCase();
    if (r == 'seller' || r == 'rider') return r;
    return 'user';
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
