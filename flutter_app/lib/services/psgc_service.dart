import 'dart:convert';
import 'package:http/http.dart' as http;

class PsgcLocation {
  final String code;
  final String name;

  const PsgcLocation({required this.code, required this.name});

  factory PsgcLocation.fromJson(Map<String, dynamic> json) {
    return PsgcLocation(
      code: json['code']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is PsgcLocation && other.code == code);

  @override
  int get hashCode => code.hashCode;
}

class PsgcService {
  static const String _base = 'https://psgc.gitlab.io/api';
  static const String ncrRegionCode = '130000000';
  static const Duration _timeout = Duration(seconds: 15);

  static Future<List<PsgcLocation>> _get(String path) async {
    final res = await http.get(Uri.parse('$_base$path')).timeout(_timeout);
    if (res.statusCode != 200) {
      throw Exception('PSGC API ${res.statusCode}');
    }
    final raw = jsonDecode(res.body);
    if (raw is! List) throw Exception('PSGC API unexpected response');
    final items = raw
        .whereType<Map<String, dynamic>>()
        .map(PsgcLocation.fromJson)
        .where((l) => l.code.isNotEmpty && l.name.isNotEmpty)
        .toList();
    items.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return items;
  }

  static Future<List<PsgcLocation>> fetchRegions() => _get('/regions/');

  static Future<List<PsgcLocation>> fetchProvinces(String regionCode) =>
      _get('/regions/$regionCode/provinces/');

  static Future<List<PsgcLocation>> fetchDistricts(String regionCode) =>
      _get('/regions/$regionCode/districts/');

  static Future<List<PsgcLocation>> fetchCitiesByProvince(String provinceCode) =>
      _get('/provinces/$provinceCode/cities-municipalities/');

  static Future<List<PsgcLocation>> fetchCitiesByDistrict(String districtCode) =>
      _get('/districts/$districtCode/cities-municipalities/');

  static Future<List<PsgcLocation>> fetchBarangays(String cityCode) =>
      _get('/cities-municipalities/$cityCode/barangays/');

  static bool isNcr(String regionCode) => regionCode == ncrRegionCode;
}
