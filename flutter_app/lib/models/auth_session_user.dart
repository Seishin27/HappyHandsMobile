class AuthSessionUser {
  final String id;
  final String email;
  final String role;
  final String? displayName;
  final String? photoURL;

  const AuthSessionUser({
    required this.id,
    required this.email,
    required this.role,
    this.displayName,
    this.photoURL,
  });

  String? get uid => id;
}