import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../../providers/auth_provider.dart';
import '../../core/theme/app_theme.dart';
import 'forgot_password_screen.dart';

enum AuthRole { buyer, seller, rider }

// ─────────────────────────────────────────────────────────────────────────────
// Shared input decoration — matches the screenshot exactly:
//   • Uppercase label above the field (floatingLabelBehavior.always)
//   • Light gray fill (#F8FAFC)
//   • Rounded border (#E2E8F0)
//   • Icon prefix in slate-400
// ─────────────────────────────────────────────────────────────────────────────
InputDecoration authFieldDec({
  required String label,
  required String hint,
  required IconData icon,
  Widget? suffix,
}) {
  return InputDecoration(
    labelText: label.toUpperCase(),
    labelStyle: const TextStyle(
      fontSize: 11,
      fontWeight: FontWeight.w700,
      color: AppTheme.mediumGray,
      letterSpacing: 0.8,
    ),
    hintText: hint,
    hintStyle: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 14),
    prefixIcon: Icon(icon, color: AppTheme.mediumGray, size: 16),
    prefixIconConstraints: const BoxConstraints(minWidth: 44, minHeight: 44),
    suffixIcon: suffix,
    filled: true,
    fillColor: AppTheme.lightGray,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppTheme.borderGray),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppTheme.borderGray),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppTheme.primaryBlue, width: 1.5),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppTheme.errorRed),
    ),
    focusedErrorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppTheme.errorRed, width: 1.5),
    ),
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    floatingLabelBehavior: FloatingLabelBehavior.always,
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Primary auth button — dark navy, full width, rounded
// ─────────────────────────────────────────────────────────────────────────────
class AuthPrimaryButton extends StatelessWidget {
  final String label;
  final bool loading;
  final VoidCallback? onPressed;

  const AuthPrimaryButton({
    super.key,
    required this.label,
    required this.loading,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: ElevatedButton(
        onPressed: loading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppTheme.heroDark,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: loading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
            : Text(
                label,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.2,
                ),
              ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Error banner
// ─────────────────────────────────────────────────────────────────────────────
class AuthErrorBanner extends StatelessWidget {
  final String message;
  const AuthErrorBanner(this.message, {super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFEE2E2),
        border: Border.all(color: const Color(0xFFFECACA)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(FontAwesomeIcons.circleExclamation,
              color: Color(0xFF991B1B), size: 14),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Color(0xFF991B1B), fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Login form (email + password) — used by all three roles
// ─────────────────────────────────────────────────────────────────────────────
class AuthForm extends StatefulWidget {
  final AuthRole role;
  final bool showForgotPassword;

  const AuthForm({
    super.key,
    required this.role,
    this.showForgotPassword = false,
  });

  @override
  State<AuthForm> createState() => _AuthFormState();
}

class _AuthFormState extends State<AuthForm> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  String get _roleEndpoint {
    switch (widget.role) {
      case AuthRole.buyer:
        return 'buyer';
      case AuthRole.seller:
        return 'seller';
      case AuthRole.rider:
        return 'rider';
    }
  }

  String get _roleLabel {
    switch (widget.role) {
      case AuthRole.buyer:
        return 'Customer';
      case AuthRole.seller:
        return 'Seller';
      case AuthRole.rider:
        return 'Rider';
    }
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });
    try {
      final auth = context.read<AuthProvider>();
      await auth.login(
        email: _emailCtrl.text.trim(),
        password: _passCtrl.text,
        role: _roleEndpoint,
      );
      if (!mounted) return;
      if (auth.error != null || auth.user == null) {
        setState(() => _error = auth.error ?? 'Login failed. Please try again.');
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Welcome back, $_roleLabel!'),
        backgroundColor: AppTheme.successGreen,
        duration: const Duration(seconds: 1),
      ));
      String route;
      switch (auth.activeRole) {
        case 'seller':
          route = '/seller-dashboard';
          break;
        case 'rider':
          route = '/rider-dashboard';
          break;
        default:
          route = '/home';
      }
      Navigator.of(context).pushNamedAndRemoveUntil(route, (r) => r.isFirst);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _forgotPassword() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => const ForgotPasswordScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_error != null) AuthErrorBanner(_error!),
          TextFormField(
            controller: _emailCtrl,
            keyboardType: TextInputType.emailAddress,
            enabled: !_loading,
            decoration: authFieldDec(
              label: 'Email',
              hint: 'Enter your email',
              icon: FontAwesomeIcons.envelope,
            ),
            validator: (v) {
              if (v == null || v.isEmpty) return 'Email is required';
              if (!RegExp(r'^[\w\-.]+@([\w\-]+\.)+[\w\-]{2,4}$').hasMatch(v)) {
                return 'Enter a valid email';
              }
              return null;
            },
          ),
          const SizedBox(height: 14),
          TextFormField(
            controller: _passCtrl,
            obscureText: _obscure,
            enabled: !_loading,
            decoration: authFieldDec(
              label: 'Password',
              hint: 'Enter your password',
              icon: FontAwesomeIcons.lock,
              suffix: IconButton(
                onPressed: () => setState(() => _obscure = !_obscure),
                icon: Icon(
                  _obscure ? FontAwesomeIcons.eye : FontAwesomeIcons.eyeSlash,
                  color: const Color(0xFF94A3B8),
                  size: 16,
                ),
              ),
            ),
            validator: (v) {
              if (v == null || v.isEmpty) return 'Password is required';
              if (v.length < 6) return 'At least 6 characters';
              return null;
            },
          ),
          if (widget.showForgotPassword) ...[
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _forgotPassword,
                style: TextButton.styleFrom(
                  padding: EdgeInsets.zero,
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: const Text(
                  'Forgot Password?',
                  style: TextStyle(
                    fontSize: 13,
                    color: AppTheme.mediumGray,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ),
          ],
          const SizedBox(height: 20),
          AuthPrimaryButton(
            label: 'Sign in',
            loading: _loading,
            onPressed: _login,
          ),
        ],
      ),
    );
  }
}
