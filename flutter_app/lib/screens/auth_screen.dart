import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../providers/auth_provider.dart';
import '../core/theme/app_theme.dart';
import '../services/psgc_service.dart';
import 'auth/auth_form.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Background colour matching the screenshot (#EEF2F7 — light blue-gray)
// ─────────────────────────────────────────────────────────────────────────────
const _kBg = Color(0xFFEEF2F7);

// ─────────────────────────────────────────────────────────────────────────────
// Shared shell used by all three auth screens.
//
// Layout:
//   Mobile  → full-screen white card (no left panel)
//   Tablet+ → left panel (illustration) + right white card
// ─────────────────────────────────────────────────────────────────────────────
class AuthShell extends StatelessWidget {
  /// Widget shown in the left illustration panel (tablet+).
  final Widget illustration;

  /// The white card content (form + links).
  final Widget card;

  const AuthShell({
    super.key,
    required this.illustration,
    required this.card,
  });

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.of(context).size.width > 640;

    return Scaffold(
      backgroundColor: _kBg,
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: wide ? _wideLayout(context) : _narrowLayout(context),
      ),
    );
  }

  Widget _wideLayout(BuildContext context) {
    return Row(
      children: [
        // Left — illustration
        Expanded(
          flex: 6,
          child: Container(
            color: _kBg,
            child: Center(child: illustration),
          ),
        ),
        // Right — white card, full height, scrollable
        Expanded(
          flex: 4,
          child: Container(
            color: _kBg,
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                    horizontal: 32, vertical: 40),
                child: _cardContainer(card),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _narrowLayout(BuildContext context) {
    final keyboardVisible = MediaQuery.of(context).viewInsets.bottom > 100;
    final bottomPadding = MediaQuery.of(context).viewInsets.bottom;
    return SingleChildScrollView(
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: EdgeInsets.fromLTRB(
        24,
        keyboardVisible ? 16 : 48,
        24,
        keyboardVisible ? bottomPadding + 16 : 48,
      ),
      child: Column(
        children: [
          // Hide illustration when keyboard is open to save space
          if (!keyboardVisible) ...[
            SizedBox(height: 120, child: Center(child: illustration)),
            const SizedBox(height: 20),
          ],
          _cardContainer(card),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _cardContainer(Widget child) {
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(maxWidth: 420),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.10),
            blurRadius: 40,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
      child: child,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Default illustration — the two happy-hands logo image
// ─────────────────────────────────────────────────────────────────────────────
class _HappyHandsIllustration extends StatelessWidget {
  const _HappyHandsIllustration();

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/logos/logoo.png',
      width: 260,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) => const _FallbackIllustration(),
    );
  }
}

class _FallbackIllustration extends StatelessWidget {
  const _FallbackIllustration();

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Two overlapping hand emojis mimicking the logo
        const Text('🤚🖐', style: TextStyle(fontSize: 80)),
        const SizedBox(height: 16),
        const Text(
          'Happy Hands',
          style: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w800,
            color: Color(0xFF2C5AA0),
            letterSpacing: -0.5,
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Customer Auth Screen  (Login + Sign up)
// ─────────────────────────────────────────────────────────────────────────────
class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  // 0 = login, 1 = signup
  int _view = 0;

  @override
  Widget build(BuildContext context) {
    return AuthShell(
      illustration: const _HappyHandsIllustration(),
      card: _view == 0 ? _buildLoginCard() : _buildSignupCard(),
    );
  }

  // ── Login card ─────────────────────────────────────────────────────────────
  Widget _buildLoginCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'Welcome Back',
          style: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w800,
            color: Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Please enter your details to sign in.',
          style: TextStyle(fontSize: 14, color: Color(0xFF64748B)),
        ),
        const SizedBox(height: 28),
        const AuthForm(role: AuthRole.buyer, showForgotPassword: true),
        const SizedBox(height: 20),
        Center(
          child: RichText(
            text: TextSpan(
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
              children: [
                const TextSpan(text: "Don't have an account? "),
                WidgetSpan(
                  alignment: PlaceholderAlignment.middle,
                  child: GestureDetector(
                    onTap: () => setState(() => _view = 1),
                    child: const Text(
                      'Sign up',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF2563EB),
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

  // ── Sign-up card ───────────────────────────────────────────────────────────
  Widget _buildSignupCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'Create Account',
          style: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w800,
            color: Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Fill in your details to get started.',
          style: TextStyle(fontSize: 14, color: Color(0xFF64748B)),
        ),
        const SizedBox(height: 28),
        _UserRegisterForm(onSuccess: () => setState(() => _view = 0)),
        const SizedBox(height: 20),
        Center(
          child: RichText(
            text: TextSpan(
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
              children: [
                const TextSpan(text: 'Already have an account? '),
                WidgetSpan(
                  alignment: PlaceholderAlignment.middle,
                  child: GestureDetector(
                    onTap: () => setState(() => _view = 0),
                    child: const Text(
                      'Sign in',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF2563EB),
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
}

// ─────────────────────────────────────────────────────────────────────────────
// Customer registration form
// ─────────────────────────────────────────────────────────────────────────────
class _UserRegisterForm extends StatefulWidget {
  final VoidCallback? onSuccess;
  const _UserRegisterForm({this.onSuccess});

  @override
  State<_UserRegisterForm> createState() => _UserRegisterFormState();
}

class _UserRegisterFormState extends State<_UserRegisterForm> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _contactCtrl = TextEditingController();

  // PSGC Lists
  List<PsgcLocation> _regions = [];
  List<PsgcLocation> _provincesOrDistricts = [];
  List<PsgcLocation> _cities = [];
  List<PsgcLocation> _barangays = [];

  // Selected Values
  PsgcLocation? _selectedRegion;
  PsgcLocation? _selectedProvince;
  PsgcLocation? _selectedCity;
  PsgcLocation? _selectedBarangay;

  // Loading States
  bool _isLoadingRegions = false;
  bool _isLoadingProvinces = false;
  bool _isLoadingCities = false;
  bool _isLoadingBarangays = false;

  bool _obscurePass = true;
  bool _obscureConfirm = true;

  @override
  void initState() {
    super.initState();
    _loadRegions();
  }

  Future<void> _loadRegions() async {
    setState(() => _isLoadingRegions = true);
    try {
      final regions = await PsgcService.fetchRegions();
      if (mounted) setState(() => _regions = regions);
    } catch (e) {
      debugPrint('Error loading regions: $e');
    } finally {
      if (mounted) setState(() => _isLoadingRegions = false);
    }
  }

  Future<void> _onRegionChanged(PsgcLocation? val) async {
    if (val == null || val == _selectedRegion) return;
    setState(() {
      _selectedRegion = val;
      _selectedProvince = null;
      _selectedCity = null;
      _selectedBarangay = null;
      _provincesOrDistricts = [];
      _cities = [];
      _barangays = [];
      _isLoadingProvinces = true;
    });

    try {
      List<PsgcLocation> items;
      if (PsgcService.isNcr(val.code)) {
        items = await PsgcService.fetchDistricts(val.code);
      } else {
        items = await PsgcService.fetchProvinces(val.code);
      }
      if (mounted) setState(() => _provincesOrDistricts = items);
    } catch (e) {
      debugPrint('Error loading provinces: $e');
    } finally {
      if (mounted) setState(() => _isLoadingProvinces = false);
    }
  }

  Future<void> _onProvinceChanged(PsgcLocation? val) async {
    if (val == null || val == _selectedProvince) return;
    setState(() {
      _selectedProvince = val;
      _selectedCity = null;
      _selectedBarangay = null;
      _cities = [];
      _barangays = [];
      _isLoadingCities = true;
    });

    try {
      List<PsgcLocation> items;
      if (PsgcService.isNcr(_selectedRegion?.code ?? '')) {
        items = await PsgcService.fetchCitiesByDistrict(val.code);
      } else {
        items = await PsgcService.fetchCitiesByProvince(val.code);
      }
      if (mounted) setState(() => _cities = items);
    } catch (e) {
      debugPrint('Error loading cities: $e');
    } finally {
      if (mounted) setState(() => _isLoadingCities = false);
    }
  }

  Future<void> _onCityChanged(PsgcLocation? val) async {
    if (val == null || val == _selectedCity) return;
    setState(() {
      _selectedCity = val;
      _selectedBarangay = null;
      _barangays = [];
      _isLoadingBarangays = true;
    });

    try {
      final items = await PsgcService.fetchBarangays(val.code);
      if (mounted) setState(() => _barangays = items);
    } catch (e) {
      debugPrint('Error loading barangays: $e');
    } finally {
      if (mounted) setState(() => _isLoadingBarangays = false);
    }
  }

  @override
  void dispose() {
    for (final c in [
      _nameCtrl, _emailCtrl, _passCtrl, _confirmCtrl,
      _addressCtrl, _contactCtrl,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedRegion == null || _selectedProvince == null ||
        _selectedCity == null || _selectedBarangay == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Please select all location fields'),
        backgroundColor: AppTheme.errorRed,
      ));
      return;
    }

    final auth = context.read<AuthProvider>();
    await auth.register(
      email: _emailCtrl.text.trim(),
      password: _passCtrl.text,
      displayName: _nameCtrl.text.trim(),
      region: _selectedRegion!.name,
      province: _selectedProvince!.name,
      city: _selectedCity!.name,
      barangay: _selectedBarangay!.name,
      homeAddress: _addressCtrl.text.trim(),
      contactNumber: _contactCtrl.text.trim(),
    );
    if (!mounted) return;
    if (auth.error != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(auth.error!),
        backgroundColor: AppTheme.errorRed,
      ));
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
      content: Text('Registration successful! Please sign in.'),
      backgroundColor: AppTheme.successGreen,
    ));
    widget.onSuccess?.call();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        return Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (auth.error != null) AuthErrorBanner(auth.error!),
              TextFormField(
                controller: _nameCtrl,
                decoration: authFieldDec(
                    label: 'Full Name',
                    hint: 'Your full name',
                    icon: FontAwesomeIcons.user),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: authFieldDec(
                    label: 'Email',
                    hint: 'Enter your email',
                    icon: FontAwesomeIcons.envelope),
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Required';
                  if (!RegExp(r'^[\w\-.]+@([\w\-]+\.)+[\w\-]{2,4}$')
                      .hasMatch(v)) { return 'Enter a valid email'; }
                  return null;
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _passCtrl,
                obscureText: _obscurePass,
                decoration: authFieldDec(
                  label: 'Password',
                  hint: 'Create a password',
                  icon: FontAwesomeIcons.lock,
                  suffix: IconButton(
                    onPressed: () =>
                        setState(() => _obscurePass = !_obscurePass),
                    icon: Icon(
                      _obscurePass
                          ? FontAwesomeIcons.eye
                          : FontAwesomeIcons.eyeSlash,
                      color: const Color(0xFF94A3B8),
                      size: 16,
                    ),
                  ),
                ),
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Required';
                  if (v.length < 6) return 'At least 6 characters';
                  return null;
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _confirmCtrl,
                obscureText: _obscureConfirm,
                decoration: authFieldDec(
                  label: 'Confirm Password',
                  hint: 'Re-enter password',
                  icon: FontAwesomeIcons.lock,
                  suffix: IconButton(
                    onPressed: () =>
                        setState(() => _obscureConfirm = !_obscureConfirm),
                    icon: Icon(
                      _obscureConfirm
                          ? FontAwesomeIcons.eye
                          : FontAwesomeIcons.eyeSlash,
                      color: const Color(0xFF94A3B8),
                      size: 16,
                    ),
                  ),
                ),
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Required';
                  if (v != _passCtrl.text) return 'Passwords do not match';
                  return null;
                },
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<PsgcLocation>(
                initialValue: _selectedRegion,
                decoration: authFieldDec(
                  label: 'Region',
                  hint: _isLoadingRegions ? 'Loading...' : 'Select Region',
                  icon: FontAwesomeIcons.locationDot,
                  suffix: _isLoadingRegions
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : null,
                ),
                items: _regions
                    .map((l) => DropdownMenuItem(
                          value: l,
                          child: Text(l.name,
                              style: const TextStyle(fontSize: 14)),
                        ))
                    .toList(),
                onChanged: _isLoadingRegions ? null : _onRegionChanged,
                validator: (v) => v == null ? 'Required' : null,
                dropdownColor: Colors.white,
                isExpanded: true,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<PsgcLocation>(
                initialValue: _selectedProvince,
                decoration: authFieldDec(
                  label: 'Province / District',
                  hint: _isLoadingProvinces ? 'Loading...' : 'Select Province',
                  icon: FontAwesomeIcons.mapLocationDot,
                  suffix: _isLoadingProvinces
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : null,
                ),
                items: _provincesOrDistricts
                    .map((l) => DropdownMenuItem(
                          value: l,
                          child: Text(l.name,
                              style: const TextStyle(fontSize: 14)),
                        ))
                    .toList(),
                onChanged: (_isLoadingProvinces || _selectedRegion == null)
                    ? null
                    : _onProvinceChanged,
                validator: (v) => v == null ? 'Required' : null,
                dropdownColor: Colors.white,
                isExpanded: true,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<PsgcLocation>(
                initialValue: _selectedCity,
                decoration: authFieldDec(
                  label: 'City / Municipality',
                  hint: _isLoadingCities ? 'Loading...' : 'Select City',
                  icon: FontAwesomeIcons.city,
                  suffix: _isLoadingCities
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : null,
                ),
                items: _cities
                    .map((l) => DropdownMenuItem(
                          value: l,
                          child: Text(l.name,
                              style: const TextStyle(fontSize: 14)),
                        ))
                    .toList(),
                onChanged: (_isLoadingCities || _selectedProvince == null)
                    ? null
                    : _onCityChanged,
                validator: (v) => v == null ? 'Required' : null,
                dropdownColor: Colors.white,
                isExpanded: true,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<PsgcLocation>(
                initialValue: _selectedBarangay,
                decoration: authFieldDec(
                  label: 'Barangay',
                  hint: _isLoadingBarangays ? 'Loading...' : 'Select Barangay',
                  icon: FontAwesomeIcons.locationPin,
                  suffix: _isLoadingBarangays
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : null,
                ),
                items: _barangays
                    .map((l) => DropdownMenuItem(
                          value: l,
                          child: Text(l.name,
                              style: const TextStyle(fontSize: 14)),
                        ))
                    .toList(),
                onChanged: (_isLoadingBarangays || _selectedCity == null)
                    ? null
                    : (PsgcLocation? val) => setState(() => _selectedBarangay = val),
                validator: (v) => v == null ? 'Required' : null,
                dropdownColor: Colors.white,
                isExpanded: true,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _addressCtrl,
                decoration: authFieldDec(
                    label: 'Home Address',
                    hint: 'House no., street, landmark',
                    icon: FontAwesomeIcons.house),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _contactCtrl,
                keyboardType: TextInputType.phone,
                decoration: authFieldDec(
                    label: 'Contact Number',
                    hint: '09XXXXXXXXX',
                    icon: FontAwesomeIcons.phone),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 20),
              AuthPrimaryButton(
                label: 'Create Account',
                loading: auth.isLoading,
                onPressed: _register,
              ),
            ],
          ),
        );
      },
    );
  }
}
