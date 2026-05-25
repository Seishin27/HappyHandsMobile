class ApiResponse<T> {
  final String status; // "success" | "error"
  final String message;
  final T? data;

  ApiResponse({
    required this.status,
    required this.message,
    required this.data,
  });

  bool get isSuccess => status.toLowerCase() == 'success';

  static ApiResponse<R> fromJson<R>(
    Map<String, dynamic> json,
    R Function(dynamic raw) parser,
  ) {
    return ApiResponse<R>(
      status: (json['status'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      data: parser(json['data']),
    );
  }
}

