import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Extracted colors from web app
  static const Color primaryBlue = Color(0xFF2563EB);   // auth pages (#2563eb)
  static const Color navBlue = Color(0xFF2C5AA0);        // navbar, product prices, main site (#2c5aa0)
  static const Color heroDark = Color(0xFF0B2350);       // hero h1, shop-now button (#0b2350)
  static const Color darkBlue = Color(0xFF1E293B);
  static const Color lightGray = Color(0xFFF1F5F9);
  static const Color mediumGray = Color(0xFF64748B);
  static const Color borderGray = Color(0xFFE2E8F0);
  static const Color white = Color(0xFFFFFFFF);
  static const Color black = Color(0xFF181A1B);
  static const Color errorRed = Color(0xFFEF4444);
  static const Color successGreen = Color(0xFF10B981);
  static const Color cartBadgeRed = Color(0xFFFF6B6B);
  static const List<String> _fontFallbacks = [
    'Segoe UI Emoji',
    'Noto Color Emoji',
    'Apple Color Emoji',
  ];

  static TextStyle _interTextStyle({
    double? fontSize,
    FontWeight? fontWeight,
    Color? color,
    double? letterSpacing,
  }) {
    return GoogleFonts.inter(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      letterSpacing: letterSpacing,
    ).copyWith(fontFamilyFallback: _fontFallbacks);
  }

  // Hero gradient colors from web
  static const LinearGradient heroGradient1 = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFFF7F0), Color(0xFFFFF0FB)],
  );

  static const LinearGradient heroGradient2 = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFF0FBFF), Color(0xFFF7FFF2)],
  );

  static const LinearGradient heroGradient3 = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFFF8E6), Color(0xFFEAF7FF)],
  );

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      fontFamily: GoogleFonts.inter().fontFamily,
      primaryColor: primaryBlue,
      scaffoldBackgroundColor: white,

      // Text theme matching web typography
      textTheme: GoogleFonts.interTextTheme().copyWith(
        displayLarge: _interTextStyle(
          fontSize: 48,
          fontWeight: FontWeight.w800,
          color: darkBlue,
          letterSpacing: 1.0,
        ),
        displayMedium: _interTextStyle(
          fontSize: 36,
          fontWeight: FontWeight.w700,
          color: darkBlue,
        ),
        headlineLarge: _interTextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w700,
          color: darkBlue,
        ),
        headlineMedium: _interTextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w600,
          color: darkBlue,
        ),
        titleLarge: _interTextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: black,
        ),
        titleMedium: _interTextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: black,
        ),
        bodyLarge: _interTextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          color: black,
        ),
        bodyMedium: _interTextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: mediumGray,
        ),
        labelLarge: _interTextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: white,
        ),
      ),

      // App bar theme
      appBarTheme: AppBarTheme(
        backgroundColor: lightGray,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: _interTextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: darkBlue,
        ),
        iconTheme: const IconThemeData(color: darkBlue, size: 24),
      ),

      // Default ElevatedButton: solid primary blue with white text. The
      // previous transparent-on-white made every primary action invisible
      // outside of hero sections. Pages that sit on a colored hero can
      // still override locally with .styleFrom(backgroundColor:Colors.transparent).
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryBlue,
          foregroundColor: white,
          disabledBackgroundColor: primaryBlue.withValues(alpha: 0.4),
          disabledForegroundColor: white.withValues(alpha: 0.7),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          textStyle: _interTextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.4,
          ),
        ),
      ),

      // Default OutlinedButton: primary-blue text + primary-blue border on a
      // transparent background — the standard "secondary" Material treatment.
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primaryBlue,
          side: const BorderSide(color: primaryBlue, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          textStyle: _interTextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.4,
          ),
        ),
      ),

      // TextButton (used as inline links) — keep it on-brand.
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryBlue,
          textStyle: _interTextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      // FAB defaults — visible against the white scaffold.
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: primaryBlue,
        foregroundColor: white,
      ),

      // Card theme matching product cards (web uses 15px radius)
      cardTheme: CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(15),
          side: BorderSide(color: borderGray.withValues(alpha: 0.3)),
        ),
        color: white,
      ),

      // Input decoration theme
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: lightGray,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: borderGray, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: borderGray, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primaryBlue, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: errorRed, width: 1),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        labelStyle: _interTextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: darkBlue,
        ),
        hintStyle: _interTextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: mediumGray,
        ),
      ),

      // Icon theme
      iconTheme: const IconThemeData(color: mediumGray, size: 20),
    );
  }
}
