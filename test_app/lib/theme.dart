import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

abstract final class AppColors {
  static const navy = Color(0xFF0B1F3A);
  static const navyLight = Color(0xFF1A3358);
  static const blue = Color(0xFF1E63E9);
  static const blueLight = Color(0xFF3B7AF0);
  static const gold = Color(0xFFC8972B);
  static const goldLight = Color(0xFFE5B84A);
  static const bgPage = Color(0xFFF7F9FC);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceAlt = Color(0xFFF0F4FA);
  static const textPrimary = Color(0xFF0D1B2A);
  static const textSecondary = Color(0xFF4A5568);
  static const textMuted = Color(0xFF8A9BB0);
  static const border = Color(0xFFE2E8F0);
  static const borderStrong = Color(0xFFCBD5E1);
  static const success = Color(0xFF10B981);
  static const warning = Color(0xFFF59E0B);
  static const error = Color(0xFFEF4444);
}

abstract final class AppGradients {
  static const navyHero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0B1F3A), Color(0xFF1A3358), Color(0xFF0B1F3A)],
    stops: [0.0, 0.5, 1.0],
  );
  static const blueAccent = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1E63E9), Color(0xFF3B7AF0)],
  );
  static const goldAccent = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFC8972B), Color(0xFFE5B84A)],
  );
  static const pageBg = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFF7F9FC), Color(0xFFEEF3FB)],
  );
}

abstract final class AppShadows {
  static const card = [
    BoxShadow(color: Color(0x0A000000), blurRadius: 8, offset: Offset(0, 2)),
    BoxShadow(color: Color(0x06000000), blurRadius: 24, offset: Offset(0, 8)),
  ];
  static const cardHover = [
    BoxShadow(color: Color(0x14000000), blurRadius: 16, offset: Offset(0, 4)),
    BoxShadow(color: Color(0x0A000000), blurRadius: 40, offset: Offset(0, 12)),
  ];
  static const button = [
    BoxShadow(color: Color(0x3A1E63E9), blurRadius: 16, offset: Offset(0, 6)),
  ];
  static const navBar = [
    BoxShadow(color: Color(0x1A000000), blurRadius: 20, offset: Offset(0, 4)),
  ];
}

abstract final class AppRadius {
  static const sm = BorderRadius.all(Radius.circular(8));
  static const md = BorderRadius.all(Radius.circular(12));
  static const lg = BorderRadius.all(Radius.circular(16));
  static const xl = BorderRadius.all(Radius.circular(24));
  static const full = BorderRadius.all(Radius.circular(999));
}

ThemeData buildAppTheme() {
  final base = GoogleFonts.interTextTheme();
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.blue,
      brightness: Brightness.light,
    ).copyWith(
      primary: AppColors.blue,
      secondary: AppColors.gold,
      surface: AppColors.surface,
    ),
    scaffoldBackgroundColor: AppColors.bgPage,
    textTheme: base.copyWith(
      displayLarge: GoogleFonts.poppins(
          fontSize: 57, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
      displayMedium: GoogleFonts.poppins(
          fontSize: 45, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
      displaySmall: GoogleFonts.poppins(
          fontSize: 36, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
      headlineLarge: GoogleFonts.poppins(
          fontSize: 32, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
      headlineMedium: GoogleFonts.poppins(
          fontSize: 26, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
      headlineSmall: GoogleFonts.poppins(
          fontSize: 22, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
      titleLarge: GoogleFonts.poppins(
          fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
      titleMedium: GoogleFonts.inter(
          fontSize: 16, fontWeight: FontWeight.w500, color: AppColors.textPrimary),
      titleSmall: GoogleFonts.inter(
          fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.textPrimary),
      bodyLarge: GoogleFonts.inter(fontSize: 16, color: AppColors.textSecondary),
      bodyMedium: GoogleFonts.inter(fontSize: 14, color: AppColors.textSecondary),
      bodySmall: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
      labelLarge: GoogleFonts.inter(
          fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 0.3),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.blue,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: const RoundedRectangleBorder(borderRadius: AppRadius.md),
        textStyle: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.blue,
        side: const BorderSide(color: AppColors.blue, width: 1.5),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: const RoundedRectangleBorder(borderRadius: AppRadius.md),
        textStyle: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceAlt,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.blue, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.error),
      ),
      hintStyle: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 14),
      labelStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 14),
    ),
    cardTheme: CardThemeData(
      color: AppColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      backgroundColor: AppColors.navy,
      contentTextStyle: GoogleFonts.inter(color: Colors.white, fontSize: 14),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      titleTextStyle: GoogleFonts.poppins(
          fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
    ),
  );
}

// Reusable UI building blocks

class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final double? width;
  final IconData? icon;

  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.loading = false,
    this.width,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: 50,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: AppRadius.md,
          boxShadow: onPressed != null ? AppShadows.button : [],
        ),
        child: ElevatedButton(
          onPressed: loading ? null : onPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.blue,
            foregroundColor: Colors.white,
            disabledBackgroundColor: AppColors.blue.withOpacity(0.6),
            shape: const RoundedRectangleBorder(borderRadius: AppRadius.md),
          ),
          child: loading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white),
                )
              : Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (icon != null) ...[Icon(icon, size: 18), const SizedBox(width: 8)],
                    Text(label,
                        style: GoogleFonts.inter(
                            fontSize: 15, fontWeight: FontWeight.w600)),
                  ],
                ),
        ),
      ),
    );
  }
}

class GhostButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final Color? color;

  const GhostButton({super.key, required this.label, this.onPressed, this.color});

  @override
  Widget build(BuildContext context) {
    final c = color ?? AppColors.blue;
    return SizedBox(
      height: 50,
      child: OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: c,
          side: BorderSide(color: c, width: 1.5),
          shape: const RoundedRectangleBorder(borderRadius: AppRadius.md),
          padding: const EdgeInsets.symmetric(horizontal: 24),
        ),
        child: Text(label,
            style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600)),
      ),
    );
  }
}

class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? color;
  final List<BoxShadow>? shadows;
  final BorderRadius? radius;
  final Border? border;

  const AppCard({
    super.key,
    required this.child,
    this.padding,
    this.color,
    this.shadows,
    this.radius,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: color ?? AppColors.surface,
        borderRadius: radius ?? const BorderRadius.all(Radius.circular(16)),
        border: border ?? Border.all(color: AppColors.border),
        boxShadow: shadows ?? AppShadows.card,
      ),
      child: child,
    );
  }
}

class StatusBadge extends StatelessWidget {
  final String label;
  final Color color;
  final Color? bg;

  const StatusBadge({super.key, required this.label, required this.color, this.bg});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg ?? color.withOpacity(0.12),
        borderRadius: AppRadius.full,
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
            fontSize: 12, fontWeight: FontWeight.w600, color: color),
      ),
    );
  }
}
