import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';
import 'landing_page.dart';
import 'login_page.dart';
import 'role_home_page.dart';
import 'theme.dart';

Future<Map<String, dynamic>> signupUser(
    String username, String password, String role) async {
  try {
    final res = await http
        .post(
          Uri.parse('${ApiConfig.baseUrl}/signup'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'username': username,
            'password': password,
            'role': role,
          }),
        )
        .timeout(const Duration(seconds: 20));

    if (res.statusCode == 200 && res.body.isNotEmpty) {
      final data = jsonDecode(res.body);
      if (data is Map<String, dynamic>) return data;
    }
  } catch (e) {
    return {'success': false, 'message': 'Signup failed: $e'};
  }
  return {'success': false, 'message': 'Unable to sign up right now.'};
}

class SignupPage extends StatefulWidget {
  const SignupPage({super.key});

  @override
  State<SignupPage> createState() => _SignupPageState();
}

class _SignupPageState extends State<SignupPage>
    with SingleTickerProviderStateMixin {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  String _role = 'client';
  bool _obscure = true;
  bool _obscureConfirm = true;
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
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleSignup() async {
    final username = _usernameCtrl.text.trim();
    final password = _passwordCtrl.text;
    final confirm = _confirmCtrl.text;

    if (username.isEmpty || password.isEmpty || confirm.isEmpty) {
      setState(() => _error = 'Please fill in all fields.');
      return;
    }
    if (password.length < 6) {
      setState(() => _error = 'Password must be at least 6 characters.');
      return;
    }
    if (password != confirm) {
      setState(() => _error = 'Passwords do not match.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final result = await signupUser(username, password, _role);
      if (!mounted) return;

      if (result['success'] == true) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', result['access_token'] ?? '');
        await prefs.setInt('user_id', result['user_id'] ?? 0);
        await prefs.setString('user_email', result['email'] ?? '');
        await prefs.setString('user_role', result['role']?.toString() ?? 'client');

        if (!mounted) return;
        Navigator.pushReplacement(
          context,
          PageRouteBuilder(
            pageBuilder: (_, __, ___) =>
                RoleHomePage(role: result['role']?.toString() ?? 'client'),
            transitionsBuilder: (_, anim, __, child) =>
                FadeTransition(opacity: anim, child: child),
            transitionDuration: const Duration(milliseconds: 400),
          ),
        );
      } else {
        setState(
            () => _error = result['message']?.toString() ?? 'Sign up failed.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    final compact = w < 840;

    final form = _SignupForm(
      usernameCtrl: _usernameCtrl,
      passwordCtrl: _passwordCtrl,
      confirmCtrl: _confirmCtrl,
      role: _role,
      obscure: _obscure,
      obscureConfirm: _obscureConfirm,
      loading: _loading,
      error: _error,
      onRoleChanged: (r) => setState(() => _role = r),
      onObscureToggle: () => setState(() => _obscure = !_obscure),
      onObscureConfirmToggle: () =>
          setState(() => _obscureConfirm = !_obscureConfirm),
      onSignup: _handleSignup,
      onLogin: () => Navigator.pushReplacement(
          context, MaterialPageRoute(builder: (_) => const LoginPage())),
    );

    final onBack = () => Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (_) => const LandingPage()));

    if (compact) {
      return Scaffold(
        backgroundColor: AppColors.bgPage,
        body: SafeArea(
          child: FadeTransition(
            opacity: _fade,
            child: SlideTransition(
              position: _slide,
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _BackButton(onBack: onBack, dark: true),
                    const SizedBox(height: 32),
                    Center(
                      child: Column(children: [
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
                      ]),
                    ),
                    const SizedBox(height: 36),
                    form,
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.bgPage,
      body: Row(
        children: [
          // Brand panel
          Expanded(
            flex: 5,
            child: Container(
              decoration:
                  const BoxDecoration(gradient: AppGradients.navyHero),
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
                    child: const Icon(Icons.balance,
                        color: Colors.white, size: 26),
                  ),
                  const SizedBox(height: 20),
                  Text('Join AdvocateAI',
                      style: GoogleFonts.poppins(
                          fontSize: 32,
                          fontWeight: FontWeight.w800,
                          color: Colors.white)),
                  const SizedBox(height: 12),
                  Text('Get AI-powered legal help\nor grow your legal practice.',
                      style: GoogleFonts.inter(
                          fontSize: 15,
                          color: Colors.white.withOpacity(0.7),
                          height: 1.6)),
                  const SizedBox(height: 48),
                  _RolePickerCard(
                    role: 'client',
                    icon: Icons.person_outline,
                    title: 'I need legal help',
                    description: 'Get AI analysis and connect with lawyers',
                  ),
                  const SizedBox(height: 12),
                  _RolePickerCard(
                    role: 'lawyer',
                    icon: Icons.gavel_outlined,
                    title: 'I am a lawyer',
                    description:
                        'Browse cases and grow your client base',
                  ),
                  const Spacer(),
                  Text('© 2026 AdvocateAI',
                      style: GoogleFonts.inter(
                          fontSize: 12,
                          color: Colors.white.withOpacity(0.35))),
                ],
              ),
            ),
          ),
          // Form
          Expanded(
            flex: 6,
            child: FadeTransition(
              opacity: _fade,
              child: SlideTransition(
                position: _slide,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(vertical: 48),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 440),
                      child: form,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RolePickerCard extends StatelessWidget {
  final String role;
  final IconData icon;
  final String title;
  final String description;

  const _RolePickerCard(
      {required this.role,
      required this.icon,
      required this.title,
      required this.description});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: const BorderRadius.all(Radius.circular(12)),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Row(
        children: [
          Icon(icon, color: AppColors.gold, size: 22),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: GoogleFonts.inter(
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                      fontSize: 13)),
              Text(description,
                  style: GoogleFonts.inter(
                      fontSize: 11.5,
                      color: Colors.white.withOpacity(0.6))),
            ],
          ),
        ],
      ),
    );
  }
}

class _SignupForm extends StatelessWidget {
  final TextEditingController usernameCtrl;
  final TextEditingController passwordCtrl;
  final TextEditingController confirmCtrl;
  final String role;
  final bool obscure;
  final bool obscureConfirm;
  final bool loading;
  final String? error;
  final ValueChanged<String> onRoleChanged;
  final VoidCallback onObscureToggle;
  final VoidCallback onObscureConfirmToggle;
  final VoidCallback onSignup;
  final VoidCallback onLogin;

  const _SignupForm({
    required this.usernameCtrl,
    required this.passwordCtrl,
    required this.confirmCtrl,
    required this.role,
    required this.obscure,
    required this.obscureConfirm,
    required this.loading,
    required this.error,
    required this.onRoleChanged,
    required this.onObscureToggle,
    required this.onObscureConfirmToggle,
    required this.onSignup,
    required this.onLogin,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('Create your account',
            style: GoogleFonts.poppins(
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: AppColors.navy)),
        const SizedBox(height: 6),
        Text('Free to join. No credit card required.',
            style: GoogleFonts.inter(
                fontSize: 14, color: AppColors.textSecondary)),
        const SizedBox(height: 28),

        // Error
        if (error != null) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.error.withOpacity(0.08),
              borderRadius: AppRadius.sm,
              border: Border.all(color: AppColors.error.withOpacity(0.3)),
            ),
            child: Row(children: [
              const Icon(Icons.error_outline,
                  color: AppColors.error, size: 16),
              const SizedBox(width: 8),
              Expanded(
                  child: Text(error!,
                      style: GoogleFonts.inter(
                          fontSize: 13, color: AppColors.error))),
            ]),
          ),
          const SizedBox(height: 20),
        ],

        // I am a … selector
        _FieldLabel('I am a …'),
        const SizedBox(height: 8),
        Row(children: [
          _RoleChip(
            label: 'Client',
            icon: Icons.person_outline,
            selected: role == 'client',
            onTap: () => onRoleChanged('client'),
          ),
          const SizedBox(width: 10),
          _RoleChip(
            label: 'Lawyer',
            icon: Icons.gavel_outlined,
            selected: role == 'lawyer',
            onTap: () => onRoleChanged('lawyer'),
          ),
        ]),
        const SizedBox(height: 20),

        _FieldLabel('Username'),
        const SizedBox(height: 6),
        TextField(
          controller: usernameCtrl,
          textInputAction: TextInputAction.next,
          decoration: InputDecoration(
            hintText: 'Choose a username',
            prefixIcon: const Icon(Icons.person_outline,
                color: AppColors.textMuted),
          ),
        ),
        const SizedBox(height: 16),

        _FieldLabel('Password'),
        const SizedBox(height: 6),
        TextField(
          controller: passwordCtrl,
          obscureText: obscure,
          textInputAction: TextInputAction.next,
          decoration: InputDecoration(
            hintText: 'Minimum 6 characters',
            prefixIcon:
                const Icon(Icons.lock_outline, color: AppColors.textMuted),
            suffixIcon: IconButton(
              icon: Icon(
                  obscure
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                  color: AppColors.textMuted,
                  size: 20),
              onPressed: onObscureToggle,
            ),
          ),
        ),
        const SizedBox(height: 16),

        _FieldLabel('Confirm password'),
        const SizedBox(height: 6),
        TextField(
          controller: confirmCtrl,
          obscureText: obscureConfirm,
          textInputAction: TextInputAction.done,
          onSubmitted: (_) => loading ? null : onSignup(),
          decoration: InputDecoration(
            hintText: 'Repeat your password',
            prefixIcon: const Icon(Icons.lock_outline,
                color: AppColors.textMuted),
            suffixIcon: IconButton(
              icon: Icon(
                  obscureConfirm
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                  color: AppColors.textMuted,
                  size: 20),
              onPressed: onObscureConfirmToggle,
            ),
          ),
        ),
        const SizedBox(height: 28),

        PrimaryButton(
          label: 'Create account',
          onPressed: loading ? null : onSignup,
          loading: loading,
          width: double.infinity,
        ),
        const SizedBox(height: 24),

        Center(
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Text('Already have an account? ',
                style: GoogleFonts.inter(
                    fontSize: 14, color: AppColors.textSecondary)),
            GestureDetector(
              onTap: onLogin,
              child: Text('Log in',
                  style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.blue)),
            ),
          ]),
        ),
      ],
    );
  }
}

class _RoleChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  const _RoleChip({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.blue.withOpacity(0.08) : AppColors.surfaceAlt,
          borderRadius: AppRadius.sm,
          border: Border.all(
            color: selected ? AppColors.blue : AppColors.border,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon,
                size: 16,
                color: selected ? AppColors.blue : AppColors.textMuted),
            const SizedBox(width: 6),
            Text(label,
                style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: selected
                        ? AppColors.blue
                        : AppColors.textSecondary)),
          ],
        ),
      ),
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
