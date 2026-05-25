import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';

class RoleCard extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;
  final Color iconBackgroundColor;
  final VoidCallback onTap;
  final String buttonText;

  const RoleCard({
    super.key,
    required this.title,
    required this.description,
    required this.icon,
    required this.iconBackgroundColor,
    required this.onTap,
    this.buttonText = 'Get Started',
  });

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isSmallScreen = screenWidth < 360;

    return Card(
      elevation: 2,
      shadowColor: AppTheme.black.withValues(alpha: 0.08),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppConstants.radiusXL),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppConstants.radiusXL),
        child: Padding(
          padding: EdgeInsets.all(isSmallScreen ? 20 : 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Icon
              Container(
                width: isSmallScreen ? 56 : 64,
                height: isSmallScreen ? 56 : 64,
                decoration: BoxDecoration(
                  color: iconBackgroundColor,
                  borderRadius: BorderRadius.circular(AppConstants.radiusLG),
                ),
                child: Icon(
                  icon,
                  size: isSmallScreen ? 28 : 32,
                  color: AppTheme.primaryBlue,
                ),
              ),
              const SizedBox(height: 20),

              // Title
              Text(
                title,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: AppTheme.darkBlue,
                      fontWeight: FontWeight.w700,
                      fontSize: isSmallScreen ? 18 : 20,
                    ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),

              // Description
              Text(
                description,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppTheme.mediumGray,
                      height: 1.5,
                      fontSize: isSmallScreen ? 13 : 14,
                    ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 20),

              // Button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onTap,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    foregroundColor: AppTheme.white,
                    elevation: 0,
                    padding: EdgeInsets.symmetric(
                      horizontal: isSmallScreen ? 20 : 24,
                      vertical: isSmallScreen ? 12 : 14,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius:
                          BorderRadius.circular(AppConstants.radiusLG),
                    ),
                  ),
                  child: Text(
                    buttonText,
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: AppTheme.white,
                          fontWeight: FontWeight.w600,
                          fontSize: isSmallScreen ? 13 : 14,
                        ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
