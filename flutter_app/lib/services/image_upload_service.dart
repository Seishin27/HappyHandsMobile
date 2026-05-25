import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import '../core/network/api_exceptions.dart';

typedef TokenProvider = Future<String?> Function();

/// Service for uploading product images using multipart requests.
///
/// Handles image compression, validation, and multipart file uploads
/// to the Flask backend.
class ImageUploadService {
  final http.Client _client;
  final TokenProvider _tokenProvider;

  // Image validation constraints
  static const int maxImageSizeBytes = 10 * 1024 * 1024; // 10MB
  static const List<String> allowedExtensions = [
    'jpg',
    'jpeg',
    'png',
    'gif',
    'webp'
  ];

  ImageUploadService({
    http.Client? client,
    required TokenProvider tokenProvider,
  })  : _client = client ?? http.Client(),
        _tokenProvider = tokenProvider;

  /// Uploads multiple product images to the server.
  ///
  /// Validates each image before upload and returns a list of uploaded image URLs.
  ///
  /// Parameters:
  /// - [images]: List of image files to upload
  ///
  /// Returns:
  /// - List of uploaded image URLs from the server
  ///
  /// Throws:
  /// - [ApiException] if validation fails or upload fails
  Future<List<String>> uploadProductImages(List<File> images) async {
    if (images.isEmpty) {
      return [];
    }

    // Validate all images before uploading
    for (final image in images) {
      _validateImage(image);
    }

    // Create multipart request
    final uri = _buildUri('/seller/products/upload-images');
    final request = http.MultipartRequest('POST', uri);

    // Add authorization header
    final token = await _tokenProvider();
    if (token != null && token.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $token';
    }

    // Add images to the request
    for (int i = 0; i < images.length; i++) {
      final image = images[i];
      final filename = _getFilename(image);
      final mimeType = _getMimeType(filename);

      final multipartFile = await http.MultipartFile.fromPath(
        'images', // Field name expected by backend
        image.path,
        filename: filename,
        contentType: mimeType,
      );

      request.files.add(multipartFile);
    }

    // Send the request
    try {
      final streamedResponse = await _client
          .send(request)
          .timeout(const Duration(seconds: 60));

      final response = await http.Response.fromStream(streamedResponse);

      return _parseUploadResponse(response);
    } catch (e) {
      throw ApiException(
        'Failed to upload images: ${e.toString()}',
        cause: e,
      );
    }
  }

  /// Validates an image file.
  ///
  /// Checks:
  /// - File exists
  /// - File size is within limits
  /// - File extension is allowed
  ///
  /// Throws [ApiException] if validation fails.
  void _validateImage(File image) {
    // Check if file exists
    if (!image.existsSync()) {
      throw ApiException('Image file does not exist: ${image.path}');
    }

    // Check file size
    final fileSize = image.lengthSync();
    if (fileSize > maxImageSizeBytes) {
      final sizeMB = (fileSize / (1024 * 1024)).toStringAsFixed(2);
      final maxMB = (maxImageSizeBytes / (1024 * 1024)).toStringAsFixed(0);
      throw ApiException(
        'Image size ($sizeMB MB) exceeds maximum allowed size ($maxMB MB)',
      );
    }

    // Check file extension
    final filename = _getFilename(image);
    final extension = filename.split('.').last.toLowerCase();
    if (!allowedExtensions.contains(extension)) {
      throw ApiException(
        'Invalid image format. Allowed formats: ${allowedExtensions.join(", ")}',
      );
    }
  }

  /// Extracts filename from file path.
  String _getFilename(File file) {
    return file.path.split('/').last.split('\\').last;
  }

  /// Determines MIME type based on file extension.
  http.MediaType _getMimeType(String filename) {
    final extension = filename.split('.').last.toLowerCase();
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return http.MediaType('image', 'jpeg');
      case 'png':
        return http.MediaType('image', 'png');
      case 'gif':
        return http.MediaType('image', 'gif');
      case 'webp':
        return http.MediaType('image', 'webp');
      default:
        return http.MediaType('image', 'jpeg');
    }
  }

  /// Builds the full URI for the API endpoint.
  Uri _buildUri(String path) {
    final base = AppConfig.apiBaseUrl.replaceAll(RegExp(r'/$ '), '');
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    return Uri.parse('$base/$cleanPath');
  }

  /// Parses the upload response and extracts image URLs.
  ///
  /// Expected response format:
  /// ```json
  /// {
  ///   "success": true,
  ///   "urls": ["url1", "url2", ...]
  /// }
  /// ```
  ///
  /// Throws [ApiException] if the response indicates failure.
  List<String> _parseUploadResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      try {
        final json = _decodeJson(response.body);

        // Check for success flag
        final success = json['success'] as bool? ?? false;
        if (!success) {
          final message = json['message'] ?? json['msg'] ?? 'Upload failed';
          throw ApiException(
            message.toString(),
            statusCode: response.statusCode,
          );
        }

        // Extract URLs from response
        final urls = json['urls'] as List<dynamic>? ?? [];
        return urls.map((url) => url.toString()).toList();
      } catch (e) {
        if (e is ApiException) rethrow;
        throw ApiException(
          'Failed to parse upload response',
          statusCode: response.statusCode,
          cause: e,
        );
      }
    } else {
      // Handle error response
      String message = 'Upload failed';
      try {
        final json = _decodeJson(response.body);
        message = json['message'] ?? json['msg'] ?? json['error'] ?? message;
      } catch (_) {
        // If JSON parsing fails, use default message
      }

      throw ApiException(
        message.toString(),
        statusCode: response.statusCode,
      );
    }
  }

  /// Decodes JSON response body.
  Map<String, dynamic> _decodeJson(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      throw ApiException('Invalid JSON response format');
    } catch (e) {
      throw ApiException('Failed to decode JSON response', cause: e);
    }
  }
}
