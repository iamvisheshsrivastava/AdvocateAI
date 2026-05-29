import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'theme.dart';
import 'login_page.dart';
import 'signup_page.dart';

class LandingPage extends StatefulWidget {
  const LandingPage({super.key});

  @override
  State<LandingPage> createState() => _LandingPageState();
}

class _LandingPageState extends State<LandingPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _heroCtrl;
  late Animation<double> _heroFade;
  late Animation<Offset> _heroSlide;

  @override
  void initState() {
    super.initState();
    _heroCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 900));
    _heroFade = CurvedAnimation(parent: _heroCtrl, curve: Curves.easeOut);
    _heroSlide = Tween<Offset>(
            begin: const Offset(0, 0.06), end: Offset.zero)
        .animate(CurvedAnimation(parent: _heroCtrl, curve: Curves.easeOut));
    _heroCtrl.forward();
  }

  @override
  void dispose() {
    _heroCtrl.dispose();
    super.dispose();
  }

  void _goLogin() => Navigator.push(
      context, MaterialPageRoute(builder: (_) => LoginPage()));

  void _goSignup() => Navigator.push(
      context, MaterialPageRoute(builder: (_) => const SignupPage()));

  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    final compact = w < 920;

    return Scaffold(
      backgroundColor: AppColors.bgPage,
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _NavBar(compact: compact, onLogin: _goLogin, onSignup: _goSignup),
            _HeroSection(
                compact: compact,
                fade: _heroFade,
                slide: _heroSlide,
                onGetStarted: _goSignup,
                onLogin: _goLogin),
            _FeaturesSection(compact: compact),
            _HowItWorksSection(compact: compact),
            _ForLawyersSection(compact: compact),
            _CtaSection(onGetStarted: _goSignup),
            _Footer(),
          ],
        ),
      ),
    );
  }
}

// ── Nav bar ──────────────────────────────────────────────────────────────────

class _NavBar extends StatelessWidget {
  final bool compact;
  final VoidCallback onLogin;
  final VoidCallback onSignup;

  const _NavBar(
      {required this.compact, required this.onLogin, required this.onSignup});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      padding: EdgeInsets.symmetric(
          horizontal: compact ? 20 : 64, vertical: 0),
      height: 68,
      child: Row(
        children: [
          _Logo(),
          const Spacer(),
          if (!compact) ...[
            _NavLink('Features'),
            _NavLink('For Lawyers'),
            _NavLink('Pricing'),
            const SizedBox(width: 16),
          ],
          TextButton(
            onPressed: onLogin,
            child: Text('Log in',
                style: GoogleFonts.inter(
                    fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          ),
          const SizedBox(width: 8),
          SizedBox(
            height: 38,
            child: ElevatedButton(
              onPressed: onSignup,
              style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.blue,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  shape: const RoundedRectangleBorder(
                      borderRadius: AppRadius.md)),
              child: Text('Get started',
                  style: GoogleFonts.inter(
                      fontWeight: FontWeight.w600, fontSize: 14)),
            ),
          ),
        ],
      ),
    );
  }
}

class _Logo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: const BoxDecoration(
            gradient: AppGradients.blueAccent,
            borderRadius: AppRadius.sm,
          ),
          child: const Icon(Icons.balance, color: Colors.white, size: 20),
        ),
        const SizedBox(width: 10),
        Text('AdvocateAI',
            style: GoogleFonts.poppins(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppColors.navy)),
      ],
    );
  }
}

class _NavLink extends StatelessWidget {
  final String label;
  const _NavLink(this.label);

  @override
  Widget build(BuildContext context) => TextButton(
        onPressed: () {},
        child: Text(label,
            style: GoogleFonts.inter(
                fontWeight: FontWeight.w500,
                color: AppColors.textSecondary,
                fontSize: 14)),
      );
}

// ── Hero ─────────────────────────────────────────────────────────────────────

class _HeroSection extends StatelessWidget {
  final bool compact;
  final Animation<double> fade;
  final Animation<Offset> slide;
  final VoidCallback onGetStarted;
  final VoidCallback onLogin;

  const _HeroSection({
    required this.compact,
    required this.fade,
    required this.slide,
    required this.onGetStarted,
    required this.onLogin,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(gradient: AppGradients.navyHero),
      padding: EdgeInsets.symmetric(
          horizontal: compact ? 24 : 80,
          vertical: compact ? 64 : 96),
      child: FadeTransition(
        opacity: fade,
        child: SlideTransition(
          position: slide,
          child: compact
              ? _HeroContent(
                  compact: compact,
                  onGetStarted: onGetStarted,
                  onLogin: onLogin)
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                        flex: 6,
                        child: _HeroContent(
                            compact: compact,
                            onGetStarted: onGetStarted,
                            onLogin: onLogin)),
                    const SizedBox(width: 64),
                    Expanded(flex: 5, child: _HeroVisual()),
                  ],
                ),
        ),
      ),
    );
  }
}

class _HeroContent extends StatelessWidget {
  final bool compact;
  final VoidCallback onGetStarted;
  final VoidCallback onLogin;

  const _HeroContent(
      {required this.compact,
      required this.onGetStarted,
      required this.onLogin});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: AppColors.gold.withOpacity(0.15),
            borderRadius: AppRadius.full,
            border: Border.all(color: AppColors.gold.withOpacity(0.4)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.auto_awesome,
                  size: 14, color: AppColors.gold),
              const SizedBox(width: 6),
              Text('AI-powered legal assistance',
                  style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.gold)),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Text(
          'Your legal rights,\ndefended with AI.',
          style: GoogleFonts.poppins(
            fontSize: compact ? 38 : 52,
            fontWeight: FontWeight.w800,
            color: Colors.white,
            height: 1.12,
          ),
        ),
        const SizedBox(height: 8),
        ShaderMask(
          shaderCallback: (bounds) =>
              AppGradients.goldAccent.createShader(bounds),
          blendMode: BlendMode.srcIn,
          child: Text(
            'Find the perfect lawyer.',
            style: GoogleFonts.poppins(
              fontSize: compact ? 28 : 38,
              fontWeight: FontWeight.w700,
              height: 1.2,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'AdvocateAI analyses your legal situation with AI, organises your case, and connects you with the right lawyer — in seconds.',
          style: GoogleFonts.inter(
            fontSize: compact ? 15 : 17,
            color: Colors.white.withOpacity(0.75),
            height: 1.65,
          ),
        ),
        const SizedBox(height: 36),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            SizedBox(
              height: 52,
              child: DecoratedBox(
                decoration: BoxDecoration(
                    borderRadius: AppRadius.md,
                    boxShadow: AppShadows.button),
                child: ElevatedButton.icon(
                  onPressed: onGetStarted,
                  icon: const Icon(Icons.arrow_forward, size: 18),
                  label: Text('Get started free',
                      style: GoogleFonts.inter(
                          fontWeight: FontWeight.w700, fontSize: 15)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.blue,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 28, vertical: 14),
                    shape: const RoundedRectangleBorder(
                        borderRadius: AppRadius.md),
                  ),
                ),
              ),
            ),
            SizedBox(
              height: 52,
              child: OutlinedButton(
                onPressed: onLogin,
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: BorderSide(
                      color: Colors.white.withOpacity(0.4), width: 1.5),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 28, vertical: 14),
                  shape: const RoundedRectangleBorder(
                      borderRadius: AppRadius.md),
                ),
                child: Text('Log in',
                    style: GoogleFonts.inter(
                        fontWeight: FontWeight.w600, fontSize: 15)),
              ),
            ),
          ],
        ),
        const SizedBox(height: 32),
        Row(
          children: [
            _TrustPill(Icons.verified_user, 'Bank-grade security'),
            const SizedBox(width: 16),
            _TrustPill(Icons.flash_on, 'Instant AI analysis'),
          ],
        ),
      ],
    );
  }
}

class _TrustPill extends StatelessWidget {
  final IconData icon;
  final String label;
  const _TrustPill(this.icon, this.label);

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: AppColors.gold),
        const SizedBox(width: 6),
        Text(label,
            style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: Colors.white.withOpacity(0.65))),
      ],
    );
  }
}

class _HeroVisual extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: const BorderRadius.all(Radius.circular(20)),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Column(
        children: [
          _ChatBubble(
              text: 'My landlord is refusing to return my deposit after move-out.',
              isUser: true),
          const SizedBox(height: 12),
          _ChatBubble(
              text:
                  'Based on German tenancy law (§ 548 BGB), your landlord has a limited window to claim deductions. You likely have a strong case. I\'ve found 3 specialised lawyers in your area.',
              isUser: false),
          const SizedBox(height: 16),
          _LawyerCard(
              name: 'Dr. Anna Müller',
              area: 'Tenancy Law',
              rating: '4.9',
              city: 'Berlin'),
          const SizedBox(height: 10),
          _LawyerCard(
              name: 'Thomas Fischer',
              area: 'Property Law',
              rating: '4.8',
              city: 'Berlin'),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  final String text;
  final bool isUser;
  const _ChatBubble({required this.text, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 280),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isUser
              ? AppColors.blue
              : Colors.white.withOpacity(0.12),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(12),
            topRight: const Radius.circular(12),
            bottomLeft: isUser ? const Radius.circular(12) : Radius.zero,
            bottomRight: isUser ? Radius.zero : const Radius.circular(12),
          ),
        ),
        child: Text(text,
            style: GoogleFonts.inter(
                fontSize: 12.5,
                color: Colors.white.withOpacity(isUser ? 1 : 0.85),
                height: 1.5)),
      ),
    );
  }
}

class _LawyerCard extends StatelessWidget {
  final String name;
  final String area;
  final String rating;
  final String city;

  const _LawyerCard(
      {required this.name,
      required this.area,
      required this.rating,
      required this.city});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: const BorderRadius.all(Radius.circular(10)),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: AppColors.gold.withOpacity(0.3),
            child: Text(name[0],
                style: GoogleFonts.poppins(
                    fontWeight: FontWeight.w700,
                    color: AppColors.gold,
                    fontSize: 14)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name,
                    style: GoogleFonts.inter(
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                        fontSize: 13)),
                Text('$area · $city',
                    style: GoogleFonts.inter(
                        fontSize: 11,
                        color: Colors.white.withOpacity(0.6))),
              ],
            ),
          ),
          Row(
            children: [
              const Icon(Icons.star, size: 13, color: AppColors.gold),
              const SizedBox(width: 3),
              Text(rating,
                  style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.gold)),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Features ─────────────────────────────────────────────────────────────────

class _FeaturesSection extends StatelessWidget {
  final bool compact;
  const _FeaturesSection({required this.compact});

  static const _features = [
    _FeatureData(
        Icons.psychology_alt,
        'AI Legal Analysis',
        'Describe your situation in plain language. Our AI instantly identifies the legal area, urgency, and applicable laws.',
        AppColors.blue),
    _FeatureData(
        Icons.description,
        'Document Intelligence',
        'Upload contracts, notices, or letters. We extract key obligations, deadlines, and risks automatically.',
        AppColors.gold),
    _FeatureData(
        Icons.people,
        'Smart Lawyer Matching',
        'Matched by expertise, city, language, and responsiveness — not just the biggest ad budget.',
        AppColors.success),
    _FeatureData(
        Icons.chat,
        'Secure Messaging',
        'Communicate directly with your lawyer inside a secure, documented case workspace.',
        Color(0xFF8B5CF6)),
    _FeatureData(
        Icons.timeline,
        'Case Timeline',
        'Track every event, deadline, and document in a clear, organised case timeline.',
        Color(0xFFEC4899)),
    _FeatureData(
        Icons.shield,
        'Privacy First',
        'Your data is encrypted at rest and in transit. We never sell your information.',
        AppColors.navy),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
          horizontal: compact ? 24 : 80, vertical: 80),
      color: AppColors.bgPage,
      child: Column(
        children: [
          _SectionLabel('Features'),
          const SizedBox(height: 12),
          Text('Everything you need,\nnothing you don\'t.',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                  fontSize: compact ? 28 : 38,
                  fontWeight: FontWeight.w700,
                  color: AppColors.navy,
                  height: 1.2)),
          const SizedBox(height: 52),
          LayoutBuilder(
            builder: (context, c) {
              final cols = c.maxWidth > 700 ? 3 : 1;
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: cols,
                  crossAxisSpacing: 20,
                  mainAxisSpacing: 20,
                  childAspectRatio: cols == 3 ? 1.05 : 2.5,
                ),
                itemCount: _features.length,
                itemBuilder: (_, i) => _FeatureCard(_features[i]),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _FeatureData {
  final IconData icon;
  final String title;
  final String description;
  final Color color;
  const _FeatureData(this.icon, this.title, this.description, this.color);
}

class _FeatureCard extends StatelessWidget {
  final _FeatureData data;
  const _FeatureCard(this.data);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: const BorderRadius.all(Radius.circular(16)),
        border: Border.all(color: AppColors.border),
        boxShadow: AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
                color: data.color.withOpacity(0.1),
                borderRadius: AppRadius.sm),
            child: Icon(data.icon, color: data.color, size: 22),
          ),
          const SizedBox(height: 16),
          Text(data.title,
              style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary)),
          const SizedBox(height: 8),
          Expanded(
            child: Text(data.description,
                style: GoogleFonts.inter(
                    fontSize: 13.5,
                    color: AppColors.textSecondary,
                    height: 1.6)),
          ),
        ],
      ),
    );
  }
}

// ── How it works ─────────────────────────────────────────────────────────────

class _HowItWorksSection extends StatelessWidget {
  final bool compact;
  const _HowItWorksSection({required this.compact});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
          horizontal: compact ? 24 : 80, vertical: 80),
      color: AppColors.surface,
      child: Column(
        children: [
          _SectionLabel('How it works'),
          const SizedBox(height: 12),
          Text('From problem to lawyer\nin three simple steps.',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                  fontSize: compact ? 28 : 38,
                  fontWeight: FontWeight.w700,
                  color: AppColors.navy,
                  height: 1.2)),
          const SizedBox(height: 52),
          LayoutBuilder(builder: (context, c) {
            final horiz = c.maxWidth > 700;
            final steps = [
              _StepData('1', Icons.chat_bubble_outline, 'Describe your problem',
                  'Tell us what\'s happening in plain language — no legal jargon required.'),
              _StepData('2', Icons.analytics_outlined, 'AI analyses your case',
                  'We identify the legal area, urgency level, relevant laws, and next actions.'),
              _StepData('3', Icons.handshake_outlined, 'Connect with a lawyer',
                  'Browse matched lawyers, review profiles, and message the best fit directly.'),
            ];
            return horiz
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: steps
                        .expand((s) => [
                              Expanded(child: _StepCard(s)),
                              if (s != steps.last)
                                Padding(
                                  padding: const EdgeInsets.only(top: 36),
                                  child: Icon(Icons.arrow_forward,
                                      color: AppColors.border, size: 24),
                                ),
                            ])
                        .toList(),
                  )
                : Column(
                    children: steps
                        .map((s) => Padding(
                            padding: const EdgeInsets.only(bottom: 20),
                            child: _StepCard(s)))
                        .toList());
          }),
        ],
      ),
    );
  }
}

class _StepData {
  final String number;
  final IconData icon;
  final String title;
  final String description;
  const _StepData(this.number, this.icon, this.title, this.description);
}

class _StepCard extends StatelessWidget {
  final _StepData data;
  const _StepCard(this.data);

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: const BoxDecoration(
                gradient: AppGradients.blueAccent,
                shape: BoxShape.circle,
              ),
              child: Icon(data.icon, color: Colors.white, size: 28),
            ),
            Positioned(
              top: 0,
              right: 0,
              child: Container(
                width: 22,
                height: 22,
                decoration: const BoxDecoration(
                    color: AppColors.gold, shape: BoxShape.circle),
                child: Center(
                  child: Text(data.number,
                      style: GoogleFonts.poppins(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: Colors.white)),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(data.title,
            textAlign: TextAlign.center,
            style: GoogleFonts.poppins(
                fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.navy)),
        const SizedBox(height: 8),
        Text(data.description,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
                fontSize: 13.5,
                color: AppColors.textSecondary,
                height: 1.6)),
      ],
    );
  }
}

// ── For Lawyers ───────────────────────────────────────────────────────────────

class _ForLawyersSection extends StatelessWidget {
  final bool compact;
  const _ForLawyersSection({required this.compact});

  @override
  Widget build(BuildContext context) {
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionLabel('For Lawyers'),
        const SizedBox(height: 16),
        Text('Grow your practice\nwith quality clients.',
            style: GoogleFonts.poppins(
                fontSize: compact ? 26 : 34,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                height: 1.2)),
        const SizedBox(height: 20),
        ...[
          'Browse pre-qualified cases that match your specialisation',
          'AI-generated case briefs — no cold calls, no vague enquiries',
          'Real-time messaging and document sharing in one place',
          'Build your profile with ratings and verified credentials',
        ].map((t) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 3),
                    width: 18,
                    height: 18,
                    decoration: const BoxDecoration(
                        color: AppColors.gold, shape: BoxShape.circle),
                    child: const Icon(Icons.check, size: 11, color: Colors.white),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(t,
                        style: GoogleFonts.inter(
                            fontSize: 14,
                            color: Colors.white.withOpacity(0.85),
                            height: 1.5)),
                  ),
                ],
              ),
            )),
      ],
    );

    return Container(
      decoration: const BoxDecoration(gradient: AppGradients.navyHero),
      padding: EdgeInsets.symmetric(
          horizontal: compact ? 24 : 80, vertical: 80),
      child: compact
          ? content
          : Row(
              children: [
                Expanded(flex: 5, child: content),
                const SizedBox(width: 80),
                Expanded(
                    flex: 4,
                    child: Container(
                      padding: const EdgeInsets.all(28),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.07),
                        borderRadius: const BorderRadius.all(Radius.circular(20)),
                        border:
                            Border.all(color: Colors.white.withOpacity(0.12)),
                      ),
                      child: Column(
                        children: [
                          _MetricTile(Icons.work, '340', 'Open cases today'),
                          const Divider(color: Color(0x22FFFFFF)),
                          _MetricTile(
                              Icons.speed, '< 2 min', 'Average match time'),
                          const Divider(color: Color(0x22FFFFFF)),
                          _MetricTile(
                              Icons.trending_up, '68 %', 'Case acceptance rate'),
                        ],
                      ),
                    )),
              ],
            ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  const _MetricTile(this.icon, this.value, this.label);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        children: [
          Icon(icon, color: AppColors.gold, size: 24),
          const SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(value,
                  style: GoogleFonts.poppins(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: Colors.white)),
              Text(label,
                  style: GoogleFonts.inter(
                      fontSize: 13,
                      color: Colors.white.withOpacity(0.6))),
            ],
          ),
        ],
      ),
    );
  }
}

// ── CTA ──────────────────────────────────────────────────────────────────────

class _CtaSection extends StatelessWidget {
  final VoidCallback onGetStarted;
  const _CtaSection({required this.onGetStarted});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 40, vertical: 80),
      padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 60),
      decoration: BoxDecoration(
        gradient: AppGradients.blueAccent,
        borderRadius: const BorderRadius.all(Radius.circular(24)),
        boxShadow: [
          BoxShadow(
              color: AppColors.blue.withOpacity(0.35),
              blurRadius: 40,
              offset: const Offset(0, 16)),
        ],
      ),
      child: Column(
        children: [
          Text('Ready to take action?',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                  fontSize: 36,
                  fontWeight: FontWeight.w800,
                  color: Colors.white)),
          const SizedBox(height: 12),
          Text(
              'Describe your legal issue for free. No credit card required.',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                  fontSize: 16,
                  color: Colors.white.withOpacity(0.8),
                  height: 1.5)),
          const SizedBox(height: 32),
          SizedBox(
            height: 52,
            child: ElevatedButton(
              onPressed: onGetStarted,
              style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: AppColors.blue,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 36, vertical: 14),
                  shape: const RoundedRectangleBorder(
                      borderRadius: AppRadius.md)),
              child: Text('Start for free',
                  style: GoogleFonts.inter(
                      fontWeight: FontWeight.w700, fontSize: 16)),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Footer ────────────────────────────────────────────────────────────────────

class _Footer extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 32),
      decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.border))),
      child: Row(
        children: [
          _Logo(),
          const Spacer(),
          Text('© 2026 AdvocateAI. All rights reserved.',
              style: GoogleFonts.inter(
                  fontSize: 13, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

// ── Shared ────────────────────────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.blue.withOpacity(0.08),
        borderRadius: AppRadius.full,
        border: Border.all(color: AppColors.blue.withOpacity(0.2)),
      ),
      child: Text(text.toUpperCase(),
          style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.blue,
              letterSpacing: 1.2)),
    );
  }
}
