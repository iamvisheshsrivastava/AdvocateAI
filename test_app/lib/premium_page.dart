import 'package:flutter/material.dart';

class PremiumPage extends StatelessWidget {
  const PremiumPage({super.key});

  @override
  Widget build(BuildContext context) {
    final plans = _plans;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pricing'),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFF7F9FC), Color(0xFFEFF6FB)],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isMobile = constraints.maxWidth < 900;

              return SingleChildScrollView(
                padding: EdgeInsets.symmetric(
                  horizontal: isMobile ? 16 : 32,
                  vertical: isMobile ? 20 : 28,
                ),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1200),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        const Text(
                          'Choose a plan that fits your legal search needs',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 30,
                            fontWeight: FontWeight.bold,
                            height: 1.2,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          'Start free and upgrade when you need more AI-powered legal support.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 16,
                            color: Colors.grey.shade700,
                          ),
                        ),
                        const SizedBox(height: 28),
                        Wrap(
                          spacing: 16,
                          runSpacing: 16,
                          alignment: WrapAlignment.center,
                          children: plans
                              .map((plan) => SizedBox(
                                    width: isMobile ? constraints.maxWidth : 360,
                                    child: _PricingCard(plan: plan),
                                  ))
                              .toList(),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _PricingCard extends StatelessWidget {
  final _PlanData plan;

  const _PricingCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    final isCurrentPlan = plan.isCurrentPlan;

    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: plan.highlighted ? const Color(0xFF1E88E5) : Colors.grey.shade200,
            width: plan.highlighted ? 1.6 : 1,
          ),
          color: Colors.white,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: const Color(0xFFEEF6FF),
                  child: Icon(plan.icon, color: const Color(0xFF1E88E5)),
                ),
                const SizedBox(width: 10),
                Text(
                  plan.name,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (plan.highlighted) ...[
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE3F2FD),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      'Popular',
                      style: TextStyle(
                        color: Color(0xFF1565C0),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 16),
            Text(
              plan.price,
              style: const TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              'Per month',
              style: TextStyle(color: Colors.grey.shade600),
            ),
            const SizedBox(height: 18),
            ...plan.features.map(
              (feature) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 2),
                      child: Icon(
                        Icons.check_circle,
                        size: 18,
                        color: Color(0xFF1E88E5),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        feature,
                        style: const TextStyle(fontSize: 14.5, height: 1.3),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: isCurrentPlan
                    ? null
                    : () {
                        showDialog<void>(
                          context: context,
                          builder: (dialogContext) => AlertDialog(
                            title: const Text('Coming Soon'),
                            content: const Text('Payment integration coming soon.'),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(dialogContext),
                                child: const Text('OK'),
                              ),
                            ],
                          ),
                        );
                      },
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  backgroundColor:
                      isCurrentPlan ? Colors.grey.shade400 : const Color(0xFF1E88E5),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Text(isCurrentPlan ? 'Current Plan' : 'Upgrade'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlanData {
  final String name;
  final String price;
  final List<String> features;
  final IconData icon;
  final bool isCurrentPlan;
  final bool highlighted;

  const _PlanData({
    required this.name,
    required this.price,
    required this.features,
    required this.icon,
    this.isCurrentPlan = false,
    this.highlighted = false,
  });
}

const List<_PlanData> _plans = [
  _PlanData(
    name: 'Free',
    price: '€0',
    icon: Icons.verified_user_outlined,
    isCurrentPlan: true,
    features: [
      '5 AI lawyer searches per day',
      'Basic lawyer profiles',
      'Watchlist support',
    ],
  ),
  _PlanData(
    name: 'Premium',
    price: '€19',
    icon: Icons.star_outline,
    highlighted: true,
    features: [
      'Unlimited AI lawyer search',
      'Lawyer comparison',
      'Priority lawyer recommendations',
      'AI case summary generation',
      'Better recommendation ranking',
    ],
  ),
  _PlanData(
    name: 'Pro',
    price: '€49',
    icon: Icons.workspace_premium_outlined,
    features: [
      'Advanced AI legal assistant',
      'Legal document explanation',
      'Unlimited search',
      'Consultation booking support',
      'Priority support',
    ],
  ),
];