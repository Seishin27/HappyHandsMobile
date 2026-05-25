import 'package:flutter/foundation.dart';

import '../models/seller_profile.dart';
import '../services/flask_api_service.dart';

/// Provider for managing seller profile state and operations.
///
/// This provider handles:
/// - Fetching seller profile information
/// - Updating profile details
/// - Changing password
/// - Managing edit mode for profile editing
/// - Loading and error states
class ProfileProvider extends ChangeNotifier {
  final FlaskApiService _api;

  ProfileProvider(this._api);

  SellerProfile? _profile;
  bool _isLoading = false;
  String? _error;
  bool _isEditing = false;

  SellerProfile? get profile => _profile;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isEditing => _isEditing;

  /// Fetches the seller's profile from the API.
  ///
  /// Sets loading state while fetching and clears any previous errors.
  /// Updates the profile state on success.
  ///
  /// Throws Exception if the API call fails.
  Future<void> fetchProfile() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _profile = await _api.fetchSellerProfile();
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Updates the seller's profile with new information.
  ///
  /// Parameters:
  /// - [profile]: Updated SellerProfile object
  ///
  /// Sets loading state while updating and clears any previous errors.
  /// Updates the local profile state on success and exits edit mode.
  ///
  /// Throws Exception if the API call fails.
  Future<void> updateProfile(SellerProfile profile) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _profile = await _api.updateSellerProfile(profile);
      _isEditing = false;
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Changes the seller's password.
  ///
  /// Parameters:
  /// - [currentPassword]: Current password for verification
  /// - [newPassword]: New password to set
  ///
  /// Sets loading state while changing password and clears any previous errors.
  ///
  /// Throws Exception if the API call fails (e.g., incorrect current password).
  Future<void> changePassword(String currentPassword, String newPassword) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      await _api.changePassword(currentPassword, newPassword);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Toggles the edit mode for profile editing.
  ///
  /// When entering edit mode, clears any previous errors.
  /// When exiting edit mode, also clears errors.
  void toggleEditMode() {
    _isEditing = !_isEditing;
    _error = null;
    notifyListeners();
  }

  /// Enables edit mode for profile editing.
  void enableEditMode() {
    _isEditing = true;
    _error = null;
    notifyListeners();
  }

  /// Disables edit mode and clears any errors.
  void disableEditMode() {
    _isEditing = false;
    _error = null;
    notifyListeners();
  }

  /// Clears the current error message.
  void clearError() {
    _error = null;
    notifyListeners();
  }
}
