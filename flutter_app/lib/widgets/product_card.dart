import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../models/product.dart';
import '../core/theme/app_theme.dart';
import '../core/config/app_config.dart';

class ProductCard extends StatefulWidget {
  final Product product;
  final VoidCallback? onTap;
  final VoidCallback? onAddToCart;
  final bool showAddToCart;
  final double? width;
  final double? height;

  const ProductCard({
    super.key,
    required this.product,
    this.onTap,
    this.onAddToCart,
    this.showAddToCart = true,
    this.width,
    this.height,
  });

  @override
  State<ProductCard> createState() => _ProductCardState();
}

class _ProductCardState extends State<ProductCard> {
  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.white,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: AppTheme.borderGray.withValues(alpha: 0.5),
              width: 1,
            ),
            boxShadow: const [
              BoxShadow(
                color: Color(0x0F000000),
                blurRadius: 8,
                offset: Offset(0, 2),
              ),
            ],
          ),
          // Column fills the full grid cell height (270px from mainAxisExtent)
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Fixed-height image ────────────────────────────────────────
              ClipRRect(
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(12),
                  topRight: Radius.circular(12),
                ),
                child: Stack(
                  children: [
                    SizedBox(
                      height: widget.product.imageUrls.length > 1 ? 150 : 130,
                      width: double.infinity,
                      child: _buildProductImage(),
                    ),
                    // Low-stock badge
                    if (widget.product.stock != null &&
                        widget.product.stock! > 0 &&
                        widget.product.stock! < 5)
                      Positioned(
                        top: 6,
                        left: 6,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 3),
                          decoration: BoxDecoration(
                            color: AppTheme.errorRed,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            'Only ${widget.product.stock} left',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),

              // ── Info section — Expanded so button always sits at bottom ───
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Name — takes available space, pushes price/button down
                      Expanded(
                        child: Text(
                          widget.product.name,
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF333333),
                            fontSize: 12,
                            height: 1.3,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),

                      // Price — always at same vertical position
                      Text(
                        '₱${widget.product.price.toStringAsFixed(2)}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF2C5AA0),
                          fontSize: 13,
                        ),
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),

                      // Stock
                      if (widget.product.stock != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          widget.product.stock! == 0
                              ? 'Out of stock'
                              : 'Stock: ${widget.product.stock}',
                          style: TextStyle(
                            color: widget.product.stock! == 0
                                ? AppTheme.errorRed
                                : const Color(0xFF666666),
                            fontSize: 10,
                            fontWeight: widget.product.stock! == 0
                                ? FontWeight.w600
                                : FontWeight.normal,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],

                      // Add to Cart — always at the bottom
                      if (widget.showAddToCart) ...[
                        const SizedBox(height: 6),
                        SizedBox(
                          width: double.infinity,
                          height: 30,
                          child: ElevatedButton(
                            onPressed: widget.product.stock == 0
                                ? null
                                : widget.onAddToCart,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF2C5AA0),
                              foregroundColor: Colors.white,
                              disabledBackgroundColor: Colors.grey[300],
                              elevation: 0,
                              padding: const EdgeInsets.symmetric(horizontal: 4),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                            child: const Text(
                              'Add to cart',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProductImage() {
    final urls = widget.product.imageUrls.take(4).toList();
    if (urls.isEmpty) return _imagePlaceholder();
    return _buildCollage(urls);
  }

  Widget _buildCollage(List<String> urls) {
    Widget img(String url) {
      final full = url.startsWith('http') ? url : '${AppConfig.uploadsBaseUrl}/$url';
      return CachedNetworkImage(
        imageUrl: full,
        fit: BoxFit.cover,
        width: double.infinity,
        height: double.infinity,
        placeholder: (_, __) => Container(color: AppTheme.lightGray),
        errorWidget: (_, __, ___) => _imagePlaceholder(),
      );
    }

    const sep = 1.0;

    if (urls.length == 1) return img(urls[0]);

    if (urls.length == 2) {
      return Row(children: [
        Expanded(child: img(urls[0])),
        const SizedBox(width: sep),
        Expanded(child: img(urls[1])),
      ]);
    }

    if (urls.length == 3) {
      return Row(children: [
        Expanded(child: img(urls[0])),
        const SizedBox(width: sep),
        Expanded(
          child: Column(children: [
            Expanded(child: img(urls[1])),
            const SizedBox(height: sep),
            Expanded(child: img(urls[2])),
          ]),
        ),
      ]);
    }

    // 4 images — 2×2 grid
    return Column(children: [
      Expanded(
        child: Row(children: [
          Expanded(child: img(urls[0])),
          const SizedBox(width: sep),
          Expanded(child: img(urls[1])),
        ]),
      ),
      const SizedBox(height: sep),
      Expanded(
        child: Row(children: [
          Expanded(child: img(urls[2])),
          const SizedBox(width: sep),
          Expanded(child: img(urls[3])),
        ]),
      ),
    ]);
  }

  Widget _imagePlaceholder() {
    return Container(
      color: AppTheme.lightGray,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(FontAwesomeIcons.image, size: 28, color: AppTheme.mediumGray),
          const SizedBox(height: 6),
          Text(
            'No Image',
            style: TextStyle(fontSize: 10, color: AppTheme.mediumGray),
          ),
        ],
      ),
    );
  }
}
