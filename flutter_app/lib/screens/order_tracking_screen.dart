import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../services/flask_api_service.dart';

class OrderTrackingScreen extends StatefulWidget {
  final int orderId;
  final String pickupAddress;
  final String deliveryAddress;

  const OrderTrackingScreen({
    super.key,
    required this.orderId,
    required this.pickupAddress,
    required this.deliveryAddress,
  });

  @override
  State<OrderTrackingScreen> createState() => _OrderTrackingScreenState();
}

class _OrderTrackingScreenState extends State<OrderTrackingScreen> {
  // Center of the Philippines as fallback
  static const LatLng _fallback = LatLng(12.8797, 121.7740);

  LatLng? _pickup;
  LatLng? _delivery;
  LatLng? _rider;
  String _status = '';
  bool _loading = true;
  bool _delivered = false;

  Timer? _pollTimer;
  final MapController _mapController = MapController();

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _init() async {
    final results = await Future.wait([
      _geocode(widget.pickupAddress),
      _geocode(widget.deliveryAddress),
    ]);
    if (mounted) {
      setState(() {
        _pickup = results[0] ?? _fallback;
        _delivery = results[1] ?? _fallback;
        _loading = false;
      });
    }
    _startPolling();
  }

  Future<LatLng?> _geocode(String address) async {
    if (address.trim().isEmpty) return null;
    try {
      final uri = Uri.https('nominatim.openstreetmap.org', '/search', {
        'q': address,
        'format': 'json',
        'limit': '1',
      });
      final res = await http.get(uri, headers: {'User-Agent': 'HappyHandsApp/1.0'});
      if (res.statusCode == 200) {
        final list = jsonDecode(res.body) as List<dynamic>;
        if (list.isNotEmpty) {
          final item = list.first as Map<String, dynamic>;
          final lat = double.tryParse(item['lat']?.toString() ?? '');
          final lng = double.tryParse(item['lon']?.toString() ?? '');
          if (lat != null && lng != null) return LatLng(lat, lng);
        }
      }
    } catch (_) {}
    return null;
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 10), (_) => _pollRider());
    _pollRider();
  }

  Future<void> _pollRider() async {
    final api = context.read<FlaskApiService>();
    final data = await api.fetchRiderLocation(widget.orderId);
    if (!mounted || data == null) return;

    final lat = (data['lat'] as num?)?.toDouble();
    final lng = (data['lng'] as num?)?.toDouble();
    final status = data['status']?.toString() ?? '';

    setState(() {
      _status = status;
      if (lat != null && lng != null) _rider = LatLng(lat, lng);
      if (status == 'delivered') {
        _delivered = true;
        _pollTimer?.cancel();
      }
    });

    if (_rider != null) {
      _mapController.move(_rider!, 15.0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Track Order'),
        backgroundColor: const Color(0xFF6B3FA0),
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Stack(
              children: [
                FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(
                    initialCenter: _rider ?? _delivery ?? _pickup ?? _fallback,
                    initialZoom: 14.0,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.example.flutter_app',
                    ),
                    MarkerLayer(markers: _buildMarkers()),
                  ],
                ),
                if (_delivered)
                  Positioned(
                    bottom: 24,
                    left: 24,
                    right: 24,
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
                      decoration: BoxDecoration(
                        color: Colors.green,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.check_circle, color: Colors.white),
                          SizedBox(width: 8),
                          Text('Order Delivered', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                        ],
                      ),
                    ),
                  ),
                if (!_delivered && _status.isNotEmpty)
                  Positioned(
                    top: 12,
                    left: 12,
                    right: 12,
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 4)],
                      ),
                      child: Text(
                        'Status: ${_status.replaceAll('_', ' ').toUpperCase()}',
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
              ],
            ),
    );
  }

  List<Marker> _buildMarkers() {
    final markers = <Marker>[];
    if (_pickup != null) {
      markers.add(Marker(
        point: _pickup!,
        width: 40,
        height: 40,
        child: const Icon(Icons.store, color: Colors.green, size: 36),
      ));
    }
    if (_delivery != null) {
      markers.add(Marker(
        point: _delivery!,
        width: 40,
        height: 40,
        child: const Icon(Icons.home, color: Colors.red, size: 36),
      ));
    }
    if (_rider != null) {
      markers.add(Marker(
        point: _rider!,
        width: 44,
        height: 44,
        child: const Icon(Icons.delivery_dining, color: Colors.blue, size: 40),
      ));
    }
    return markers;
  }
}
