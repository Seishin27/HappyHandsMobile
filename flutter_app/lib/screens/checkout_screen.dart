import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../models/cart_item.dart';
import '../providers/auth_provider.dart';
import '../providers/cart_provider.dart';
import '../services/flask_api_service.dart';
import '../services/psgc_service.dart';
import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';

class CheckoutScreen extends StatefulWidget {
  final List<CartItem> selectedItems;
  const CheckoutScreen({super.key, required this.selectedItems});

  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  final _formKey = GlobalKey<FormState>();

  // PSGC state
  List<PsgcLocation> _regions = [];
  List<PsgcLocation> _provinces = [];
  List<PsgcLocation> _cities = [];
  List<PsgcLocation> _barangays = [];

  PsgcLocation? _selectedRegion;
  PsgcLocation? _selectedProvince;
  PsgcLocation? _selectedCity;
  PsgcLocation? _selectedBarangay;

  bool _loadingRegions = false;
  bool _loadingProvinces = false;
  bool _loadingCities = false;
  bool _loadingBarangays = false;
  bool _loadingShipping = false;
  double _shippingCost = 36.0; // minimum shipping fee

  // Text fields
  final _homeAddressController = TextEditingController();
  final _contactController = TextEditingController();

  bool _isProcessing = false;
  bool _loadingAddress = true;

  @override
  void initState() {
    super.initState();
    _loadRegions();
    _loadSavedAddress();
    _homeAddressController.addListener(_onDeliveryFieldChanged);
    _contactController.addListener(_onDeliveryFieldChanged);
  }

  @override
  void dispose() {
    _homeAddressController.removeListener(_onDeliveryFieldChanged);
    _contactController.removeListener(_onDeliveryFieldChanged);
    _homeAddressController.dispose();
    _contactController.dispose();
    super.dispose();
  }

  void _onDeliveryFieldChanged() {
    if (!mounted || _loadingAddress) return;
    _refreshShippingEstimate();
  }

  FlaskApiService get _api => context.read<FlaskApiService>();

  Future<void> _loadRegions() async {
    setState(() => _loadingRegions = true);
    try {
      final list = await PsgcService.fetchRegions();
      if (mounted) setState(() => _regions = list);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingRegions = false);
    }
  }

  Future<void> _loadSavedAddress() async {
    setState(() => _loadingAddress = true);
    try {
      final saved = await _api.fetchSavedAddress();
      if (saved != null && mounted) {
        _homeAddressController.text = saved['home_address'] ?? '';
        _contactController.text = saved['contact_number'] ?? '';

        // Restore PSGC selections by name (wait for regions to load first)
        final regionName = saved['region'] ?? '';
        final provinceName = saved['province'] ?? '';
        final cityName = saved['city'] ?? '';
        final barangayName = saved['barangay'] ?? '';

        if (regionName.isNotEmpty) {
          await _ensureRegionsLoaded();
          final region = _regions.cast<PsgcLocation?>().firstWhere(
            (r) => r!.name == regionName,
            orElse: () => null,
          );
          if (region != null && mounted) {
            setState(() => _selectedRegion = region);
            await _onRegionChanged(region, preselect: provinceName);

            if (provinceName.isNotEmpty) {
              final province = _provinces.cast<PsgcLocation?>().firstWhere(
                (p) => p!.name == provinceName,
                orElse: () => null,
              );
              if (province != null && mounted) {
                setState(() => _selectedProvince = province);
                await _onProvinceChanged(province, preselect: cityName);

                if (cityName.isNotEmpty) {
                  final city = _cities.cast<PsgcLocation?>().firstWhere(
                    (c) => c!.name == cityName,
                    orElse: () => null,
                  );
                  if (city != null && mounted) {
                    setState(() => _selectedCity = city);
                    await _onCityChanged(city, preselect: barangayName);
                  }
                }
              }
            }
            await _refreshShippingEstimate();
          }
        }
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingAddress = false);
    }
  }

  Future<void> _ensureRegionsLoaded() async {
    if (_regions.isNotEmpty) return;
    final list = await PsgcService.fetchRegions();
    if (mounted) setState(() => _regions = list);
  }

  Future<void> _onRegionChanged(PsgcLocation region, {String preselect = ''}) async {
    setState(() {
      _selectedRegion = region;
      _selectedProvince = null;
      _selectedCity = null;
      _selectedBarangay = null;
      _provinces = [];
      _cities = [];
      _barangays = [];
      _loadingProvinces = true;
    });
    try {
      final list = PsgcService.isNcr(region.code)
          ? await PsgcService.fetchDistricts(region.code)
          : await PsgcService.fetchProvinces(region.code);
      if (mounted) {
        setState(() => _provinces = list);
        if (preselect.isNotEmpty) {
          final match = list.cast<PsgcLocation?>().firstWhere(
            (p) => p!.name == preselect,
            orElse: () => null,
          );
          if (match != null) setState(() => _selectedProvince = match);
        }
      }
      await _refreshShippingEstimate();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingProvinces = false);
    }
  }

  Future<void> _onProvinceChanged(PsgcLocation province, {String preselect = ''}) async {
    setState(() {
      _selectedProvince = province;
      _selectedCity = null;
      _selectedBarangay = null;
      _cities = [];
      _barangays = [];
      _loadingCities = true;
    });
    try {
      final isNcr = _selectedRegion != null && PsgcService.isNcr(_selectedRegion!.code);
      final list = isNcr
          ? await PsgcService.fetchCitiesByDistrict(province.code)
          : await PsgcService.fetchCitiesByProvince(province.code);
      if (mounted) {
        setState(() => _cities = list);
        if (preselect.isNotEmpty) {
          final match = list.cast<PsgcLocation?>().firstWhere(
            (c) => c!.name == preselect,
            orElse: () => null,
          );
          if (match != null) setState(() => _selectedCity = match);
        }
      }
      await _refreshShippingEstimate();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingCities = false);
    }
  }

  Future<void> _onCityChanged(PsgcLocation city, {String preselect = ''}) async {
    setState(() {
      _selectedCity = city;
      _selectedBarangay = null;
      _barangays = [];
      _loadingBarangays = true;
    });
    try {
      final list = await PsgcService.fetchBarangays(city.code);
      if (mounted) {
        setState(() => _barangays = list);
        if (preselect.isNotEmpty) {
          final match = list.cast<PsgcLocation?>().firstWhere(
            (b) => b!.name == preselect,
            orElse: () => null,
          );
          if (match != null) setState(() => _selectedBarangay = match);
        }
      }
      await _refreshShippingEstimate();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingBarangays = false);
    }
  }

  Future<void> _refreshShippingEstimate() async {
    if (_selectedRegion == null || _selectedProvince == null || _selectedCity == null || _selectedBarangay == null) {
      if (mounted) {
        setState(() => _shippingCost = 36.0); // show minimum while address incomplete
      }
      return;
    }

    setState(() => _loadingShipping = true);
    try {
      final productIds = widget.selectedItems.map((e) => e.product.id).toList();
      final shipping = await _api.estimateShipping(
        region: _selectedRegion!.name,
        province: _selectedProvince!.name,
        city: _selectedCity!.name,
        barangay: _selectedBarangay!.name,
        productIds: productIds,
      );
      if (mounted) {
        setState(() => _shippingCost = shipping < 36.0 ? 36.0 : shipping);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _shippingCost = 36.0); // fallback to minimum
      }
    } finally {
      if (mounted) {
        setState(() => _loadingShipping = false);
      }
    }
  }

  InputDecoration _dec(String label, {IconData? icon, String? hint}) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      hintStyle: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 13),
      labelStyle: const TextStyle(
          color: Color(0xFF374151), fontSize: 13, fontWeight: FontWeight.w500),
      prefixIcon: icon != null
          ? Icon(icon, color: AppTheme.mediumGray, size: 16)
          : null,
      contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFFD1D5DB))),
      enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFFD1D5DB))),
      focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFF2563EB), width: 1.5)),
      errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppTheme.errorRed)),
      focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppTheme.errorRed)),
      filled: true,
      fillColor: AppTheme.white,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: const Text(
          'Checkout',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        backgroundColor: AppTheme.white,
        foregroundColor: AppTheme.darkBlue,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: AppTheme.borderGray),
        ),
      ),
      body: widget.selectedItems.isEmpty
          ? _buildEmptyState()
          : Form(
              key: _formKey,
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Page title (matches web)
                    const Text(
                      'Checkout',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF111827),
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Review your delivery details and confirm your order.',
                      style: TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
                    ),
                    const SizedBox(height: 20),
                    // Delivery details card
                    _buildDeliveryCard(),
                    const SizedBox(height: 16),
                    // Order summary card (matches web right panel)
                    _buildOrderSummaryCard(),
                    const SizedBox(height: 16),
                    // Place order button
                    _buildPlaceOrderButton(),
                  ],
                ),
              ),
            ),
    );
  }

  // ── Delivery details card (matches web left panel) ──────────────────────

  Widget _buildDeliveryCard() {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.07),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Card header
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Delivery details',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF111827),
                  ),
                ),
                if (_loadingAddress)
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
            child: _buildShippingFields(),
          ),
        ],
      ),
    );
  }

  Widget _buildShippingFields() {
    if (_loadingAddress) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 16),
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      );
    }
    return Column(
      children: [
        // Region + Province row
        Row(
          children: [
            Expanded(
              child: _psgcDropdown<PsgcLocation>(
                label: 'Region',
                value: _selectedRegion,
                items: _regions,
                loading: _loadingRegions,
                onChanged: (v) { if (v != null) _onRegionChanged(v); },
                validator: (v) => v == null ? 'Required' : null,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _psgcDropdown<PsgcLocation>(
                label: _selectedRegion != null && PsgcService.isNcr(_selectedRegion!.code)
                    ? 'District'
                    : 'Province',
                value: _selectedProvince,
                items: _provinces,
                loading: _loadingProvinces,
                enabled: _selectedRegion != null,
                onChanged: (v) { if (v != null) _onProvinceChanged(v); },
                validator: (v) => v == null ? 'Required' : null,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        // City + Barangay row
        Row(
          children: [
            Expanded(
              child: _psgcDropdown<PsgcLocation>(
                label: 'City / Municipality',
                value: _selectedCity,
                items: _cities,
                loading: _loadingCities,
                enabled: _selectedProvince != null,
                onChanged: (v) { if (v != null) _onCityChanged(v); },
                validator: (v) => v == null ? 'Required' : null,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _psgcDropdown<PsgcLocation>(
                label: 'Barangay',
                value: _selectedBarangay,
                items: _barangays,
                loading: _loadingBarangays,
                enabled: _selectedCity != null,
                onChanged: (v) {
                  setState(() => _selectedBarangay = v);
                  _refreshShippingEstimate();
                },
                validator: (v) => v == null ? 'Required' : null,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        // Home address
        TextFormField(
          controller: _homeAddressController,
          decoration: _dec(
            'Home address / landmark *',
            hint: 'House, street, village, or landmark',
          ),
          validator: (v) =>
              (v == null || v.trim().isEmpty) ? 'Please enter your address' : null,
        ),
        const SizedBox(height: 10),
        // Contact number
        TextFormField(
          controller: _contactController,
          keyboardType: TextInputType.phone,
          decoration: _dec(
            'Contact number *',
            hint: '09XX-XXX-XXXX',
          ),
          validator: (v) =>
              (v == null || v.trim().isEmpty) ? 'Please enter your contact number' : null,
        ),
      ],
    );
  }

  // ── Order summary card (matches web right panel) ─────────────────────────

  Widget _buildOrderSummaryCard() {
    final items = widget.selectedItems;
    final subtotal = items.fold(0.0, (s, e) => s + e.subtotal);
    final shipping = _shippingCost;
    final total = subtotal + shipping;

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.08),
            blurRadius: 32,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          const Text(
            'Order summary',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: Color(0xFF111827),
            ),
          ),
          const SizedBox(height: 8),
          const Divider(color: Color(0xFFE5E7EB), height: 1),
          const SizedBox(height: 8),
          // Items
          ...items.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Flexible(
                            child: Text(
                              item.product.name,
                              style: const TextStyle(
                                fontSize: 13,
                                color: Color(0xFF111827),
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '× ${item.quantity}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: Color(0xFF6B7280),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      '₱${item.subtotal.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF111827),
                      ),
                    ),
                  ],
                ),
              )),
          const SizedBox(height: 8),
          const Divider(color: Color(0xFFE5E7EB), height: 1),
          const SizedBox(height: 8),
          // Subtotal
          _summaryRow('Subtotal', '₱${subtotal.toStringAsFixed(2)}'),
          const SizedBox(height: 4),
          // Shipping with loading indicator
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Shipping',
                style: TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
              ),
              _loadingShipping
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(
                      '₱${shipping.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF111827),
                      ),
                    ),
            ],
          ),
          const SizedBox(height: 8),
          const Divider(color: Color(0xFFE5E7EB), height: 1),
          const SizedBox(height: 8),
          // Total
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Total',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF111827),
                ),
              ),
              Text(
                '₱${total.toStringAsFixed(2)}',
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF111827),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          // Payment section (COD)
          const Text(
            'Payment',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Color(0xFF111827),
            ),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFF9FAFB),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFE5E7EB)),
            ),
            child: Row(
              children: [
                Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: AppTheme.primaryBlue, width: 2),
                  ),
                  child: Center(
                    child: Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.primaryBlue,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Cash on Delivery (COD)',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF111827),
                        ),
                      ),
                      Text(
                        'Pay safely with cash when your order arrives.',
                        style: TextStyle(
                          fontSize: 11,
                          color: Color(0xFF6B7280),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value) => Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
          Text(value,
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF111827))),
        ],
      );

  // _buildShippingSection replaced by _buildDeliveryCard + _buildShippingFields above

  Widget _psgcDropdown<T extends PsgcLocation>({
    required String label,
    required T? value,
    required List<T> items,
    required bool loading,
    bool enabled = true,
    required void Function(T?) onChanged,
    required String? Function(T?) validator,
  }) {
    final effectiveEnabled = enabled && !loading && items.isNotEmpty;
    return DropdownButtonFormField<T>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(
        labelText: loading ? '$label...' : label,
        labelStyle: const TextStyle(
            color: Color(0xFF374151), fontSize: 12, fontWeight: FontWeight.w500),
        contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFFD1D5DB))),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFFD1D5DB))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFF2563EB), width: 1.5)),
        errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.errorRed)),
        focusedErrorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.errorRed)),
        filled: true,
        fillColor: AppTheme.white,
      ),
      hint: Text(
        loading ? 'Loading...' : 'Select $label',
        style: TextStyle(
            color: effectiveEnabled ? const Color(0xFF9CA3AF) : Colors.grey[400],
            fontSize: 12),
      ),
      items: items
          .map((e) => DropdownMenuItem<T>(
                value: e,
                child: Text(e.name,
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                    style: const TextStyle(fontSize: 13)),
              ))
          .toList(),
      onChanged: effectiveEnabled ? onChanged : null,
      validator: validator,
    );
  }

  // _buildPaymentSection is now embedded inside _buildOrderSummaryCard

  Widget _buildPlaceOrderButton() {
    final total = widget.selectedItems.fold(0.0, (s, e) => s + e.subtotal) + _shippingCost;
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: _isProcessing
          ? Container(
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF2C5AA0), Color(0xFF1E3A5F)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(999),
              ),
              child: const Center(
                child: SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                  ),
                ),
              ),
            )
          : GestureDetector(
              onTap: _placeOrder,
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF2C5AA0), Color(0xFF1E3A5F)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(999),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF2563EB).withValues(alpha: 0.35),
                      blurRadius: 25,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Center(
                  child: Text(
                    'Place order  —  ₱${total.toStringAsFixed(2)}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spacingXL),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(FontAwesomeIcons.cartShopping,
                size: 56, color: AppTheme.mediumGray),
            const SizedBox(height: 16),
            Text('No items selected',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(color: AppTheme.darkBlue)),
            const SizedBox(height: 8),
            Text('Go back to cart and select items to checkout.',
                textAlign: TextAlign.center,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: AppTheme.mediumGray)),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: AppTheme.white),
              child: const Text('Back to Cart'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _placeOrder() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isProcessing = true);
    try {
      final api = _api;
      final productIds =
          widget.selectedItems.map((e) => e.product.id).toList();

      final result = await api.placeOrder(
        region: _selectedRegion!.name,
        province: _selectedProvince!.name,
        city: _selectedCity!.name,
        barangay: _selectedBarangay!.name,
        homeAddress: _homeAddressController.text.trim(),
        contactNumber: _contactController.text.trim(),
        productIds: productIds,
      );

      if (!mounted) return;

      // Clear local cart state
      final cartProvider = context.read<CartProvider>();
      final authProvider = context.read<AuthProvider>();
      await cartProvider.loadCart(authProvider.backendAccessToken);

      final orderNumbers = (result['order_numbers'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          [];

      _showSuccessDialog(orderNumbers);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(e.toString().replaceFirst('Exception: ', '')),
          backgroundColor: AppTheme.errorRed,
        ));
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  void _showSuccessDialog(List<String> orderNumbers) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(FontAwesomeIcons.circleCheck,
                color: Colors.green, size: 22),
            const SizedBox(width: 10),
            Text('Order Placed!',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: AppTheme.darkBlue, fontWeight: FontWeight.w700)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Thank you for your order!'),
            if (orderNumbers.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text('Order Number${orderNumbers.length > 1 ? 's' : ''}:',
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              ...orderNumbers.map((n) => Text(n,
                  style: const TextStyle(
                      color: AppTheme.primaryBlue,
                      fontWeight: FontWeight.w500,
                      fontSize: 12))),
            ],
            const SizedBox(height: 10),
            const Text('You can track your order in My Orders.'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).pushNamedAndRemoveUntil('/orders', (r) => r.isFirst);
            },
            child: const Text('View Orders'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).pushNamedAndRemoveUntil('/', (_) => false);
            },
            style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryBlue,
                foregroundColor: AppTheme.white),
            child: const Text('Continue Shopping'),
          ),
        ],
      ),
    );
  }
}
