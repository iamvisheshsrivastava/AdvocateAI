import 'package:flutter/material.dart';
import 'login_page.dart';
import 'signup_page.dart';

class LandingPage extends StatelessWidget {
  const LandingPage({super.key});

  @override
  Widget build(BuildContext context) {
    const navy = Color(0xFF0B1F3A);
    const blue = Color(0xFF1E63E9);

    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFFF5F9FF), Color(0xFFEAF2FF)],
              ),
            ),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              width: 280,
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [Color(0x1E1E63E9), Color(0x001E63E9)],
                ),
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomRight,
            child: Container(
              width: 260,
              height: 260,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [Color(0x261E63E9), Color(0x001E63E9)],
                ),
              ),
            ),
          ),
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xAAFFFFFF), Color(0xE6FFFFFF)],
              ),
            ),
          ),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final isCompact = constraints.maxWidth < 920;

                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
                  child: Column(
                    children: [
                      Expanded(
                        child: Center(
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            child: ConstrainedBox(
                              constraints: BoxConstraints(maxWidth: isCompact ? 760 : 860),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  _HeroMark(isCompact: isCompact),
                                  SizedBox(height: isCompact ? 18 : 22),
                                  Text(
                                    'AdvocateAI',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      fontSize: isCompact ? 56 : 70,
                                      height: 1,
                                      color: navy,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  const SizedBox(height: 14),
                                  Container(
                                    width: isCompact ? 260 : 360,
                                    height: 2,
                                    color: const Color(0x551E63E9),
                                  ),
                                  const SizedBox(height: 6),
                                  const Icon(Icons.diamond, color: blue, size: 14),
                                  const SizedBox(height: 6),
                                  Container(
                                    width: isCompact ? 260 : 360,
                                    height: 2,
                                    color: const Color(0x551E63E9),
                                  ),
                                  SizedBox(height: isCompact ? 16 : 20),
                                  Text(
                                    'The smartest way to find the',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      fontSize: isCompact ? 18 : 22,
                                      color: navy,
                                      height: 1.3,
                                    ),
                                  ),
                                  Text(
                                    'perfect lawyer in your city.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      fontSize: isCompact ? 22 : 30,
                                      color: blue,
                                      height: 1.2,
                                      fontStyle: FontStyle.italic,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  SizedBox(height: isCompact ? 14 : 18),
                                  Container(
                                    width: isCompact ? 420 : 620,
                                    height: 1,
                                    color: const Color(0x553B4B64),
                                  ),
                                  SizedBox(height: isCompact ? 14 : 18),
                                  ConstrainedBox(
                                    constraints: const BoxConstraints(maxWidth: 740),
                                    child: const Text(
                                      'AdvocateAI helps you discover the best advocates near you based on top reviews, expertise, and legal categories. Powered by AI-driven semantic search, we connect you with the right legal professional in seconds.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        fontSize: 16,
                                        color: Color(0xFF42556F),
                                        height: 1.6,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                  SizedBox(height: isCompact ? 16 : 20),
                                  Text(
                                    'Find the perfect lawyer for you.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      fontSize: isCompact ? 42 : 50,
                                      color: navy,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  SizedBox(height: isCompact ? 16 : 20),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      _HeroButton(
                                        label: 'Log In',
                                        background: blue,
                                        foreground: Colors.white,
                                        onPressed: () {
                                          Navigator.push(
                                            context,
                                            MaterialPageRoute(builder: (_) => LoginPage()),
                                          );
                                        },
                                      ),
                                      const SizedBox(width: 18),
                                      _HeroButton(
                                        label: 'Sign Up',
                                        background: Colors.white,
                                        foreground: blue,
                                        borderColor: const Color(0xFF1E63E9),
                                        onPressed: () {
                                          Navigator.push(
                                            context,
                                            MaterialPageRoute(builder: (_) => const SignupPage()),
                                          );
                                        },
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                      const Column(
                        children: [
                          Text(
                            '© 2026 AdvocateAI. All rights reserved.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF4A5C74),
                            ),
                          ),
                          SizedBox(height: 10),
                          Text(
                            'We are expanding to handle all legal matters digitally. Stay connected for upcoming features.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 12.5,
                              color: Color(0xFF596C85),
                              fontStyle: FontStyle.italic,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroMark extends StatelessWidget {
  final bool isCompact;

  const _HeroMark({required this.isCompact});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: isCompact ? 120 : 140,
      height: isCompact ? 90 : 104,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Positioned(
            top: 2,
            child: Icon(
              Icons.balance,
              size: isCompact ? 92 : 108,
              color: const Color(0xFF1E63E9),
            ),
          ),
          Container(
            width: isCompact ? 56 : 64,
            height: isCompact ? 56 : 64,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(99),
              border: Border.all(color: const Color(0xFFD9E1EC), width: 2),
            ),
            child: Icon(
              Icons.psychology,
              size: isCompact ? 32 : 36,
              color: const Color(0xFF1A3F67),
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroButton extends StatelessWidget {
  final String label;
  final Color background;
  final Color foreground;
  final Color? borderColor;
  final VoidCallback onPressed;

  const _HeroButton({
    required this.label,
    required this.background,
    required this.foreground,
    this.borderColor,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 190,
      height: 56,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          boxShadow: [
            BoxShadow(
              color: const Color(0x2A1E63E9),
              blurRadius: 10,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor: background,
            foregroundColor: foreground,
            elevation: 0,
            side: borderColor != null ? BorderSide(color: borderColor!, width: 1.4) : null,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
          child: Text(
            label,
            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700),
          ),
        ),
      ),
    );
  }
}