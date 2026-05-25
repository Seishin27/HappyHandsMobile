import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

/// A cross-platform image widget that:
/// - Uses [Image.network] on Flutter Web (CachedNetworkImage doesn't support web)
/// - Uses [CachedNetworkImage] on mobile/desktop for caching benefits
class CrossPlatformNetworkImage extends StatelessWidget {
  final String imageUrl;
  final double? width;
  final double? height;
  final BoxFit? fit;
  final Widget? placeholder;
  final Widget? errorWidget;

  const CrossPlatformNetworkImage({
    super.key,
    required this.imageUrl,
    this.width,
    this.height,
    this.fit,
    this.placeholder,
    this.errorWidget,
  });

  @override
  Widget build(BuildContext context) {
    if (kIsWeb) {
      // On web, CachedNetworkImage is not supported — use Image.network with
      // a builder to show placeholder/error states.
      return Image.network(
        imageUrl,
        width: width,
        height: height,
        fit: fit,
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child;
          return placeholder ??
              SizedBox(
                width: width,
                height: height,
                child: Center(
                  child: CircularProgressIndicator(
                    value: loadingProgress.expectedTotalBytes != null
                        ? loadingProgress.cumulativeBytesLoaded /
                            loadingProgress.expectedTotalBytes!
                        : null,
                    strokeWidth: 2,
                  ),
                ),
              );
        },
        errorBuilder: (context, error, stackTrace) {
          return errorWidget ??
              SizedBox(
                width: width,
                height: height,
                child: Icon(
                  Icons.broken_image,
                  color: Colors.grey.shade400,
                ),
              );
        },
      );
    }

    // Mobile/desktop: use CachedNetworkImage for caching
    return CachedNetworkImage(
      imageUrl: imageUrl,
      width: width,
      height: height,
      fit: fit,
      placeholder: placeholder != null
          ? (context, url) => placeholder!
          : (context, url) => SizedBox(
                width: width,
                height: height,
                child: Center(
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
      errorWidget: errorWidget != null
          ? (context, url, error) => errorWidget!
          : (context, url, error) => SizedBox(
                width: width,
                height: height,
                child: Icon(
                  Icons.broken_image,
                  color: Colors.grey.shade400,
                ),
              ),
    );
  }
}
