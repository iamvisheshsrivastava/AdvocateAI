import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';
import 'landing_page.dart';
import 'role_home_page.dart';
import 'signup_page.dart';
import 'theme.dart';

Future<Map<String, dynamic>?> loginUser(
    String username, String password) async {
  try {
    final res = await http
        .post(
          Uri.parse('${ApiConfig.baseUrl}/login'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': username, 'password': password}),
        )
        .timeout(const Duration(seconds: 20));

    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      if (data['success'] == true) return data as Map<String, dynamic>;
    }
  } catch (_) {}
  return null;
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage>
    with SingleTickerProviderStateMixin {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  late AnimationController _animCtrl;
  late Animation<double> _fade;
  late Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600));
    _fade = CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut);
    _slide = Tween<Offset>(begin: const Offset(0, 0.04), end: Offset.zero)
        .animate(CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut));
    _animCtrl.forward();
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    final username = _usernameCtrl.text.trim();
    final password = _passwordCtrl.text;

    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = 'Please enter your username and password.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final data = await loginUser(username, password);
      if (!mounted) return;

      if (data != null) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', data['access_token'] ?? '');
        await prefs.setInt('user_id', data['user_id'] ?? 0);
        await prefs.setString('user_email', data['email'] ?? '');
        await prefs.setString('user_role', data['role']?.toString() ?? 'client');

        if (!mounted) return;
        Navigator.pushReplacement(
          context,
          PageRouteBuilder(
            pageBuilder: (_, __, ___) =>
                RoleHomePage(role: data['role']?.toString() ?? 'client'),
            transitionsBuilder: (_, anim, __, child) =>
                FadeTransition(opacity: anim, child: child),
            transitionDuration: const Duration(milliseconds: 400),
          ),
        );
      } else {
        setState(() => _error = 'Incorrect username or password.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    final compact = w < 840;

    return Scaffold(
      backgroundColor: AppColors.bgPage,
      body: compact
          ? _MobileLayout(
              fade: _fade,
              slide: _slide,
              usernameCtrl: _usernameCtrl,
              passwordCtrl: _passwordCtrl,
              obscure: _obscure,
              loading: _loading,
              error: _error,
              onObscureToggle: () => setState(() => _obscure = !_obscure),
              onLogin: _handleLogin,
              onBack: () => Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const LandingPage())),
              onSignup: () => Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const SignupPage())),
            )
          : _DesktopLayout(
              fade: _fade,
              slide: _slide,
              usernameCtrl: _usernameCtrl,
              passwordCtrl: _passwordCtrl,
              obscure: _obscure,
              loading: _loading,
              error: _error,
              onObscureToggle: () => setState(() => _obscure = !_obscure),
              onLogin: _handleLogin,
              onBack: () => Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const LandingPage())),
              onSignup: () => Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const SignupPage())),
            ),
    );
  }
}

// ── Desktop split layout ──────────────────────────────────────────────────────

class _DesktopLayout extends StatelessWidget {
  final Animation<double> fade;
  final Animation<Offset> slide;
  final TextEditingController usernameCtrl;
  final TextEditingController passwordCtrl;
  final bool obscure;
  final bool loading;
  final String? error;
  final VoidCallback onObscureToggle;
  final VoidCallback onLogin;
  final VoidCallback onBack;
  final VoidCallback onSignup;

  const _DesktopLayout({
    required this.fade,
    required this.slide,
    required this.usernameCtrl,
    required this.passwordCtrl,
    required this.obscure,
    required this.loading,
    required this.error,
    required this.onObscureToggle,
    required this.onLogin,
    required this.onBack,
    required this.onSignup,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // Brand panel
        Expanded(
          flex: 5,
          child: Container(
            decoration: const BoxDecoration(gradient: AppGradients.navyHero),
            padding: const EdgeInsets.all(56),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _BackButton(onBack: onBack, dark: false),
                const Spacer(),
                Container(
                  width: 48,
                  height: 48,
                  decoration: const BoxDecoration(
                      gradient: AppGradients.blueAccent,
                      borderRadius: AppRadius.sm),
                  child:
                      const Icon(Icons.balance, color: Colors.white, size: 26),
                ),
                const SizedBox(height: 20),
                Text('AdvocateAI',
                    style: GoogleFonts.poppins(
                        fontSize: 32,
                        fontWeight: FontWeight.w800,
                        color: Colors.white)),
                const SizedBox(height: 12),
                Text(
                    'AI-powered legal assistance.\nConnecting clients with the right lawyers.',
                    style: GoogleFonts.inter(
                        fontSize: 15,
                        color: Colors.white.withOpacity(0.7),
                        height: 1.6)),
                const SizedBox(height: 48),
                ...[
                  'Instant AI legal analysis',
                  'Smart lawyer matching',
                  'Secure case workspace',
                  'Document intelligence',
                ].map((f) => Padding(
                      padding: const EdgeInsets.only(bottom: 14),
                      child: Row(children: [
                        Container(
                          width: 20,
                          height: 20,
                          decoration: const BoxDecoration(
                              color: AppColors.gold, shape: BoxShape.circle),
                          child: const Icon(Icons.check,
                              size: 12, color: Colors.white),
                        ),
                        const SizedBox(width: 12),
                        Text(f,
                            style: GoogleFonts.inter(
                                fontSize: 14,
                                color: Colors.white.withOpacity(0.85))),
                      ]),
                    )),
                const Spacer(),
                Text('© 2026 AdvocateAI',
                    style: GoogleFonts.inter(
                        fontSize: 12, color: Colors.white.withOpacity(0.35))),
              ],
            ),
          ),
        ),
        // Form panel
        Expanded(
          flex: 6,
          child: FadeTransition(
            opacity: fade,
            child: SlideTransition(
              position: slide,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: _LoginForm(
                    usernameCtrl: usernameCtrl,
                    passwordCtrl: passwordCtrl,
                    obscure: obscure,
                    loading: loading,
                    error: error,
                    onObscureToggle: onObscureToggle,
                    onLogin: onLogin,
                    onSignup: onSignup,
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ── Mobile layout ─────────────────────────────────────────────────────────────

class _MobileLayout extends StatelessWidget {
  final Animation<double> fade;
  final Animation<Offset> slide;
  final TextEditingController usernameCtrl;
  final TextEditingController passwordCtrl;
  final bool obscure;
  final bool loading;
  final String? error;
  final VoidCallback onObscureToggle;
  final VoidCallback onLogin;
  final VoidCallback onBack;
  final VoidCallback onSignup;

  const _MobileLayout({
    required this.fade,
    required this.slide,
    required this.usernameCtrl,
    required this.passwordCtrl,
    required this.obscure,
    required this.loading,
    required this.error,
    required this.onObscureToggle,
    required this.onLogin,
    required this.onBack,
    required this.onSignup,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: FadeTransition(
        opacity: fade,
        child: SlideTransition(
          position: slide,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _BackButton(onBack: onBack, dark: true),
                const SizedBox(height: 32),
                Center(
                  child: Column(
                    children: [
                      Container(
                        width: 52,
                        height: 52,
                        decoration: const BoxDecoration(
                            gradient: AppGradients.blueAccent,
                            borderRadius: AppRadius.md),
                        child: const Icon(Icons.balance,
                            color: Colors.white, size: 28),
                      ),
                      const SizedBox(height: 12),
                      Text('AdvocateAI',
                          style: GoogleFonts.poppins(
                              fontSize: 24,
                              fontWeight: FontWeight.w800,
                              color: AppColors.navy)),
                    ],
                  ),
                ),
                const SizedBox(height: 36),
                _LoginForm(
                  usernameCtrl: usernameCtrl,
                  passwordCtrl: passwordCtrl,
                  obscure: obscure,
                  loading: loading,
                  error: error,
                  onObscureToggle: onObscureToggle,
                  onLogin: onLogin,
                  onSignup: onSignup,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Shared form ───────────────────────────────────────────────────────────────

class _LoginForm extends StatelessWidget {
  final TextEditingController usernameCtrl;
  final TextEditingController passwordCtrl;
  final bool obscure;
  final bool loading;
  final String? error;
  final VoidCallback onObscureToggle;
  final VoidCallback onLogin;
  final VoidCallback onSignup;

  const _LoginForm({
    required this.usernameCtrl,
    required this.passwordCtrl,
    required this.obscure,
    required this.loading,
    required this.error,
    required this.onObscureToggle,
    required this.onLogin,
    required this.onSignup,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('Welcome back',
            style: GoogleFonts.poppins(
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: AppColors.navy)),
        const SizedBox(height: 6),
        Text('Sign in to your AdvocateAI account.',
            style: GoogleFonts.inter(
                fontSize: 14, color: AppColors.textSecondary)),
        const SizedBox(height: 32),

        // Error banner
        if (error != null) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.error.withOpacity(0.08),
              borderRadius: AppRadius.sm,
              border: Border.all(color: AppColors.error.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.error_outline,
                    color: AppColors.error, size: 16),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(error!,
                      style: GoogleFonts.inter(
                          fontSize: 13, color: AppColors.error)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],

        _FieldLabel('Username'),
        const SizedBox(height: 6),
        TextField(
          controller: usernameCtrl,
          textInputAction: TextInputAction.next,
          decoration: InputDecoration(
            hintText: 'Enter your username',
            prefixIcon:
                const Icon(Icons.person_outline, color: AppColors.textMuted),
          ),
        ),
        const SizedBox(height: 20),

        _FieldLabel('Password'),
        const SizedBox(height: 6),
        TextField(
          controller: passwordCtrl,
          obscureText: obscure,
          textInputAction: TextInputAction.done,
          onSubmitted: (_) => onLogin(),
          decoration: InputDecoration(
            hintText: 'Enter your password',
            prefixIcon:
                const Icon(Icons.lock_outline, color: AppColors.textMuted),
            suffixIcon: IconButton(
              icon: Icon(
                  obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                  color: AppColors.textMuted,
                  size: 20),
              onPressed: onObscureToggle,
            ),
          ),
        ),
        const SizedBox(height: 28),

        PrimaryButton(
          label: 'Sign in',
          onPressed: loading ? null : onLogin,
          loading: loading,
          width: double.infinity,
        ),
        const SizedBox(height: 24),

        Center(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text("Don't have an account? ",
                  style: GoogleFonts.inter(
                      fontSize: 14, color: AppColors.textSecondary)),
              GestureDetector(
                onTap: onSignup,
                child: Text('Create one',
                    style: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.blue)),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _FieldLabel extends StatelessWidget {
  final String text;
  const _FieldLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(text,
        style: GoogleFonts.inter(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary));
  }
}

class _BackButton extends StatelessWidget {
  final VoidCallback onBack;
  final bool dark;
  const _BackButton({required this.onBack, required this.dark});

  @override
  Widget build(BuildContext context) {
    return TextButton.icon(
      onPressed: onBack,
      icon: Icon(Icons.arrow_back,
          size: 16,
          color: dark ? AppColors.textSecondary : Colors.white.withOpacity(0.7)),
      label: Text('Back',
          style: GoogleFonts.inter(
              fontSize: 13,
              color: dark
                  ? AppColors.textSecondary
                  : Colors.white.withOpacity(0.7))),
      style: TextButton.styleFrom(padding: EdgeInsets.zero),
    );
  }
}
