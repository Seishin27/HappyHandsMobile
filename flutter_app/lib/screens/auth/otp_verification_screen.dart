import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../../services/mysql_auth_service.dart';
import '../../core/theme/app_theme.dart';
import 'auth_form.dart';

// ─────────────────────────────────────────────────────────────────────────────
// OtpVerificationScreen
//
// Step 1 — Enter the 4-digit OTP sent to [email].
// Step 2 — After OTP is verified, set a new password.
// ─────────────────────────────────────────────────────────────────────────────

class OtpVerificationScreen extends StatefulWidget {
  final String email;

  const OtpVerificationScreen({super.key, required this.email});

  @override
  State<OtpVerificationScreen> createState() => _OtpVerificationScreenState();
}

class _OtpVerificationScreenState extends State<OtpVerificationScreen> {
  // ── OTP step ──────────────────────────────────────────────────────────────
  final _otpFormKey = GlobalKey<FormState>();
  final _otpCtrl = TextEditingController();

  // ── Password step ─────────────────────────────────────────────────────────
  final _pwFormKey = GlobalKey<FormState>();
  final _pwCtrl = TextEditingController();
  final _pwConfirmCtrl = TextEditingController();
  bool _pwObscure = true;
  bool _pwConfirmObscure = true;

  // ── Resend cooldown ───────────────────────────────────────────────────────
  Timer? _resendTimer;
  int _resendCooldown = 60;
  bool _canResend = false;

  // ── Shared state ──────────────────────────────────────────────────────────
  bool _loading = false;
  String? _error;
  String? _resetToken; // non-null once OTP is verified
  bool _done = false;  // true after password reset succeeds

  final _authService = MysqlAuthService();

  // ── lifecycle ──────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _startResendCooldown();
  }

  @override
  void dispose() {
    _resendTimer?.cancel();
    _otpCtrl.dispose();
    _pwCtrl.dispose();
    _pwConfirmCtrl.dispose();
    super.dispose();
  }

  // ── actions ────────────────────────────────────────────────────────────────

  void _startResendCooldown() {
    _resendCooldown = 60;
    _canResend = false;
    _resendTimer?.cancel();
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) { t.cancel(); return; }
      setState(() {
        _resendCooldown--;
        if (_resendCooldown <= 0) {
          _canResend = true;
          t.cancel();
        }
      });
    });
  }

  Future<void> _resendCode() async {
    if (!_canResend) return;
    setState(() { _loading = true; _error = null; });
    try {
      await _authService.forgotPassword(widget.email);
      if (!mounted) return;
      _startResendCooldown();
      setState(() { _loading = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  Future<void> _verifyOtp() async {
    if (!(_otpFormKey.currentState?.validate() ?? false)) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final token = await _authService.verifyOtp(
        widget.email,
        _otpCtrl.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _resetToken = token;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  Future<void> _resetPassword() async {
    if (!(_pwFormKey.currentState?.validate() ?? false)) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      await _authService.resetPasswordWithOtp(
        _resetToken!,
        _pwCtrl.text,
      );
      if (!mounted) return;
      setState(() {
        _done = true;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  // ── build helpers ──────────────────────────────────────────────────────────

  Widget _buildOtpStep() {
    return Form(
      key: _otpFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_error != null) AuthErrorBanner(_error!),

          Text(
            'We sent a 4-digit code to\n${widget.email}',
            style: const TextStyle(fontSize: 14, color: AppTheme.mediumGray),
          ),

          const SizedBox(height: 24),

          TextFormField(
            controller: _otpCtrl,
            keyboardType: TextInputType.number,
            maxLength: 4,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w700,
              letterSpacing: 12,
              color: AppTheme.heroDark,
            ),
            decoration: authFieldDec(
              label: 'Verification Code',
              hint: '0000',
              icon: FontAwesomeIcons.key,
            ).copyWith(
              counterText: '',
            ),
            validator: (v) {
              if (v == null || v.trim().length < 4) {
                return 'Please enter the 4-digit code.';
              }
              return null;
            },
          ),

          const SizedBox(height: 20),

          AuthPrimaryButton(
            label: 'Verify Code',
            loading: _loading,
            onPressed: _verifyOtp,
          ),

          const SizedBox(height: 12),
          Center(
            child: TextButton(
              onPressed: _canResend ? _resendCode : null,
              child: Text(
                _canResend
                    ? 'Resend Code'
                    : 'Resend Code in ${_resendCooldown}s',
                style: TextStyle(
                  fontSize: 13,
                  color: _canResend ? AppTheme.primaryBlue : AppTheme.mediumGray,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPasswordStep() {
    return Form(
      key: _pwFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_error != null) AuthErrorBanner(_error!),

          const Text(
            'OTP verified. Choose a new password for your account.',
            style: TextStyle(fontSize: 14, color: AppTheme.mediumGray),
          ),

          const SizedBox(height: 24),

          TextFormField(
            controller: _pwCtrl,
            obscureText: _pwObscure,
            decoration: authFieldDec(
              label: 'New Password',
              hint: 'At least 6 characters',
              icon: FontAwesomeIcons.lock,
              suffix: IconButton(
                icon: Icon(
                  _pwObscure
                      ? FontAwesomeIcons.eyeSlash
                      : FontAwesomeIcons.eye,
                  size: 16,
                  color: AppTheme.mediumGray,
                ),
                onPressed: () => setState(() => _pwObscure = !_pwObscure),
              ),
            ),
            validator: (v) {
              if (v == null || v.length < 6) {
                return 'Password must be at least 6 characters.';
              }
              return null;
            },
          ),

          const SizedBox(height: 14),

          TextFormField(
            controller: _pwConfirmCtrl,
            obscureText: _pwConfirmObscure,
            decoration: authFieldDec(
              label: 'Confirm Password',
              hint: 'Repeat your new password',
              icon: FontAwesomeIcons.lock,
              suffix: IconButton(
                icon: Icon(
                  _pwConfirmObscure
                      ? FontAwesomeIcons.eyeSlash
                      : FontAwesomeIcons.eye,
                  size: 16,
                  color: AppTheme.mediumGray,
                ),
                onPressed: () =>
                    setState(() => _pwConfirmObscure = !_pwConfirmObscure),
              ),
            ),
            validator: (v) {
              if (v != _pwCtrl.text) return 'Passwords do not match.';
              return null;
            },
          ),

          const SizedBox(height: 20),

          AuthPrimaryButton(
            label: 'Reset Password',
            loading: _loading,
            onPressed: _resetPassword,
          ),
        ],
      ),
    );
  }

  Widget _buildDoneStep() {
    return Column(
      children: [
        const SizedBox(height: 24),
        const Icon(
          FontAwesomeIcons.circleCheck,
          color: AppTheme.successGreen,
          size: 56,
        ),
        const SizedBox(height: 20),
        const Text(
          'Password reset!',
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: AppTheme.heroDark,
          ),
        ),
        const SizedBox(height: 10),
        const Text(
          'Your password has been updated successfully. You can now log in with your new password.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 14, color: AppTheme.mediumGray),
        ),
        const SizedBox(height: 32),
        AuthPrimaryButton(
          label: 'Back to Login',
          loading: false,
          onPressed: () {
            // Pop back to the login screen (removes forgot-password + otp screens).
            Navigator.of(context).popUntil((route) => route.isFirst);
          },
        ),
      ],
    );
  }

  // ── build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    String title;
    if (_done) {
      title = 'Password Reset';
    } else if (_resetToken != null) {
      title = 'New Password';
    } else {
      title = 'Enter OTP';
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: _done
            ? _buildDoneStep()
            : _resetToken != null
                ? _buildPasswordStep()
                : _buildOtpStep(),
      ),
    );
  }
}
