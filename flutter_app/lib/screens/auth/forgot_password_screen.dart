import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../../providers/auth_provider.dart';
import '../../services/mysql_auth_service.dart';
import '../../core/theme/app_theme.dart';
import 'auth_form.dart';
import 'otp_verification_screen.dart';

// ─────────────────────────────────────────────────────────────────────────────
// ForgotPasswordScreen
// ─────────────────────────────────────────────────────────────────────────────

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();

  bool _loading = false;
  String? _error;

  /// True while polling for OTP delivery confirmation.
  bool _waitingForEmail = false;

  Timer? _pollTimer;

  /// Elapsed poll ticks (each tick = 500 ms). Timeout at 60 ticks (30 s).
  int _pollSeconds = 0;

  final _authService = MysqlAuthService();

  // ── lifecycle ──────────────────────────────────────────────────────────────

  @override
  void dispose() {
    _pollTimer?.cancel();
    _emailCtrl.dispose();
    super.dispose();
  }

  // ── actions ────────────────────────────────────────────────────────────────

  Future<void> _sendCode() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    final email = _emailCtrl.text.trim();

    await context.read<AuthProvider>().forgotPassword(email);

    if (!mounted) return;

    final auth = context.read<AuthProvider>();

    if (auth.error != null) {
      setState(() {
        _error = auth.error;
        _loading = false;
      });
      return;
    }

    // Request accepted — start polling for OTP delivery status.
    setState(() {
      _loading = false;
      _waitingForEmail = true;
      _pollSeconds = 0;
    });

    _pollTimer = Timer.periodic(const Duration(milliseconds: 500), (timer) async {
      if (!mounted) {
        timer.cancel();
        return;
      }

      _pollSeconds++;

      // Timeout after 30 seconds (60 ticks × 500 ms).
      if (_pollSeconds >= 60) {
        timer.cancel();
        if (mounted) {
          setState(() {
            _waitingForEmail = false;
            _error = 'Email sending timed out. Please try again.';
          });
        }
        return;
      }

      try {
        final status = await _authService.checkOtpStatus(email);

        if (status == 'sent') {
          timer.cancel();
          if (mounted) {
            setState(() => _waitingForEmail = false);
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => OtpVerificationScreen(email: email),
              ),
            );
          }
        } else if (status == 'error') {
          timer.cancel();
          if (mounted) {
            setState(() {
              _waitingForEmail = false;
              _error = 'Failed to send email. Please try again.';
            });
          }
        }
        // 'pending' or 'none' — keep polling.
      } catch (_) {
        // Network hiccup — keep polling until timeout.
      }
    });
  }

  // ── build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Forgot Password'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Error banner
              if (_error != null) AuthErrorBanner(_error!),

              // Description
              const Text(
                "Enter your registered email address and we'll send you a "
                '4-digit code to reset your password.',
                style: TextStyle(
                  fontSize: 14,
                  color: AppTheme.mediumGray,
                ),
              ),

              const SizedBox(height: 24),

              // Email field
              TextFormField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: authFieldDec(
                  label: 'Email',
                  hint: 'you@example.com',
                  icon: FontAwesomeIcons.envelope,
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter your email address.';
                  }
                  final emailRegex = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
                  if (!emailRegex.hasMatch(value.trim())) {
                    return 'Please enter a valid email address.';
                  }
                  return null;
                },
              ),

              const SizedBox(height: 8),

              // Polling indicator
              if (_waitingForEmail)
                Row(
                  children: const [
                    SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          AppTheme.primaryBlue,
                        ),
                      ),
                    ),
                    SizedBox(width: 10),
                    Text(
                      'Sending code to your email...',
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.mediumGray,
                      ),
                    ),
                  ],
                ),

              const SizedBox(height: 20),

              // Submit button
              AuthPrimaryButton(
                label: 'Send Code',
                loading: _loading,
                onPressed: _waitingForEmail ? null : _sendCode,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
