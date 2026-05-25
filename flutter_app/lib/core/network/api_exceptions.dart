class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final Object? cause;

  ApiException(this.message, {this.statusCode, this.cause});

  @override
  String toString() => 'ApiException(statusCode=$statusCode, message=$message)';
}

