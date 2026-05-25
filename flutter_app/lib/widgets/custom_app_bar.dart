import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../providers/cart_provider.dart';
import '../providers/auth_provider.dart';
import '../core/theme/app_theme.dart';
import '../core/constants/app_constants.dart';

class CustomAppBar extends StatefulWidget implements PreferredSizeWidget {
  final String title;
  final bool showSearch;
  final bool showBackButton;
  final bool showActions;
  final TextEditingController? searchController;
  final Function(String)? onSearchChanged;
  final VoidCallback? onCartTap;
  final VoidCallback? onProfileTap;
  final VoidCallback? onBackTap;
  final List<Widget>? actions;

  const CustomAppBar({
    super.key,
    required this.title,
    this.showSearch = false,
    this.showBackButton = false,
    this.showActions = true,
    this.searchController,
    this.onSearchChanged,
    this.onCartTap,
    this.onProfileTap,
    this.onBackTap,
    this.actions,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight + 16);

  @override
  State<CustomAppBar> createState() => _CustomAppBarState();
}

class _CustomAppBarState extends State<CustomAppBar>
    with SingleTickerProviderStateMixin {
  bool _searchExpanded = false;
  late final AnimationController _animController;
  late final Animation<double> _widthAnim;
  late final Animation<double> _fadeAnim;
  final FocusNode _searchFocus = FocusNode();
  late final TextEditingController _internalSearchCtrl;

  static const String _profileMenuValue = 'profile';
  static const String _ordersMenuValue = 'orders';
  static const String _messagesMenuValue = 'messages';
  static const String _settingsMenuValue = 'settings';
  static const String _logoutMenuValue = 'logout';

  @override
  void initState() {
    super.initState();
    _internalSearchCtrl = widget.searchController ?? TextEditingController();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 150),
    );
    _widthAnim = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutCubic,
    );
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeOut);
  }

  @override
  void dispose() {
    _animController.dispose();
    _searchFocus.dispose();
    // Only dispose if we created it internally
    if (widget.searchController == null) {
      _internalSearchCtrl.dispose();
    }
    super.dispose();
  }

  void _openSearch() {
    setState(() => _searchExpanded = true);
    _animController.forward();
    Future.delayed(const Duration(milliseconds: 50), () {
      if (mounted) _searchFocus.requestFocus();
    });
  }

  void _closeSearch() {
    _animController.reverse().then((_) {
      if (mounted) {
        setState(() => _searchExpanded = false);
        _internalSearchCtrl.clear();
        widget.onSearchChanged?.call('');
      }
    });
    _searchFocus.unfocus();
  }

  @override
  Widget build(BuildContext context) {
    final isHomeBar = widget.title == 'Happy Hands';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppConstants.spacingMD),
      decoration: BoxDecoration(
        color: AppTheme.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              height: kToolbarHeight,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  // ── Back button ──────────────────────────────────────────
                  if (widget.showBackButton)
                    IconButton(
                      onPressed:
                          widget.onBackTap ?? () => Navigator.pop(context),
                      icon: const Icon(
                        Icons.arrow_back,
                        color: AppTheme.darkBlue,
                      ),
                      tooltip: 'Back',
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(
                        minWidth: 36,
                        minHeight: 36,
                      ),
                    ),

                  // ── Logo (home) or Title (other screens) ─────────────────
                  if (!_searchExpanded) ...[
                    if (isHomeBar)
                      // Logo image with text fallback
                      Padding(
                        padding: const EdgeInsets.only(right: 4),
                        child: Image.asset(
                          'assets/logos/logoo.png',
                          height: 36,
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stackTrace) => const Text(
                            'Happy Hands',
                            style: TextStyle(
                              color: Color(0xFF2C5AA0),
                              fontWeight: FontWeight.w800,
                              fontSize: 20,
                              letterSpacing: -0.3,
                            ),
                          ),
                        ),
                      )
                    else
                      Expanded(
                        child: Text(
                          widget.title,
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(
                                color: AppTheme.darkBlue,
                                fontWeight: FontWeight.w700,
                              ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],

                  // ── Animated search bar ──────────────────────────────────
                  if (widget.showSearch)
                    Expanded(
                      child: AnimatedBuilder(
                        animation: _widthAnim,
                        builder: (context, child) {
                          if (!_searchExpanded && _widthAnim.value == 0) {
                            return const SizedBox.shrink();
                          }
                          return FadeTransition(
                            opacity: _fadeAnim,
                            child: Container(
                              height: 38,
                              margin: const EdgeInsets.symmetric(horizontal: 8),
                              decoration: BoxDecoration(
                                color: AppTheme.lightGray,
                                borderRadius: BorderRadius.circular(
                                  AppConstants.radiusFull,
                                ),
                              ),
                              child: TextField(
                                controller: _internalSearchCtrl,
                                focusNode: _searchFocus,
                                onChanged: widget.onSearchChanged,
                                style: const TextStyle(
                                  fontSize: 14,
                                  color: AppTheme.darkBlue,
                                ),
                                decoration: InputDecoration(
                                  hintText: 'Search products...',
                                  hintStyle: const TextStyle(
                                    fontSize: 13,
                                    color: AppTheme.mediumGray,
                                  ),
                                  prefixIcon: const Icon(
                                    FontAwesomeIcons.magnifyingGlass,
                                    size: 14,
                                    color: AppTheme.mediumGray,
                                  ),
                                  suffixIcon: IconButton(
                                    icon: const Icon(
                                      Icons.close,
                                      size: 16,
                                      color: AppTheme.mediumGray,
                                    ),
                                    onPressed: _closeSearch,
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(
                                      minWidth: 32,
                                      minHeight: 32,
                                    ),
                                  ),
                                  border: InputBorder.none,
                                  contentPadding: const EdgeInsets.symmetric(
                                    vertical: 10,
                                  ),
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                    ),

                  // ── Right-side action icons ───────────────────────────────
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Search icon (only when bar is collapsed)
                      if (widget.showSearch && !_searchExpanded)
                        IconButton(
                          onPressed: _openSearch,
                          icon: const Icon(
                            FontAwesomeIcons.magnifyingGlass,
                            size: 18,
                            color: AppTheme.mediumGray,
                          ),
                          tooltip: 'Search',
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(
                            minWidth: 36,
                            minHeight: 36,
                          ),
                        ),

                      // Notification bell — only when logged in
                      if (widget.showActions)
                        Consumer<AuthProvider>(
                          builder: (context, authProvider, _) {
                            if (authProvider.user == null) {
                              return const SizedBox.shrink();
                            }
                            return IconButton(
                              onPressed: () {},
                              icon: const Icon(
                                FontAwesomeIcons.bell,
                                size: 18,
                                color: AppTheme.mediumGray,
                              ),
                              tooltip: 'Notifications',
                              padding: EdgeInsets.zero,
                              constraints: const BoxConstraints(
                                minWidth: 36,
                                minHeight: 36,
                              ),
                            );
                          },
                        ),

                      // Cart button
                      if (widget.showActions)
                        Consumer<CartProvider>(
                          builder: (context, cartProvider, _) {
                            return IconButton(
                              onPressed: widget.onCartTap,
                              icon: Stack(
                                clipBehavior: Clip.none,
                                children: [
                                  const Icon(
                                    FontAwesomeIcons.cartShopping,
                                    size: 18,
                                    color: AppTheme.mediumGray,
                                  ),
                                  if (cartProvider.itemCount > 0)
                                    Positioned(
                                      top: -4,
                                      right: -6,
                                      child: Container(
                                        constraints: const BoxConstraints(
                                          minWidth: 16,
                                        ),
                                        height: 16,
                                        decoration: const BoxDecoration(
                                          color: Color(0xFFFF6B6B), // web: #ff6b6b
                                          shape: BoxShape.circle,
                                        ),
                                        child: Center(
                                          child: Text(
                                            cartProvider.itemCount > 99
                                                ? '99+'
                                                : '${cartProvider.itemCount}',
                                            style: const TextStyle(
                                              color: AppTheme.white,
                                              fontSize: 9,
                                              fontWeight: FontWeight.w700,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                              padding: EdgeInsets.zero,
                              constraints: const BoxConstraints(
                                minWidth: 36,
                                minHeight: 36,
                              ),
                            );
                          },
                        ),

                      // Profile / avatar button
                      if (widget.showActions)
                        Consumer<AuthProvider>(
                          builder: (context, authProvider, _) {
                            final isSignedIn = authProvider.user != null;

                            final avatar = Container(
                              width: 30,
                              height: 30,
                              decoration: BoxDecoration(
                                color: AppTheme.lightGray,
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: AppTheme.borderGray,
                                  width: 1,
                                ),
                              ),
                              child: authProvider.user?.photoURL != null
                                  ? ClipRRect(
                                      borderRadius: BorderRadius.circular(15),
                                      child: Image.network(
                                        authProvider.user!.photoURL!,
                                        fit: BoxFit.cover,
                                        errorBuilder:
                                            (context, error, stackTrace) =>
                                                _avatarIcon(),
                                      ),
                                    )
                                  : _avatarIcon(),
                            );

                            if (!isSignedIn) {
                              return GestureDetector(
                                onTap: widget.onProfileTap,
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 4,
                                  ),
                                  child: avatar,
                                ),
                              );
                            }

                            return PopupMenuButton<String>(
                              tooltip: 'Account',
                              onSelected: (value) async {
                                if (value == _profileMenuValue) {
                                  Navigator.pushNamed(
                                    context,
                                    '/profile',
                                    arguments: 0,
                                  );
                                } else if (value == _ordersMenuValue) {
                                  Navigator.pushNamed(context, '/orders');
                                } else if (value == _messagesMenuValue) {
                                  Navigator.pushNamed(
                                    context,
                                    '/profile',
                                    arguments: 2,
                                  );
                                } else if (value == _settingsMenuValue) {
                                  Navigator.pushNamed(
                                    context,
                                    '/profile',
                                    arguments: 3,
                                  );
                                } else if (value == _logoutMenuValue) {
                                  await authProvider.logout();
                                  if (!context.mounted) return;
                                  Navigator.pushNamedAndRemoveUntil(
                                    context,
                                    '/home',
                                    (route) => false,
                                  );
                                }
                              },
                              itemBuilder: (context) => [
                                PopupMenuItem<String>(
                                  value: _profileMenuValue,
                                  child: Row(
                                    children: [
                                      Icon(
                                        Icons.person,
                                        size: 18,
                                        color: AppTheme.darkBlue,
                                      ),
                                      const SizedBox(width: 10),
                                      const Text('Profile'),
                                    ],
                                  ),
                                ),
                                PopupMenuItem<String>(
                                  value: _ordersMenuValue,
                                  child: Row(
                                    children: [
                                      Icon(
                                        FontAwesomeIcons.box,
                                        size: 18,
                                        color: AppTheme.darkBlue,
                                      ),
                                      const SizedBox(width: 10),
                                      const Text('My Orders'),
                                    ],
                                  ),
                                ),
                                PopupMenuItem<String>(
                                  value: _messagesMenuValue,
                                  child: Row(
                                    children: [
                                      Icon(
                                        FontAwesomeIcons.commentDots,
                                        size: 18,
                                        color: AppTheme.darkBlue,
                                      ),
                                      const SizedBox(width: 10),
                                      const Text('Messages'),
                                    ],
                                  ),
                                ),
                                PopupMenuItem<String>(
                                  value: _settingsMenuValue,
                                  child: Row(
                                    children: [
                                      Icon(
                                        Icons.settings,
                                        size: 18,
                                        color: AppTheme.darkBlue,
                                      ),
                                      const SizedBox(width: 10),
                                      const Text('Settings'),
                                    ],
                                  ),
                                ),
                                const PopupMenuDivider(),
                                const PopupMenuItem<String>(
                                  value: _logoutMenuValue,
                                  child: Row(
                                    children: [
                                      Icon(Icons.logout, size: 18),
                                      SizedBox(width: 10),
                                      Text('Logout'),
                                    ],
                                  ),
                                ),
                              ],
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 4,
                                ),
                                child: avatar,
                              ),
                            );
                          },
                        ),

                      // Extra actions
                      if (widget.actions != null) ...widget.actions!,
                    ],
                  ),
                ],
              ),
            ),

            // Bottom divider
            const Divider(height: 1, thickness: 1, color: AppTheme.borderGray),
          ],
        ),
      ),
    );
  }

  Widget _avatarIcon() {
    return const Center(
      child: Icon(Icons.person_outline, color: AppTheme.darkBlue, size: 16),
    );
  }
}
