import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';
import '../widgets/custom_app_bar.dart';

/// Mirrors the Flask about.html page.
class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: CustomAppBar(title: 'About Us', showBackButton: true),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Hero banner
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: AppConstants.spacingXL,
                vertical: 60,
              ),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xFF0B2350), Color(0xFF2C5AA0)],
                ),
              ),
              child: Column(
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: const Center(
                      child: Text('👶', style: TextStyle(fontSize: 36)),
                    ),
                  ),
                  const SizedBox(height: 20),
                  const Text(
                    'Happy Hands',
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Your trusted baby essentials store',
                    style: TextStyle(
                      fontSize: 16,
                      color: Colors.white70,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.all(AppConstants.spacingXL),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Mission
                  _SectionCard(
                    icon: FontAwesomeIcons.heart,
                    iconColor: const Color(0xFFEF4444),
                    title: 'Our Mission',
                    body:
                        'We believe every child deserves the best start in life. '
                        'Happy Hands curates safe, high-quality baby essentials '
                        'so parents can focus on what matters most — their little ones.',
                  ),
                  const SizedBox(height: AppConstants.spacingLG),

                  // What we offer
                  _SectionCard(
                    icon: FontAwesomeIcons.star,
                    iconColor: const Color(0xFFF59E0B),
                    title: 'What We Offer',
                    body:
                        'From cozy clothing and comfort toys to nursery furniture '
                        'and safety gear — everything hand-picked for quality, '
                        'safety, and value.',
                  ),
                  const SizedBox(height: AppConstants.spacingLG),

                  // Features grid
                  const Text(
                    'Why Choose Us',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.darkBlue,
                    ),
                  ),
                  const SizedBox(height: AppConstants.spacingMD),
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 2,
                    childAspectRatio: 1.3,
                    crossAxisSpacing: AppConstants.spacingMD,
                    mainAxisSpacing: AppConstants.spacingMD,
                    children: const [
                      _FeatureTile(
                        emoji: '📞',
                        title: 'Customer Help',
                        subtitle: 'Always here when you need us',
                      ),
                      _FeatureTile(
                        emoji: '🚚',
                        title: 'Flat Rate Shipping',
                        subtitle: 'Only ₱30.00',
                      ),
                      _FeatureTile(
                        emoji: '↩️',
                        title: 'Easy Returns',
                        subtitle: 'Within 7 days',
                      ),
                      _FeatureTile(
                        emoji: '💳',
                        title: 'Secure Payments',
                        subtitle: 'Cash on Delivery',
                      ),
                    ],
                  ),
                  const SizedBox(height: AppConstants.spacingXL),

                  // Contact
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(AppConstants.spacingLG),
                    decoration: BoxDecoration(
                      color: AppTheme.lightGray,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.borderGray),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Get in Touch',
                          style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.darkBlue,
                          ),
                        ),
                        const SizedBox(height: AppConstants.spacingMD),
                        _ContactRow(
                          icon: FontAwesomeIcons.envelope,
                          text: 'happyhands929@gmail.com',
                        ),
                        const SizedBox(height: 10),
                        _ContactRow(
                          icon: FontAwesomeIcons.locationDot,
                          text: 'Philippines',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppConstants.spacingXXL),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String body;
  const _SectionCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.body,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppConstants.spacingLG),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.borderGray),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: iconColor, size: 20),
          ),
          const SizedBox(width: AppConstants.spacingMD),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.darkBlue,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  body,
                  style: const TextStyle(
                    fontSize: 13,
                    color: AppTheme.mediumGray,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FeatureTile extends StatelessWidget {
  final String emoji;
  final String title;
  final String subtitle;
  const _FeatureTile({
    required this.emoji,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppConstants.spacingMD),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderGray),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 28)),
          const SizedBox(height: 8),
          Text(
            title,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: AppTheme.darkBlue,
            ),
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 3),
          Text(
            subtitle,
            style: const TextStyle(fontSize: 11, color: AppTheme.mediumGray),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

class _ContactRow extends StatelessWidget {
  final IconData icon;
  final String text;
  const _ContactRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: AppTheme.primaryBlue),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 14, color: AppTheme.darkBlue),
          ),
        ),
      ],
    );
  }
}
