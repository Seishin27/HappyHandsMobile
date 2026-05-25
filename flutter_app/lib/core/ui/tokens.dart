import 'package:flutter/material.dart';

/// Design tokens extracted from the existing web CSS (HappyHands).
///
/// Source examples:
/// - `static/css/styles.css`: --baby-primary, --baby-accent, --baby-accent-2
/// - `static/css/categories.css`: --bg, --card, --muted, --brand, --accent, --radius
class AppTokens {
  // Brand colors
  static const Color brandPrimary = Color(0xFF2C5AA0); // --baby-primary / --brand
  static const Color brandAccent = Color(0xFFFFD6CC); // --baby-accent
  static const Color brandMint = Color(0xFF4FD1C5); // --baby-accent-2 / --accent

  // Surfaces
  static const Color bg = Color(0xFFF6F8FB); // --bg
  static const Color card = Colors.white; // --card
  static const Color soft = Color(0xFFF1F5F9); // --soft

  // Text
  static const Color textMain = Color(0xFF0F172A);
  static const Color textMuted = Color(0xFF6B7280); // --muted

  // Radius
  static const double radius = 12; // --radius

  static BorderRadius borderRadius([double? r]) => BorderRadius.circular(r ?? radius);
}

