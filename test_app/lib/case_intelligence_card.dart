import 'package:flutter/material.dart';

class CaseIntelligenceCard extends StatelessWidget {
  final Map<String, dynamic> data;
  final String title;
  final Color accentColor;

  const CaseIntelligenceCard({
    super.key,
    required this.data,
    this.title = 'Case Intelligence',
    this.accentColor = const Color(0xFF155EEF),
  });

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) {
      return const SizedBox.shrink();
    }

    final readinessScore = _asInt(data['readiness_score']);
    final readinessBand = (data['readiness_band'] ?? 'Needs Attention').toString();
    final missingInformation = _asStringList(data['missing_information']);
    final followUpQuestions = _asStringList(data['follow_up_questions']);
    final riskFlags = _asStringList(data['risk_flags']);
    final recommendedNextSteps = _asStringList(data['recommended_next_steps']);
    final deadlines = _asDeadlineList(data['deadlines']);
    final consultationPrep =
        Map<String, dynamic>.from(data['consultation_prep'] as Map? ?? <String, dynamic>{});
    final oneLineGoal = (consultationPrep['one_line_goal'] ?? '').toString();
    final documentsToBring = _asStringList(consultationPrep['documents_to_bring']);
    final questionsToAsk = _asStringList(consultationPrep['questions_to_ask']);

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: accentColor.withValues(alpha: 0.18)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.insights_outlined, color: accentColor),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Turn analysis into a lawyer-ready intake package.',
                        style: TextStyle(color: Colors.grey.shade700, height: 1.3),
                      ),
                    ],
                  ),
                ),
                _ScorePill(
                  score: readinessScore,
                  label: readinessBand,
                  accentColor: accentColor,
                ),
              ],
            ),
            if (oneLineGoal.isNotEmpty) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF6F8FB),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Text(
                  oneLineGoal,
                  style: const TextStyle(fontSize: 14.5, height: 1.4),
                ),
              ),
            ],
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _SectionTile(
                  title: 'Missing Information',
                  icon: Icons.playlist_add_check_circle_outlined,
                  items: missingInformation,
                  width: 340,
                ),
                _SectionTile(
                  title: 'Follow-up Questions',
                  icon: Icons.quiz_outlined,
                  items: followUpQuestions,
                  width: 340,
                ),
                _SectionTile(
                  title: 'Risk Flags',
                  icon: Icons.warning_amber_outlined,
                  items: riskFlags,
                  width: 340,
                  accent: const Color(0xFFB54708),
                ),
                _SectionTile(
                  title: 'Recommended Next Steps',
                  icon: Icons.route_outlined,
                  items: recommendedNextSteps,
                  width: 340,
                  accent: const Color(0xFF027A48),
                ),
              ],
            ),
            if (deadlines.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text(
                'Key Dates',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: deadlines.map((deadline) => _DeadlineChip(deadline: deadline)).toList(),
              ),
            ],
            if (documentsToBring.isNotEmpty || questionsToAsk.isNotEmpty) ...[
              const SizedBox(height: 16),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isNarrow = constraints.maxWidth < 760;
                  if (isNarrow) {
                    return Column(
                      children: [
                        _SectionTile(
                          title: 'Documents To Bring',
                          icon: Icons.folder_open_outlined,
                          items: documentsToBring,
                          width: constraints.maxWidth,
                          accent: const Color(0xFF175CD3),
                        ),
                        const SizedBox(height: 12),
                        _SectionTile(
                          title: 'Questions To Ask',
                          icon: Icons.record_voice_over_outlined,
                          items: questionsToAsk,
                          width: constraints.maxWidth,
                          accent: const Color(0xFF7A5AF8),
                        ),
                      ],
                    );
                  }

                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: _SectionTile(
                          title: 'Documents To Bring',
                          icon: Icons.folder_open_outlined,
                          items: documentsToBring,
                          width: double.infinity,
                          accent: const Color(0xFF175CD3),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _SectionTile(
                          title: 'Questions To Ask',
                          icon: Icons.record_voice_over_outlined,
                          items: questionsToAsk,
                          width: double.infinity,
                          accent: const Color(0xFF7A5AF8),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ScorePill extends StatelessWidget {
  final int score;
  final String label;
  final Color accentColor;

  const _ScorePill({
    required this.score,
    required this.label,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: accentColor.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            '$score%',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: accentColor,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: accentColor,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTile extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<String> items;
  final double width;
  final Color accent;

  const _SectionTile({
    required this.title,
    required this.icon,
    required this.items,
    required this.width,
    this.accent = const Color(0xFF344054),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: accent),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (items.isEmpty)
            Text(
              'No items available yet.',
              style: TextStyle(color: Colors.grey.shade600),
            )
          else
            ...items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      margin: const EdgeInsets.only(top: 7),
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: accent,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(item, style: const TextStyle(height: 1.35)),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _DeadlineChip extends StatelessWidget {
  final Map<String, dynamic> deadline;

  const _DeadlineChip({required this.deadline});

  @override
  Widget build(BuildContext context) {
    final status = (deadline['status'] ?? 'future').toString();
    final daysUntil = _asInt(deadline['days_until']);
    final statusMeta = _deadlineMeta(status);

    String secondaryText;
    if (daysUntil < 0) {
      secondaryText = '${daysUntil.abs()} days late';
    } else if (daysUntil == 0) {
      secondaryText = 'Today';
    } else {
      secondaryText = 'In $daysUntil days';
    }

    return Container(
      constraints: const BoxConstraints(maxWidth: 320),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: statusMeta.$2,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            (deadline['title'] ?? '').toString(),
            style: TextStyle(
              fontWeight: FontWeight.w700,
              color: statusMeta.$1,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${deadline['date']} • $secondaryText',
            style: TextStyle(color: statusMeta.$1),
          ),
        ],
      ),
    );
  }
}

List<String> _asStringList(dynamic value) {
  if (value is List) {
    return value.map((item) => item.toString().trim()).where((item) => item.isNotEmpty).toList();
  }
  if (value is String && value.trim().isNotEmpty) {
    return [value.trim()];
  }
  return const [];
}

List<Map<String, dynamic>> _asDeadlineList(dynamic value) {
  if (value is! List) {
    return const [];
  }
  return value.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
}

int _asInt(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is double) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

(Color, Color) _deadlineMeta(String status) {
  switch (status) {
    case 'overdue':
      return (const Color(0xFFB42318), const Color(0xFFFEF3F2));
    case 'upcoming':
      return (const Color(0xFFB54708), const Color(0xFFFFF6ED));
    default:
      return (const Color(0xFF175CD3), const Color(0xFFEFF8FF));
  }
}