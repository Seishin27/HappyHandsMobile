import 'package:flutter/material.dart';
import 'package:carousel_slider/carousel_slider.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';
import '../core/config/app_config.dart';

class HeroCarousel extends StatefulWidget {
  final VoidCallback? onShopNow;

  const HeroCarousel({super.key, this.onShopNow});

  @override
  State<HeroCarousel> createState() => _HeroCarouselState();
}

class _HeroCarouselState extends State<HeroCarousel> {
  int _currentIndex = 0;
  final CarouselSliderController _carouselController =
      CarouselSliderController();

  double _carouselHeight(double screenHeight, bool isMobile) {
    if (isMobile) {
      // On small phones use a smaller carousel — max 40% of screen height
      return (screenHeight * 0.40).clamp(240.0, 380.0).toDouble();
    }
    return (screenHeight * 0.50).clamp(480.0, 620.0).toDouble();
  }

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    final screenHeight = mediaQuery.size.height;
    final screenWidth = mediaQuery.size.width;
    final isMobile = screenWidth < 768;
    final carouselHeight = _carouselHeight(screenHeight, isMobile);

    return SizedBox(
      height: carouselHeight,
      width: double.infinity,
      child: ClipRect(
        child: Stack(
          children: [
            // Carousel
            CarouselSlider.builder(
              carouselController: _carouselController,
              options: CarouselOptions(
                height: carouselHeight,
                viewportFraction: 1.0,
                enlargeCenterPage: false,
                autoPlay: true,
                autoPlayInterval: const Duration(seconds: 5),
                autoPlayAnimationDuration: const Duration(milliseconds: 800),
                autoPlayCurve: Curves.easeInOut,
                pauseAutoPlayOnManualNavigate: true,
                pauseAutoPlayOnTouch: true,
                onPageChanged: (index, reason) {
                  setState(() {
                    _currentIndex = index;
                  });
                },
              ),
              itemCount: AppConstants.heroSlides.length,
              itemBuilder: (context, index, realIndex) {
                final slide = AppConstants.heroSlides[index];
                return _buildHeroSlide(slide, index, isMobile: isMobile);
              },
            ),

            // Navigation Arrows — web: 56×56, border-radius 24, white bg, hidden on mobile
            if (!isMobile) ...[
              Positioned(
                left: 32,
                top: 0,
                bottom: 0,
                child: Center(
                  child: _HeroArrow(
                    icon: Icons.chevron_left,
                    onTap: () => _carouselController.previousPage(),
                  ),
                ),
              ),
              Positioned(
                right: 32,
                top: 0,
                bottom: 0,
                child: Center(
                  child: _HeroArrow(
                    icon: Icons.chevron_right,
                    onTap: () => _carouselController.nextPage(),
                  ),
                ),
              ),
            ],

            // Dot Indicators — web: 14px active #0b2350, 10px inactive rgba(11,35,80,0.15)
            Positioned(
              bottom: isMobile ? 16 : 28,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: AppConstants.heroSlides.asMap().entries.map((entry) {
                  final isActive = _currentIndex == entry.key;
                  return GestureDetector(
                    onTap: () => _carouselController.animateToPage(entry.key),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 250),
                      width: isActive ? 14 : 10,
                      height: isActive ? 14 : 10,
                      margin: const EdgeInsets.symmetric(horizontal: 5),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isActive
                            ? AppTheme.heroDark
                            : const Color(0x260B2350),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeroSlide(
    Map<String, dynamic> slide,
    int index, {
    required bool isMobile,
  }) {
    LinearGradient gradient;
    String imagePath;

    switch (slide['gradient']) {
      case 'gradient1':
        gradient = AppTheme.heroGradient1;
        break;
      case 'gradient2':
        gradient = AppTheme.heroGradient2;
        break;
      case 'gradient3':
        gradient = AppTheme.heroGradient3;
        break;
      default:
        gradient = AppTheme.heroGradient1;
    }

    imagePath = slide['image'] ?? 'photo1.png';
    final imageUrl = '${AppConfig.staticBaseUrl}/images/$imagePath';

    return LayoutBuilder(
      builder: (context, constraints) {
        // Responsive padding
        final horizontalPadding = isMobile ? 16.0 : 80.0;
        final verticalPadding = isMobile ? 10.0 : 40.0;

        return SizedBox.expand(
          child: Container(
            decoration: BoxDecoration(gradient: gradient),
            child: Padding(
              padding: EdgeInsets.symmetric(
                horizontal: horizontalPadding,
                vertical: verticalPadding,
              ),
              child: isMobile
                  ? _buildMobileLayout(slide, imageUrl)
                  : _buildDesktopLayout(slide, imageUrl),
            ),
          ),
        );
      },
    );
  }

  Widget _buildMobileLayout(Map<String, dynamic> slide, String imageUrl) {
    return SingleChildScrollView(
      physics: const NeverScrollableScrollPhysics(),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildCarouselImage(imageUrl, isMobile: true),
          const SizedBox(height: 8),
          _buildTextContent(slide, isMobile: true),
        ],
      ),
    );
  }

  Widget _buildDesktopLayout(Map<String, dynamic> slide, String imageUrl) {
    return Row(
      children: [
        // Left side - Text content
        Expanded(flex: 1, child: _buildTextContent(slide, isMobile: false)),
        const SizedBox(width: 40),
        // Right side - Image
        Expanded(
          flex: 1,
          child: _buildCarouselImage(imageUrl, isMobile: false),
        ),
      ],
    );
  }

  Widget _buildTextContent(
    Map<String, dynamic> slide, {
    required bool isMobile,
  }) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: isMobile
          ? CrossAxisAlignment.center
          : CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          slide['title'] ?? '',
          style: TextStyle(
            // Web: 3.8rem desktop, 2.4rem mobile — color #0b2350, weight 800
            fontSize: isMobile ? 22.0 : 42.0,
            fontWeight: FontWeight.w800,
            color: AppTheme.heroDark,
            letterSpacing: -0.5,
            height: 1.1,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          textAlign: isMobile ? TextAlign.center : TextAlign.left,
        ),
        const SizedBox(height: 12),
        Text(
          slide['subtitle'] ?? '',
          style: TextStyle(
            // Web: 1.25rem, weight 500, color #4a5568
            fontSize: isMobile ? 12.0 : 17.0,
            fontWeight: FontWeight.w500,
            color: const Color(0xFF4A5568),
            height: 1.5,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          textAlign: isMobile ? TextAlign.center : TextAlign.left,
        ),
        SizedBox(height: isMobile ? 10.0 : 32.0),
        // Shop Now button — ElevatedButton for proper ink ripple + a11y
        ElevatedButton(
          onPressed: widget.onShopNow,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.heroDark,
            foregroundColor: Colors.white,
            elevation: 4,
            shadowColor: const Color(0x440B2350),
            padding: EdgeInsets.symmetric(
              horizontal: isMobile ? 20.0 : 42.0,
              vertical: isMobile ? 10.0 : 18.0,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(999),
            ),
            textStyle: TextStyle(
              fontSize: isMobile ? 14.0 : 17.0,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.3,
            ),
          ),
          child: const Text('Shop now'),
        ),
      ],
    );
  }

  Widget _buildCarouselImage(String imageUrl, {required bool isMobile}) {
    final h = isMobile ? 110.0 : 300.0;
    final w = isMobile ? 200.0 : 400.0;

    return ClipRRect(
      borderRadius: BorderRadius.circular(AppConstants.radiusLG),
      child: Container(
        height: isMobile ? 110 : null,
        constraints: isMobile
            ? const BoxConstraints(maxHeight: 130, maxWidth: 200)
            : const BoxConstraints(maxHeight: 360, maxWidth: 450),
        child: CachedNetworkImage(
          imageUrl: imageUrl,
          fit: BoxFit.contain,
          placeholder: (context, url) => Container(
            height: h,
            width: w,
            decoration: BoxDecoration(
              color: AppTheme.white.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(AppConstants.radiusMD),
            ),
            child: const Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primaryBlue),
              ),
            ),
          ),
          errorWidget: (context, url, error) => Container(
            height: h,
            width: w,
            decoration: BoxDecoration(
              color: AppTheme.white.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(AppConstants.radiusMD),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.image_not_supported,
                  size: isMobile ? 40 : 48,
                  color: AppTheme.darkBlue.withValues(alpha: 0.5),
                ),
                const SizedBox(height: 8),
                Text(
                  'Image not available',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppTheme.darkBlue.withValues(alpha: 0.7),
                    fontSize: isMobile ? 12 : 14,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Hero arrow button — matches web: 56×56, border-radius 24, white bg ──────
class _HeroArrow extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _HeroArrow({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.92),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.white),
          boxShadow: const [
            BoxShadow(
              color: Color(0x0F000000),
              blurRadius: 20,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: Icon(icon, color: AppTheme.heroDark, size: 26),
      ),
    );
  }
}
