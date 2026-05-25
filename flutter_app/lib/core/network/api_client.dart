import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import 'api_exceptions.dart';

typedef TokenProvider = Future<String?> Function();
typedef RefreshCallback = Future<String?> Function();

class ApiClient {
  final http.Client _client;
  final TokenProvider _tokenProvider;
  final RefreshCallback? _onRefresh;

  ApiClient({
    http.Client? client,
    required TokenProvider tokenProvider,
    RefreshCallback? onRefresh,
  })  : _client = client ?? http.Client(),
        _tokenProvider = tokenProvider,
        _onRefresh = onRefresh;

  Uri _uri(String path, [Map<String, String>? query]) {
    final base = AppConfig.apiBaseUrl.replaceAll(RegExp(r'/$'), '');
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    return Uri.parse('$base/$cleanPath').replace(queryParameters: query);
  }

  Future<Map<String, String>> _headers({bool jsonBody = false}) async {
    final headers = <String, String>{
      'Accept': 'application/json',
    };
    if (jsonBody) {
      headers['Content-Type'] = 'application/json';
    }

    final token = await _tokenProvider();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<Map<String, dynamic>> getJson(String path, {Map<String, String>? query}) async {
    return _withRefresh(() async {
      final res = await _client
          .get(_uri(path, query), headers: await _headers())
          .timeout(AppConfig.requestTimeout);
      return res;
    });
  }

  Future<Map<String, dynamic>> postJson(String path, Map<String, dynamic> body) async {
    return _withRefresh(() async {
      final res = await _client
          .post(
            _uri(path),
            headers: await _headers(jsonBody: true),
            body: jsonEncode(body),
          )
          .timeout(AppConfig.requestTimeout);
      return res;
    });
  }

  Future<Map<String, dynamic>> putJson(String path, Map<String, dynamic> body) async {
    return _withRefresh(() async {
      final res = await _client
          .put(
            _uri(path),
            headers: await _headers(jsonBody: true),
            body: jsonEncode(body),
          )
          .timeout(AppConfig.requestTimeout);
      return res;
    });
  }

  Future<Map<String, dynamic>> deleteJson(String path) async {
    return _withRefresh(() async {
      final res = await _client
          .delete(_uri(path), headers: await _headers())
          .timeout(AppConfig.requestTimeout);
      return res;
    });
  }

  /// Executes [request], and if the server returns 401 + a refresh callback
  /// is wired, refreshes the access token and retries once.
  Future<Map<String, dynamic>> _withRefresh(Future<http.Response> Function() request) async {
    final res = await request();
    if (res.statusCode == 401 && _onRefresh != null) {
      final newToken = await _onRefresh!();
      if (newToken != null && newToken.isNotEmpty) {
        final retried = await request();
        return _decode(retried);
      }
    }
    return _decode(res);
  }

  Map<String, dynamic> _decode(http.Response res) {
    Map<String, dynamic> json;
    try {
      json = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (e) {
      throw ApiException('Invalid server response (HTTP ${res.statusCode})', statusCode: res.statusCode, cause: e);
    }

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return json;
    }

    final msg = (json['message'] ?? json['msg'] ?? 'Request failed').toString();
    final data = json['data'];
    final detail = data is Map ? data['error']?.toString() : null;
    final fullMsg = (detail != null && detail.isNotEmpty) ? '$msg ($detail)' : msg;
    throw ApiException(fullMsg, statusCode: res.statusCode, cause: json);
  }
}

