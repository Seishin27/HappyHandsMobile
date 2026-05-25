import 'package:flutter/foundation.dart';

import '../models/role.dart';

/// Simplified RoleProvider — roles come from AuthProvider (MySQL/Flask).
/// Firebase Auth is no longer used for role lookup.
class RoleProvider extends ChangeNotifier {
  RoleProvider();

  bool _isLoading = false;
  String? _error;
  List<AppRole> _available = const [AppRole.user];
  AppRole _selected = AppRole.user;

  bool get isLoading => _isLoading;
  String? get error => _error;
  List<AppRole> get availableRoles => _available;
  AppRole get selectedRole => _selected;

  /// Call this with the active role string from AuthProvider after login.
  void setRoleFromString(String? roleKey) {
    final role = roleKey == null ? null : AppRoleX.fromKey(roleKey);
    _available = role == null ? const [AppRole.user] : [role];
    _selected = _available.first;
    _error = null;
    notifyListeners();
  }

  Future<void> refresh() async {
    // No-op: roles are now managed by AuthProvider via MySQL.
    // Kept for API compatibility with RoleShell.
    _isLoading = false;
    notifyListeners();
  }

  void select(AppRole role) {
    _selected = role;
    notifyListeners();
  }
}
