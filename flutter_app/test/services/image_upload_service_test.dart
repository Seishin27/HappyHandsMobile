import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:flutter_app/services/image_upload_service.dart';
import 'package:flutter_app/core/network/api_exceptions.dart';

// Manual mock for http.Client
class MockHttpClient extends http.BaseClient {
  http.StreamedResponse? _response;
  http.BaseRequest? lastRequest;

  void setResponse(http.StreamedResponse response) {
    _response = response;
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    lastRequest = request;
    if (_response == null) {
      throw Exception('No response set for mock');
    }
    return _response!;
  }
}

void main() {
  group('ImageUploadService', () {
    late MockHttpClient mockHttpClient;
    late ImageUploadService imageUploadService;
    late Directory tempDir;

    setUp(() async {
      mockHttpClient = MockHttpClient();
      imageUploadService = ImageUploadService(
        client: mockHttpClient,
        tokenProvider: () async => 'test-token',
      );

      // Create a temporary directory for test files
      tempDir = await Directory.systemTemp.createTemp('image_upload_test_');
    });

    tearDown(() async {
      // Clean up temporary directory
      if (await tempDir.exists()) {
        await tempDir.delete(recursive: true);
      }
    });

    // Helper function to create a test image file
    Future<File> createTestImage(String filename, int sizeBytes) async {
      final file = File('${tempDir.path}/$filename');
      final bytes = List<int>.filled(sizeBytes, 0);
      await file.writeAsBytes(bytes);
      return file;
    }

    group('uploadProductImages', () {
      test('successfully uploads single image', () async {
        // Arrange
        final testImage = await createTestImage('test.jpg', 1024);
        final responseBody = jsonEncode({
          'success': true,
          'urls': ['https://example.com/uploads/image1.jpg'],
        });

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(responseBody)),
            200,
          ),
        );

        // Act
        final result = await imageUploadService.uploadProductImages([testImage]);

        // Assert
        expect(result, isA<List<String>>());
        expect(result.length, 1);
        expect(result[0], 'https://example.com/uploads/image1.jpg');
        expect(mockHttpClient.lastRequest, isA<http.MultipartRequest>());
        expect(
          mockHttpClient.lastRequest!.headers['Authorization'],
          'Bearer test-token',
        );
      });

      test('successfully uploads multiple images', () async {
        // Arrange
        final testImage1 = await createTestImage('test1.jpg', 1024);
        final testImage2 = await createTestImage('test2.png', 2048);
        final testImage3 = await createTestImage('test3.webp', 512);

        final responseBody = jsonEncode({
          'success': true,
          'urls': [
            'https://example.com/uploads/image1.jpg',
            'https://example.com/uploads/image2.png',
            'https://example.com/uploads/image3.webp',
          ],
        });

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(responseBody)),
            200,
          ),
        );

        // Act
        final result = await imageUploadService.uploadProductImages([
          testImage1,
          testImage2,
          testImage3,
        ]);

        // Assert
        expect(result.length, 3);
        expect(result[0], 'https://example.com/uploads/image1.jpg');
        expect(result[1], 'https://example.com/uploads/image2.png');
        expect(result[2], 'https://example.com/uploads/image3.webp');
      });

      test('returns empty list when no images provided', () async {
        // Act
        final result = await imageUploadService.uploadProductImages([]);

        // Assert
        expect(result, isEmpty);
      });

      test('throws ApiException when image file does not exist', () async {
        // Arrange
        final nonExistentFile = File('${tempDir.path}/nonexistent.jpg');

        // Act & Assert
        expect(
          () => imageUploadService.uploadProductImages([nonExistentFile]),
          throwsA(
            isA<ApiException>().having(
              (e) => e.message,
              'message',
              contains('does not exist'),
            ),
          ),
        );
      });

      test('throws ApiException when image size exceeds limit', () async {
        // Arrange - Create an 11MB file (exceeds 10MB limit)
        final largeImage = await createTestImage(
          'large.jpg',
          11 * 1024 * 1024,
        );

        // Act & Assert
        expect(
          () => imageUploadService.uploadProductImages([largeImage]),
          throwsA(
            isA<ApiException>().having(
              (e) => e.message,
              'message',
              contains('exceeds maximum allowed size'),
            ),
          ),
        );
      });

      test('throws ApiException for invalid file extension', () async {
        // Arrange
        final invalidImage = await createTestImage('test.txt', 1024);

        // Act & Assert
        expect(
          () => imageUploadService.uploadProductImages([invalidImage]),
          throwsA(
            isA<ApiException>().having(
              (e) => e.message,
              'message',
              contains('Invalid image format'),
            ),
          ),
        );
      });

      test('accepts all valid image formats', () async {
        // Arrange
        final jpgImage = await createTestImage('test.jpg', 1024);
        final jpegImage = await createTestImage('test.jpeg', 1024);
        final pngImage = await createTestImage('test.png', 1024);
        final gifImage = await createTestImage('test.gif', 1024);
        final webpImage = await createTestImage('test.webp', 1024);

        final responseBody = jsonEncode({
          'success': true,
          'urls': [
            'url1.jpg',
            'url2.jpeg',
            'url3.png',
            'url4.gif',
            'url5.webp',
          ],
        });

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(responseBody)),
            200,
          ),
        );

        // Act
        final result = await imageUploadService.uploadProductImages([
          jpgImage,
          jpegImage,
          pngImage,
          gifImage,
          webpImage,
        ]);

        // Assert
        expect(result.length, 5);
      });

      test('throws ApiException when server returns error', () async {
        // Arrange
        final testImage = await createTestImage('test.jpg', 1024);
        final responseBody = jsonEncode({
          'success': false,
          'message': 'Upload failed due to server error',
        });

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(responseBody)),
            200,
          ),
        );

        // Act & Assert
        expect(
          () => imageUploadService.uploadProductImages([testImage]),
          throwsA(
            isA<ApiException>().having(
              (e) => e.message,
              'message',
              contains('Upload failed due to server error'),
            ),
          ),
        );
      });

      test('throws ApiException on HTTP error status', () async {
        // Arrange
        final testImage = await createTestImage('test.jpg', 1024);
        final responseBody = jsonEncode({
          'message': 'Unauthorized',
        });

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(responseBody)),
            401,
          ),
        );

        // Act & Assert
        expect(
          () => imageUploadService.uploadProductImages([testImage]),
          throwsA(
            isA<ApiException>().having(
              (e) => e.message,
              'message',
              contains('Unauthorized'),
            ),
          ),
        );
      });

      test('throws ApiException on invalid JSON response', () async {
        // Arrange
        final testImage = await createTestImage('test.jpg', 1024);
        const invalidJson = 'This is not JSON';

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(invalidJson)),
            200,
          ),
        );

        // Act & Assert
        expect(
          () => imageUploadService.uploadProductImages([testImage]),
          throwsA(isA<ApiException>()),
        );
      });

      test('validates all images before uploading any', () async {
        // Arrange
        final validImage = await createTestImage('valid.jpg', 1024);
        final invalidImage = await createTestImage('invalid.txt', 1024);

        // Act & Assert
        // Should fail validation before making any network request
        expect(
          () => imageUploadService.uploadProductImages([
            validImage,
            invalidImage,
          ]),
          throwsA(isA<ApiException>()),
        );

        // Verify no request was made
        expect(mockHttpClient.lastRequest, isNull);
      });

      test('includes authorization header in request', () async {
        // Arrange
        final testImage = await createTestImage('test.jpg', 1024);
        final responseBody = jsonEncode({
          'success': true,
          'urls': ['https://example.com/uploads/image1.jpg'],
        });

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(responseBody)),
            200,
          ),
        );

        // Act
        await imageUploadService.uploadProductImages([testImage]);

        // Assert
        expect(mockHttpClient.lastRequest, isNotNull);
        expect(
          mockHttpClient.lastRequest!.headers['Authorization'],
          'Bearer test-token',
        );
      });

      test('handles missing urls in successful response', () async {
        // Arrange
        final testImage = await createTestImage('test.jpg', 1024);
        final responseBody = jsonEncode({
          'success': true,
          // Missing 'urls' field
        });

        mockHttpClient.setResponse(
          http.StreamedResponse(
            Stream.value(utf8.encode(responseBody)),
            200,
          ),
        );

        // Act
        final result = await imageUploadService.uploadProductImages([testImage]);

        // Assert
        expect(result, isEmpty);
      });
    });
  });
}
