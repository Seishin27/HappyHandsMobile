import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';
import '../widgets/role_card.dart';
import '../widgets/custom_app_bar.dart';
import 'auth/seller_auth_screen.dart';
import 'auth/rider_auth_screen.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth < 768;
    final horizontalPadding = isMobile ? 16.0 : 24.0;

    return Scaffold(
      backgroundColor: AppTheme.lightGray,
      appBar: const CustomAppBar(
        title: 'Join Us',
        showBackButton: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: horizontalPadding,
              vertical: 24,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header Section
                Text(
                  'Become a Partner',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        color: AppTheme.darkBlue,
                        fontWeight: FontWeight.w800,
                        fontSize: isMobile ? 24 : 28,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Choose how you want to join our platform and start earning today.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: AppTheme.mediumGray,
                        height: 1.5,
                        fontSize: isMobile ? 14 : 16,
                      ),
                ),
                const SizedBox(height: 32),

                // Role Cards
                if (isMobile) ...[
                  // Mobile: Stack vertically
                  RoleCard(
                    title: 'Become a Seller',
                    description:
                        'List your products and reach thousands of customers. Start your online business today.',
                    icon: FontAwesomeIcons.store,
                    iconBackgroundColor: const Color(0xFFE8F4FD),
                    buttonText: 'Start Selling',
                    onTap: () => _navigateToSellerAuth(context),
                  ),
                  const SizedBox(height: 16),
                  RoleCard(
                    title: 'Become a Rider',
                    description:
                        'Deliver orders and earn flexible income. Join our delivery fleet and be your own boss.',
                    icon: FontAwesomeIcons.motorcycle,
                    iconBackgroundColor: const Color(0xFFFFF4E8),
                    buttonText: 'Start Delivering',
                    onTap: () => _navigateToRiderAuth(context),
                  ),
                ] else ...[
                  // Tablet/Desktop: Side by side
                  Row(
                    children: [
                      Expanded(
                        child: RoleCard(
                          title: 'Become a Seller',
                          description:
                              'List your products and reach thousands of customers. Start your online business today.',
                          icon: FontAwesomeIcons.store,
                          iconBackgroundColor: const Color(0xFFE8F4FD),
                          buttonText: 'Start Selling',
                          onTap: () => _navigateToSellerAuth(context),
                        ),
                      ),
                      const SizedBox(width: 24),
                      Expanded(
                        child: RoleCard(
                          title: 'Become a Rider',
                          description:
                              'Deliver orders and earn flexible income. Join our delivery fleet and be your own boss.',
                          icon: FontAwesomeIcons.motorcycle,
                          iconBackgroundColor: const Color(0xFFFFF4E8),
                          buttonText: 'Start Delivering',
                          onTap: () => _navigateToRiderAuth(context),
                        ),
                      ),
                    ],
                  ),
                ],

                const SizedBox(height: 32),

                // Info Section
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppTheme.white,
                    borderRadius:
                        BorderRadius.circular(AppConstants.radiusLG),
                    border: Border.all(
                      color: AppTheme.borderGray,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          color: const Color(0xFFE6F7ED),
                          borderRadius:
                              BorderRadius.circular(AppConstants.radiusMD),
                        ),
                        child: const Icon(
                          Icons.help_outline,
                          color: AppTheme.successGreen,
                          size: 24,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Need Help?',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(
                                    color: AppTheme.darkBlue,
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Contact our support team for assistance with registration.',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: AppTheme.mediumGray,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _navigateToSellerAuth(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const SellerAuthScreen(),
      ),
    );
  }

  void _navigateToRiderAuth(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const RiderAuthScreen(),
      ),
    );
  }
}
