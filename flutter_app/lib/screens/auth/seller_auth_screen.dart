import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:http/http.dart' as http;
import 'package:file_picker/file_picker.dart';

import '../../core/config/app_config.dart';
import '../../core/theme/app_theme.dart';
import '../../services/psgc_service.dart';
import '../auth_screen.dart';
import 'auth_form.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Seller Auth Screen  (Login + Register)
// ─────────────────────────────────────────────────────────────────────────────
class SellerAuthScreen extends StatefulWidget {
  const SellerAuthScreen({super.key});

  @override
  State<SellerAuthScreen> createState() => _SellerAuthScreenState();
}

class _SellerAuthScreenState extends State<SellerAuthScreen> {
  int _view = 0; // 0 = login, 1 = register

  @override
  Widget build(BuildContext context) {
    return AuthShell(
      illustration: _SellerIllustration(),
      card: _view == 0 ? _buildLoginCard() : _buildRegisterCard(),
    );
  }

  Widget _buildLoginCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'Seller Login',
          style: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w800,
            color: Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Manage your shop and connect with customers.',
          style: TextStyle(fontSize: 14, color: Color(0xFF64748B)),
        ),
        const SizedBox(height: 28),
        const AuthForm(role: AuthRole.seller),
        const SizedBox(height: 20),
        Center(
          child: RichText(
            text: TextSpan(
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
              children: [
                const TextSpan(text: "Want to sell? "),
                WidgetSpan(
                  alignment: PlaceholderAlignment.middle,
                  child: GestureDetector(
                    onTap: () => setState(() => _view = 1),
                    child: const Text(
                      'Register here',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.primaryBlue,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Center(
          child: TextButton(
            onPressed: () => Navigator.pop(context),
            style: TextButton.styleFrom(
              padding: EdgeInsets.zero,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: const Text(
              'Back to home',
              style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRegisterCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'Become a Seller',
          style: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w800,
            color: Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Start your business journey today.',
          style: TextStyle(fontSize: 14, color: Color(0xFF64748B)),
        ),
        const SizedBox(height: 24),
        _SellerRegisterForm(onSuccess: (msg) => _showSuccessAndGoLogin(msg)),
        const SizedBox(height: 20),
        Center(
          child: RichText(
            text: TextSpan(
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
              children: [
                const TextSpan(text: 'Already a seller? '),
                WidgetSpan(
                  alignment: PlaceholderAlignment.middle,
                  child: GestureDetector(
                    onTap: () => setState(() => _view = 0),
                    child: const Text(
                      'Sign in',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.primaryBlue,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Center(
          child: TextButton(
            onPressed: () => Navigator.pop(context),
            style: TextButton.styleFrom(
              padding: EdgeInsets.zero,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: const Text(
              'Back to home',
              style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
            ),
          ),
        ),
      ],
    );
  }

  void _showSuccessAndGoLogin(String msg) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64, height: 64,
              decoration: BoxDecoration(
                color: AppTheme.successGreen.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(FontAwesomeIcons.circleCheck,
                  color: AppTheme.successGreen, size: 32),
            ),
            const SizedBox(height: 16),
            const Text('Application Submitted!',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A)),
                textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(msg,
                style: const TextStyle(fontSize: 13, color: Color(0xFF64748B),
                    height: 1.5),
                textAlign: TextAlign.center),
            const SizedBox(height: 4),
            const Text(
              'Please wait for admin approval before logging in.',
              style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          SizedBox(
            width: double.infinity,
            child: AuthPrimaryButton(
              label: 'Go to Login',
              loading: false,
              onPressed: () {
                Navigator.pop(ctx);
                setState(() => _view = 0);
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _SellerIllustration extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/logos/logoo.png',
      width: 240,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) => Column(
        mainAxisSize: MainAxisSize.min,
        children: const [
          Text('🏪', style: TextStyle(fontSize: 80)),
          SizedBox(height: 16),
          Text(
            'Seller Portal',
            style: TextStyle(
              fontSize: 26,
              fontWeight: FontWeight.w800,
              color: AppTheme.navBlue,
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Seller Registration Form  (3-step wizard)
// ─────────────────────────────────────────────────────────────────────────────
class _SellerRegisterForm extends StatefulWidget {
  final void Function(String msg)? onSuccess;
  const _SellerRegisterForm({this.onSuccess});

  @override
  State<_SellerRegisterForm> createState() => _SellerRegisterFormState();
}

class _SellerRegisterFormState extends State<_SellerRegisterForm> {
  int _step = 0;

  // Step 1
  final _s1Key = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _contactCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _obscurePass = true;
  bool _obscureConfirm = true;

  // Step 2 — PSGC
  final _s2Key = GlobalKey<FormState>();
  List<PsgcLocation> _regions = [], _provinces = [], _cities = [], _barangays = [];
  PsgcLocation? _region, _province, _city, _barangay;
  bool _isNcr = false;
  bool _loadR = false, _loadP = false, _loadC = false, _loadB = false;
  String? _errR, _errP, _errC, _errB;

  // Step 3
  final _s3Key = GlobalKey<FormState>();
  final _storeCtrl = TextEditingController();
  final _storedescCtrl = TextEditingController();
  File? _permitFile;           // used on mobile
  Uint8List? _permitBytes;     // used on web
  String? _permitFileName;
  bool _agreed = false;

  bool _loading = false;
  String? _error, _success;

  @override
  void initState() {
    super.initState();
    _fetchRegions();
  }

  @override
  void dispose() {
    for (final c in [_nameCtrl, _emailCtrl, _contactCtrl, _passCtrl, _confirmCtrl, _storeCtrl, _storedescCtrl]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _fetchRegions() async {
    setState(() { _loadR = true; _errR = null; });
    try {
      final list = await PsgcService.fetchRegions();
      if (mounted) setState(() { _regions = list; _loadR = false; });
    } catch (_) {
      if (mounted) setState(() { _errR = 'Failed. Tap to retry.'; _loadR = false; });
    }
  }

  Future<void> _onRegion(PsgcLocation? r) async {
    if (r == null || r == _region) return;
    setState(() {
      _region = r; _isNcr = PsgcService.isNcr(r.code);
      _province = null; _city = null; _barangay = null;
      _provinces = []; _cities = []; _barangays = [];
      _errP = null; _errC = null; _errB = null; _loadP = true;
    });
    try {
      var list = await PsgcService.fetchProvinces(r.code);
      if (list.isEmpty) list = await PsgcService.fetchDistricts(r.code);
      if (mounted) setState(() { _provinces = list; _loadP = false; });
    } catch (_) {
      if (mounted) setState(() { _errP = 'Failed. Tap to retry.'; _loadP = false; });
    }
  }

  Future<void> _onProvince(PsgcLocation? p) async {
    if (p == null || p == _province) return;
    setState(() {
      _province = p; _city = null; _barangay = null;
      _cities = []; _barangays = []; _errC = null; _errB = null; _loadC = true;
    });
    try {
      final list = _isNcr
          ? await PsgcService.fetchCitiesByDistrict(p.code)
          : await PsgcService.fetchCitiesByProvince(p.code);
      if (mounted) setState(() { _cities = list; _loadC = false; });
    } catch (_) {
      if (mounted) setState(() { _errC = 'Failed. Tap to retry.'; _loadC = false; });
    }
  }

  Future<void> _onCity(PsgcLocation? c) async {
    if (c == null || c == _city) return;
    setState(() { _city = c; _barangay = null; _barangays = []; _errB = null; _loadB = true; });
    try {
      final list = await PsgcService.fetchBarangays(c.code);
      if (mounted) setState(() { _barangays = list; _loadB = false; });
    } catch (_) {
      if (mounted) setState(() { _errB = 'Failed. Tap to retry.'; _loadB = false; });
    }
  }

  bool _validate(int step) {
    switch (step) {
      case 0: return _s1Key.currentState?.validate() ?? false;
      case 1: return _s2Key.currentState?.validate() ?? false;
      case 2: return _s3Key.currentState?.validate() ?? false;
      default: return false;
    }
  }

  void _next() {
    if (_validate(_step)) setState(() { _error = null; _step++; });
  }

  void _back() => setState(() { _error = null; _step--; });

  Future<void> _submit() async {
    if (_loading) return;
    if (!_validate(2)) return;
    if (!_agreed) { setState(() => _error = 'Please agree to the Terms.'); return; }
    if (_permitFile == null && _permitBytes == null) {
      setState(() => _error = 'Please upload your Business Permit (PDF) to continue.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final uri = Uri.parse('${AppConfig.apiBaseUrl}/seller/register');

      // Always send JSON — bytes are pre-loaded via withData:true in FilePicker
      final body = <String, dynamic>{
        'sellername':      _nameCtrl.text.trim(),
        'selleremail':     _emailCtrl.text.trim(),
        'contactnumber':   _contactCtrl.text.trim(),
        'storename':       _storeCtrl.text.trim(),
        'storedesc':       _storedescCtrl.text.trim(),
        'region':          _region?.name ?? '',
        'province':        _province?.name ?? '',
        'city':            _city?.name ?? '',
        'barangay':        _barangay?.name ?? '',
        'password':        _passCtrl.text,
        'confirmpassword': _confirmCtrl.text,
      };

      // Attach permit as base64 if available
      if (_permitBytes != null) {
        body['businesspermit_base64'] = base64Encode(_permitBytes!);
        body['businesspermit_filename'] = _permitFileName ?? 'permit.pdf';
      } else if (_permitFile != null) {
        // Mobile fallback: read bytes from file
        final bytes = await _permitFile!.readAsBytes();
        body['businesspermit_base64'] = base64Encode(bytes);
        body['businesspermit_filename'] = _permitFileName ?? 'permit.pdf';
      }

      developer.log('POST $uri (json)', name: 'seller_register');

      http.StreamedResponse streamed;
      try {
        final req = http.Request('POST', uri)
          ..headers['Content-Type'] = 'application/json'
          ..headers['Accept'] = 'application/json'
          ..body = jsonEncode(body);
        streamed = await req.send().timeout(AppConfig.requestTimeout);
      } catch (e) {
        setState(() => _error =
            'Cannot connect to server. Make sure the server is running at ${AppConfig.apiBaseUrl}.');
        return;
      }

      final res = await http.Response.fromStream(streamed);
      developer.log('${res.statusCode}: ${res.body}', name: 'seller_register');

      Map<String, dynamic> json;
      try {
        json = jsonDecode(res.body) as Map<String, dynamic>;
      } catch (_) {
        setState(() => _error =
            'Server error (${res.statusCode}): ${res.body.length > 200 ? res.body.substring(0, 200) : res.body}');
        return;
      }

      if (res.statusCode == 201 || json['status'] == 'success') {
        final msg = json['message']?.toString() ??
            'Application submitted! We will review and contact you soon.';
        if (mounted) widget.onSuccess?.call(msg);
      } else {
        final detail = (json['data'] is Map) ? (json['data'] as Map)['error']?.toString() : null;
        final msg = json['message']?.toString() ?? 'Registration failed.';
        setState(() => _error = detail != null && detail.isNotEmpty ? '$msg\n$detail' : msg);
      }
    } catch (e, st) {
      developer.log('failed: $e', name: 'seller_register', error: e, stackTrace: st);
      setState(() => _error = 'Error: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
  // ── Shared input decoration ───────────────────────────────────────────────
  InputDecoration _dec({required String label, required String hint, required IconData icon, Widget? suffix}) {
    return authFieldDec(label: label, hint: hint, icon: icon, suffix: suffix);
  }

  Widget _sectionLabel(String text) => Padding(
    padding: const EdgeInsets.only(top: 10, bottom: 4),
    child: Text(text, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700,
        color: Color(0xFF64748B), letterSpacing: 0.5)),
  );

  // ── Step indicator ────────────────────────────────────────────────────────
  Widget _stepIndicator(List<String> labels) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        children: List.generate(labels.length * 2 - 1, (i) {
          if (i.isOdd) {
            return Expanded(child: Container(height: 2,
                color: _step > i ~/ 2 ? AppTheme.primaryBlue : const Color(0xFFE2E8F0)));
          }
          final idx = i ~/ 2;
          final active = _step == idx, done = _step > idx;
          return Column(mainAxisSize: MainAxisSize.min, children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 24, height: 24,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: done ? AppTheme.successGreen : active ? AppTheme.primaryBlue : const Color(0xFFF1F5F9),
                border: Border.all(
                  color: done ? AppTheme.successGreen : active ? AppTheme.primaryBlue : const Color(0xFFE2E8F0),
                  width: 2),
              ),
              child: Center(child: done
                  ? const Icon(Icons.check, size: 12, color: Colors.white)
                  : Text('${idx + 1}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700,
                      color: active ? Colors.white : const Color(0xFF94A3B8)))),
            ),
            const SizedBox(height: 3),
            Text(labels[idx], style: TextStyle(fontSize: 9,
                fontWeight: active ? FontWeight.w700 : FontWeight.w400,
                color: active ? AppTheme.primaryBlue : const Color(0xFF94A3B8))),
          ]);
        }),
      ),
    );
  }

  // ── Location dropdown ─────────────────────────────────────────────────────
  Widget _locDrop({
    required String label, required String hint, required IconData icon,
    required PsgcLocation? value, required List<PsgcLocation> items,
    required bool loading, required String? error,
    required Future<void> Function() onRetry,
    required ValueChanged<PsgcLocation?> onChanged,
    bool enabled = true, String? disabledHint,
  }) {
    Widget? suffix;
    if (loading) {
      suffix = const Padding(padding: EdgeInsets.all(14),
          child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)));
    } else if (error != null) {
      suffix = IconButton(onPressed: onRetry,
          icon: const Icon(FontAwesomeIcons.arrowsRotate, size: 16, color: AppTheme.primaryBlue));
    }
    final dec = _dec(label: label, hint: enabled ? hint : (disabledHint ?? hint), icon: icon, suffix: suffix)
        .copyWith(errorText: error);
    final interactive = enabled && !loading && error == null;
    return DropdownButtonFormField<PsgcLocation>(
      initialValue: value, isExpanded: true, menuMaxHeight: 300,
      decoration: dec,
      icon: interactive ? const Icon(FontAwesomeIcons.chevronDown, size: 13, color: Color(0xFF94A3B8)) : const SizedBox.shrink(),
      items: items.map((l) => DropdownMenuItem(value: l,
          child: Text(l.name, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 14, color: Color(0xFF0F172A))))).toList(),
      onChanged: interactive ? onChanged : null,
      validator: (v) => v == null ? 'Required' : null,
    );
  }

  // ── Nav buttons ───────────────────────────────────────────────────────────
  Widget _navButtons(String nextLabel) {
    return Row(children: [
      if (_step > 0) ...[
        Expanded(child: SizedBox(height: 48,
          child: OutlinedButton(
            onPressed: _loading ? null : _back,
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF0F172A),
              side: const BorderSide(color: Color(0xFFE2E8F0)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('Back', style: TextStyle(fontWeight: FontWeight.w600)),
          ),
        )),
        const SizedBox(width: 12),
      ],
      Expanded(flex: 2, child: AuthPrimaryButton(
        label: nextLabel, loading: _loading,
        onPressed: _step < 2 ? _next : _submit,
      )),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    if (_success != null) return _buildSuccess();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _stepIndicator(const ['Account', 'Location', 'Store']),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          transitionBuilder: (child, anim) => FadeTransition(opacity: anim,
              child: SlideTransition(
                  position: Tween<Offset>(begin: const Offset(0.04, 0), end: Offset.zero).animate(anim),
                  child: child)),
          child: KeyedSubtree(key: ValueKey(_step), child: _buildStep()),
        ),
        if (_error != null) ...[const SizedBox(height: 10), AuthErrorBanner(_error!)],
        const SizedBox(height: 16),
        _navButtons(_step < 2 ? 'Next' : 'Submit Application'),
        if (_step == 2) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFE2E8F0))),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(FontAwesomeIcons.circleInfo, color: Color(0xFF94A3B8), size: 13),
              const SizedBox(width: 8),
              const Expanded(child: Text(
                'Your application will be reviewed by our team. You will be notified via email once approved.',
                style: TextStyle(fontSize: 12, color: Color(0xFF64748B), height: 1.4))),
            ]),
          ),
        ],
      ],
    );
  }

  Widget _buildStep() {
    switch (_step) {
      case 0: return _step1();
      case 1: return _step2();
      case 2: return _step3();
      default: return const SizedBox.shrink();
    }
  }

  Widget _step1() => Form(key: _s1Key, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    _sectionLabel('PERSONAL INFORMATION'),
    TextFormField(controller: _nameCtrl,
        decoration: _dec(label: 'Full Name', hint: 'Your full name', icon: FontAwesomeIcons.user),
        validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
    const SizedBox(height: 12),
    TextFormField(controller: _emailCtrl, keyboardType: TextInputType.emailAddress,
        decoration: _dec(label: 'Email', hint: 'seller@email.com', icon: FontAwesomeIcons.envelope),
        validator: (v) {
          if (v == null || v.trim().isEmpty) return 'Required';
          if (!RegExp(r'^[\w\-.]+@([\w\-]+\.)+[\w\-]{2,4}$').hasMatch(v.trim())) return 'Invalid email';
          return null;
        }),
    const SizedBox(height: 12),
    TextFormField(controller: _contactCtrl, keyboardType: TextInputType.phone,
        decoration: _dec(label: 'Contact Number', hint: '09XXXXXXXXX', icon: FontAwesomeIcons.phone),
        validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
    _sectionLabel('PASSWORD'),
    TextFormField(controller: _passCtrl, obscureText: _obscurePass,
        decoration: _dec(label: 'Password', hint: 'Min. 6 characters', icon: FontAwesomeIcons.lock,
            suffix: IconButton(onPressed: () => setState(() => _obscurePass = !_obscurePass),
                icon: Icon(_obscurePass ? FontAwesomeIcons.eye : FontAwesomeIcons.eyeSlash,
                    color: const Color(0xFF94A3B8), size: 16))),
        validator: (v) {
          if (v == null || v.isEmpty) return 'Required';
          if (v.length < 6) return 'At least 6 characters';
          return null;
        }),
    const SizedBox(height: 12),
    TextFormField(controller: _confirmCtrl, obscureText: _obscureConfirm,
        decoration: _dec(label: 'Confirm Password', hint: 'Re-enter password', icon: FontAwesomeIcons.lock,
            suffix: IconButton(onPressed: () => setState(() => _obscureConfirm = !_obscureConfirm),
                icon: Icon(_obscureConfirm ? FontAwesomeIcons.eye : FontAwesomeIcons.eyeSlash,
                    color: const Color(0xFF94A3B8), size: 16))),
        validator: (v) {
          if (v == null || v.isEmpty) return 'Required';
          if (v != _passCtrl.text) return 'Passwords do not match';
          return null;
        }),
  ]));

  Widget _step2() {
    final provLabel = _isNcr ? 'District' : 'Province';
    return Form(key: _s2Key, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _sectionLabel('STORE LOCATION'),
      _locDrop(label: 'Region', hint: 'Select a region', icon: FontAwesomeIcons.map,
          value: _region, items: _regions, loading: _loadR, error: _errR,
          onRetry: _fetchRegions, onChanged: _onRegion),
      const SizedBox(height: 12),
      _locDrop(label: provLabel, hint: 'Select a $provLabel', icon: FontAwesomeIcons.locationDot,
          value: _province, items: _provinces, loading: _loadP, error: _errP,
          onRetry: () async { setState(() { _errP = null; _loadP = true; }); await _onRegion(_region); },
          onChanged: _onProvince, enabled: _region != null, disabledHint: 'Select a region first'),
      const SizedBox(height: 12),
      _locDrop(label: 'City / Municipality', hint: 'Select a city', icon: FontAwesomeIcons.city,
          value: _city, items: _cities, loading: _loadC, error: _errC,
          onRetry: () async { setState(() { _errC = null; _loadC = true; }); await _onProvince(_province); },
          onChanged: _onCity, enabled: _province != null, disabledHint: 'Select a $provLabel first'),
      const SizedBox(height: 12),
      _locDrop(label: 'Barangay', hint: 'Select a barangay', icon: FontAwesomeIcons.houseFlag,
          value: _barangay, items: _barangays, loading: _loadB, error: _errB,
          onRetry: () async { setState(() { _errB = null; _loadB = true; }); await _onCity(_city); },
          onChanged: (v) { if (v != null) setState(() => _barangay = v); },
          enabled: _city != null, disabledHint: 'Select a city first'),
    ]));
  }

  Widget _step3() => Form(key: _s3Key, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    _sectionLabel('STORE INFORMATION'),
    TextFormField(controller: _storeCtrl,
        decoration: _dec(label: 'Store Name', hint: 'Your store name', icon: FontAwesomeIcons.store),
        validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
    const SizedBox(height: 12),
    TextFormField(controller: _storedescCtrl,
        maxLines: 3,
        decoration: _dec(label: 'Store Description', hint: 'Brief description of your store', icon: FontAwesomeIcons.alignLeft),
        validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
    const SizedBox(height: 14),
    // Business Permit Upload
    _sectionLabel('BUSINESS PERMIT'),
    GestureDetector(
      onTap: () async {
        final result = await FilePicker.pickFiles(
          type: FileType.custom,
          allowedExtensions: ['pdf'],
          allowMultiple: false,
          withData: true, // always load bytes — works on web and mobile
        );
        if (result != null && result.files.isNotEmpty && mounted) {
          final picked = result.files.first;
          // Use bytes if available (always on web, and when withData:true on mobile)
          if (picked.bytes != null) {
            setState(() {
              _permitBytes = picked.bytes;
              _permitFile = null;
              _permitFileName = picked.name;
            });
          } else if (!kIsWeb && picked.path != null) {
            // Fallback for mobile if bytes not loaded
            setState(() {
              _permitFile = File(picked.path!);
              _permitBytes = null;
              _permitFileName = picked.name;
            });
          }
        }
      },
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: (_permitFile != null || _permitBytes != null) ? AppTheme.primaryBlue : const Color(0xFFE2E8F0),
            width: (_permitFile != null || _permitBytes != null) ? 1.5 : 1,
          ),
        ),
        child: Row(children: [
          Icon(
            (_permitFile != null || _permitBytes != null) ? FontAwesomeIcons.fileCircleCheck : FontAwesomeIcons.fileArrowUp,
            color: (_permitFile != null || _permitBytes != null) ? AppTheme.primaryBlue : const Color(0xFF94A3B8),
            size: 18,
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              (_permitFile != null || _permitBytes != null) ? 'Permit selected ✓' : 'Upload Business Permit (PDF)',
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 13,
                color: (_permitFile != null || _permitBytes != null) ? AppTheme.primaryBlue : const Color(0xFF0F172A),
              ),
            ),
            const SizedBox(height: 2),
            Text(
              (_permitFile != null || _permitBytes != null)
                  ? (_permitFileName ?? 'File selected')
                  : 'Tap to select a PDF file',
              style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ])),
          if (_permitFile != null || _permitBytes != null)
            GestureDetector(
              onTap: () => setState(() { _permitFile = null; _permitBytes = null; _permitFileName = null; }),
              child: const Icon(Icons.close, size: 16, color: Color(0xFF94A3B8)),
            ),
        ]),
      ),
    ),
    const SizedBox(height: 14),
    GestureDetector(
      onTap: () => setState(() => _agreed = !_agreed),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          width: 20, height: 20,
          decoration: BoxDecoration(
            color: _agreed ? AppTheme.primaryBlue : Colors.white,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: _agreed ? AppTheme.primaryBlue : const Color(0xFFE2E8F0), width: 1.5)),
          child: _agreed ? const Icon(Icons.check, size: 14, color: Colors.white) : null,
        ),
        const SizedBox(width: 10),
        const Expanded(child: Text.rich(TextSpan(
          style: TextStyle(fontSize: 13, color: Color(0xFF0F172A)),
          children: [
            TextSpan(text: 'I agree to the '),
            TextSpan(text: 'Seller Terms and Conditions',
                style: TextStyle(color: AppTheme.primaryBlue, fontWeight: FontWeight.w600)),
          ],
        ))),
      ]),
    ),
  ]));

  Widget _buildSuccess() => Center(child: Padding(
    padding: const EdgeInsets.all(32),
    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      Container(width: 72, height: 72,
          decoration: BoxDecoration(color: AppTheme.successGreen.withValues(alpha: 0.1), shape: BoxShape.circle),
          child: const Icon(FontAwesomeIcons.circleCheck, color: AppTheme.successGreen, size: 36)),
      const SizedBox(height: 20),
      const Text('Application Submitted!',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Color(0xFF0F172A)),
          textAlign: TextAlign.center),
      const SizedBox(height: 8),
      Text(_success!, style: const TextStyle(fontSize: 14, color: Color(0xFF64748B), height: 1.5),
          textAlign: TextAlign.center),
      const SizedBox(height: 28),
      AuthPrimaryButton(label: 'Back to Home', loading: false,
          onPressed: () => Navigator.pushNamedAndRemoveUntil(context, '/home', (r) => false)),
    ]),
  ));
}
