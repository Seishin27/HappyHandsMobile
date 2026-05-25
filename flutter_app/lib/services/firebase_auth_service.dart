import 'package:firebase_auth/firebase_auth.dart';
import 'dart:developer' as developer;

class FirebaseAuthService {
  final FirebaseAuth _auth;

  FirebaseAuthService({FirebaseAuth? auth}) : _auth = auth ?? FirebaseAuth.instance;

  Stream<User?> authStateChanges() => _auth.authStateChanges();
  Stream<User?> idTokenChanges() => _auth.idTokenChanges();
  Stream<User?> userChanges() => _auth.userChanges();

  User? get currentUser => _auth.currentUser;

  bool get isSignedIn => _auth.currentUser != null;

  String? get currentUserEmail => _auth.currentUser?.email;

  String? get currentUserId => _auth.currentUser?.uid;

  String? get currentUserDisplayName => _auth.currentUser?.displayName;

  String? get currentUserPhotoUrl => _auth.currentUser?.photoURL;

  Future<UserCredential> register({
    required String email,
    required String password,
    String? displayName,
  }) async {
    try {
      final credential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );

      // Update display name if provided
      if (displayName != null && displayName.isNotEmpty) {
        await credential.user?.updateDisplayName(displayName);
      }

      developer.log('User registered successfully: ${credential.user?.email}');
      return credential;
    } on FirebaseAuthException catch (e) {
      developer.log('Registration failed: ${e.code} - ${e.message}');
      rethrow;
    } catch (e) {
      developer.log('Unexpected registration error: $e');
      rethrow;
    }
  }

  Future<UserCredential> login({
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );

      developer.log('User logged in successfully: ${credential.user?.email}');
      return credential;
    } on FirebaseAuthException catch (e) {
      developer.log('Login failed: ${e.code} - ${e.message}');
      rethrow;
    } catch (e) {
      developer.log('Unexpected login error: $e');
      rethrow;
    }
  }

  Future<void> logout() async {
    try {
      await _auth.signOut();
      developer.log('User logged out successfully');
    } catch (e) {
      developer.log('Logout error: $e');
      rethrow;
    }
  }

  Future<void> resetPassword(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email);
      developer.log('Password reset email sent to: $email');
    } on FirebaseAuthException catch (e) {
      developer.log('Password reset failed: ${e.code} - ${e.message}');
      rethrow;
    } catch (e) {
      developer.log('Unexpected password reset error: $e');
      rethrow;
    }
  }

  Future<void> updateDisplayName(String displayName) async {
    try {
      await _auth.currentUser?.updateDisplayName(displayName);
      developer.log('Display name updated to: $displayName');
    } catch (e) {
      developer.log('Display name update error: $e');
      rethrow;
    }
  }

  Future<void> updatePhotoURL(String photoURL) async {
    try {
      await _auth.currentUser?.updatePhotoURL(photoURL);
      developer.log('Photo URL updated to: $photoURL');
    } catch (e) {
      developer.log('Photo URL update error: $e');
      rethrow;
    }
  }

  Future<void> reloadUser() async {
    try {
      await _auth.currentUser?.reload();
      developer.log('User data reloaded');
    } catch (e) {
      developer.log('User reload error: $e');
      rethrow;
    }
  }

  /// Firebase ID token used to authenticate to your Flask backend.
  Future<String?> getIdToken({bool forceRefresh = false}) async {
    try {
      final user = _auth.currentUser;
      if (user == null) return null;
      
      final idToken = await user.getIdToken(forceRefresh);
      developer.log('ID token retrieved successfully');
      return idToken;
    } catch (e) {
      developer.log('ID token retrieval error: $e');
      return null;
    }
  }

  /// Check if user's email is verified
  bool get isEmailVerified => _auth.currentUser?.emailVerified ?? false;

  /// Send email verification
  Future<void> sendEmailVerification() async {
    try {
      await _auth.currentUser?.sendEmailVerification();
      developer.log('Email verification sent');
    } catch (e) {
      developer.log('Email verification error: $e');
      rethrow;
    }
  }

  /// Delete current user account
  Future<void> deleteAccount() async {
    try {
      await _auth.currentUser?.delete();
      developer.log('User account deleted');
    } catch (e) {
      developer.log('Account deletion error: $e');
      rethrow;
    }
  }

  /// Get user metadata (creation time, last sign-in time)
  UserMetadata? get userMetadata => _auth.currentUser?.metadata;

  /// Check if user is anonymous
  bool get isAnonymous => _auth.currentUser?.isAnonymous ?? false;

  /// Get user provider data
  List<UserInfo> get providerData => _auth.currentUser?.providerData ?? [];
}

