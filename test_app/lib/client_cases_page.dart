import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'case_workspace_page.dart';
import 'config.dart';

class CreateCasePage extends StatefulWidget {
  final String? initialTitle;
  final String? initialDescription;
  final String? initialCity;
  final String? initialLegalArea;
  final String? initialIssueType;
  final String? initialUrgency;
  final String? initialAiSummary;
  final Map<String, dynamic>? initialCaseBrief;

  const CreateCasePage({
    super.key,
    this.initialTitle,
    this.initialDescription,
    this.initialCity,
    this.initialLegalArea,
    this.initialIssueType,
    this.initialUrgency,
    this.initialAiSummary,
    this.initialCaseBrief,
  });

  @override
  State<CreateCasePage> createState() => _CreateCasePageState();
}

class _CreateCasePageState extends State<CreateCasePage> {
  final titleController = TextEditingController();
  final descriptionController = TextEditingController();
  final legalAreaController = TextEditingController();
  final issueTypeController = TextEditingController();
  final cityController = TextEditingController();

  bool isPublic = true;
  bool isSubmitting = false;
  String aiSummary = '';
  String legalArea = '';
  String issueType = '';
  String urgency = 'Medium';
  int? createdCaseId;
  Map<String, dynamic> caseBrief = {};
  Map<String, dynamic> analysis = {};
  List<dynamic> suggestions = [];

  @override
  void initState() {
    super.initState();
    titleController.text = widget.initialTitle ?? '';
    descriptionController.text = widget.initialDescription ?? '';
    cityController.text = widget.initialCity ?? '';
    legalArea = widget.initialLegalArea ?? '';
    issueType = widget.initialIssueType ?? '';
    legalAreaController.text = legalArea;
    issueTypeController.text = issueType;
    aiSummary = widget.initialAiSummary ?? '';
    caseBrief = Map<String, dynamic>.from(widget.initialCaseBrief ?? <String, dynamic>{});
    final initialUrgency = (widget.initialUrgency ?? 'Medium').trim();
    urgency = const ['Low', 'Medium', 'High'].contains(initialUrgency)
        ? initialUrgency
        : 'Medium';
  }

  @override
  void dispose() {
    titleController.dispose();
    descriptionController.dispose();
    legalAreaController.dispose();
    issueTypeController.dispose();
    cityController.dispose();
    super.dispose();
  }

  Future<void> _submitCase() async {
    final title = titleController.text.trim();
    final description = descriptionController.text.trim();
    legalArea = legalAreaController.text.trim();
    issueType = issueTypeController.text.trim();
    final city = cityController.text.trim();

    if (title.isEmpty || description.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Title and description are required.')),
      );
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt('user_id');
    if (userId == null) return;

    setState(() => isSubmitting = true);

    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/cases/create'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'client_id': userId,
        'title': title,
        'description': description,
        'legal_area': legalArea,
        'issue_type': issueType,
        'ai_summary': aiSummary,
        'urgency': urgency,
        'city': city,
        'case_brief': caseBrief,
        'publish_publicly': isPublic,
      }),
    );

    if (!mounted) return;

    setState(() => isSubmitting = false);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (data['success'] == true) {
        setState(() {
          createdCaseId = data['case_id'] as int?;
          aiSummary = data['ai_summary']?.toString() ?? '';
          legalArea = data['legal_area']?.toString() ?? '';
          issueType = data['issue_type']?.toString() ?? '';
          urgency = data['urgency']?.toString() ?? urgency;
          suggestions = data['suggested_lawyers'] as List<dynamic>? ?? <dynamic>[];
          caseBrief = Map<String, dynamic>.from(data['case_brief'] as Map? ?? <String, dynamic>{});
          analysis = Map<String, dynamic>.from(data['analysis'] as Map? ?? <String, dynamic>{});
          legalAreaController.text = legalArea;
          issueTypeController.text = issueType;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Case created successfully.')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['message']?.toString() ?? 'Failed to create case.')),
        );
      }
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Failed to create case.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create Case')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Describe your legal issue',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 14),
                      TextField(
                        controller: titleController,
                        decoration: const InputDecoration(
                          labelText: 'Case title',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: descriptionController,
                        maxLines: 6,
                        decoration: const InputDecoration(
                          labelText: 'Case description',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: legalAreaController,
                        onChanged: (value) => legalArea = value.trim(),
                        decoration: const InputDecoration(
                          labelText: 'Legal area',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: issueTypeController,
                        onChanged: (value) => issueType = value.trim(),
                        decoration: const InputDecoration(
                          labelText: 'Issue type',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: urgency,
                        decoration: const InputDecoration(
                          labelText: 'Urgency',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'Low', child: Text('Low')),
                          DropdownMenuItem(value: 'Medium', child: Text('Medium')),
                          DropdownMenuItem(value: 'High', child: Text('High')),
                        ],
                        onChanged: (value) {
                          if (value == null) return;
                          urgency = value;
                        },
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: cityController,
                        decoration: const InputDecoration(
                          labelText: 'City',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 10),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Publish this case publicly'),
                        subtitle: const Text('Marketplace discovery works best for public cases.'),
                        value: isPublic,
                        onChanged: (value) => setState(() => isPublic = value),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: isSubmitting ? null : _submitCase,
                              icon: const Icon(Icons.send),
                              label: Text(isSubmitting ? 'Submitting...' : 'Create Case'),
                            ),
                          ),
                          if (createdCaseId != null) ...[
                            const SizedBox(width: 10),
                            OutlinedButton.icon(
                              onPressed: () async {
                                final navigator = Navigator.of(context);
                                final prefs = await SharedPreferences.getInstance();
                                final userId = prefs.getInt('user_id');
                                if (!mounted || userId == null) return;
                                await navigator.push(
                                  MaterialPageRoute(
                                    builder: (_) => CaseWorkspacePage(
                                      caseId: createdCaseId!,
                                      currentUserId: userId,
                                    ),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.chat_bubble_outline),
                              label: const Text('Open Workspace'),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              if (aiSummary.isNotEmpty || legalArea.isNotEmpty) ...[
                const SizedBox(height: 14),
                _AnalysisCard(
                  aiSummary: aiSummary,
                  legalArea: legalArea,
                  issueType: issueType,
                  urgency: urgency,
                  analysis: analysis,
                ),
              ],
              if (caseBrief.isNotEmpty) ...[
                const SizedBox(height: 14),
                _CaseBriefCard(caseBrief: caseBrief),
              ],
              if (suggestions.isNotEmpty) ...[
                const SizedBox(height: 14),
                const Text(
                  'Suggested Lawyers',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                ...suggestions.map(
                  (item) => _SuggestedLawyerCard(item: item as Map<String, dynamic>),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class MyCasesPage extends StatefulWidget {
  const MyCasesPage({super.key});

  @override
  State<MyCasesPage> createState() => _MyCasesPageState();
}

class _MyCasesPageState extends State<MyCasesPage> {
  bool isLoading = true;
  int? currentUserId;
  List<dynamic> cases = [];

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt('user_id');
    if (userId == null) return;

    final response = await http.get(Uri.parse('${ApiConfig.baseUrl}/cases/client/$userId'));
    if (!mounted) return;

    if (response.statusCode == 200) {
      setState(() {
        currentUserId = userId;
        cases = jsonDecode(response.body) as List<dynamic>;
        isLoading = false;
      });
    } else {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Cases')),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: cases.length,
              itemBuilder: (context, index) {
                final c = cases[index] as Map<String, dynamic>;
                final brief = Map<String, dynamic>.from(
                  c['case_brief'] as Map? ?? <String, dynamic>{},
                );
                return Card(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  child: ListTile(
                    leading: const Icon(Icons.folder_open),
                    title: Text(c['title']?.toString() ?? ''),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text(
                          '${c['legal_area'] ?? 'General Legal'} • ${c['city'] ?? ''} • ${c['status'] ?? ''}',
                        ),
                        if ((brief['case_summary']?.toString() ?? '').isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            brief['case_summary']?.toString() ?? '',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ],
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: currentUserId == null
                        ? null
                        : () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => CaseWorkspacePage(
                                  caseId: c['case_id'] as int,
                                  currentUserId: currentUserId!,
                                ),
                              ),
                            );
                          },
                  ),
                );
              },
            ),
    );
  }
}

class RecommendedLawyersPage extends StatefulWidget {
  final List<dynamic>? initialLawyers;

  const RecommendedLawyersPage({super.key, this.initialLawyers});

  @override
  State<RecommendedLawyersPage> createState() => _RecommendedLawyersPageState();
}

class _RecommendedLawyersPageState extends State<RecommendedLawyersPage> {
  bool isLoading = true;
  List<dynamic> lawyers = [];

  @override
  void initState() {
    super.initState();
    if (widget.initialLawyers != null && widget.initialLawyers!.isNotEmpty) {
      lawyers = widget.initialLawyers!;
      isLoading = false;
      return;
    }
    _loadLawyers();
  }

  Future<void> _loadLawyers() async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt('user_id');
    if (userId == null) return;

    final response = await http.get(Uri.parse('${ApiConfig.baseUrl}/professionals/$userId'));

    if (!mounted) return;

    if (response.statusCode == 200) {
      setState(() {
        lawyers = jsonDecode(response.body) as List<dynamic>;
        isLoading = false;
      });
    } else {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Recommended Lawyers')),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : GridView.builder(
              padding: const EdgeInsets.all(16),
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 380,
                mainAxisExtent: 210,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: lawyers.length,
              itemBuilder: (context, index) {
                final lawyer = lawyers[index] as Map<String, dynamic>;
                return _SuggestedLawyerCard(item: lawyer);
              },
            ),
    );
  }
}

class _AnalysisCard extends StatelessWidget {
  final String aiSummary;
  final String legalArea;
  final String issueType;
  final String urgency;
  final Map<String, dynamic> analysis;

  const _AnalysisCard({
    required this.aiSummary,
    required this.legalArea,
    required this.issueType,
    required this.urgency,
    required this.analysis,
  });

  @override
  Widget build(BuildContext context) {
    final reasoning = analysis['reasoning']?.toString() ?? '';
    final action = analysis['recommended_action']?.toString() ?? '';
    final confidence = analysis['confidence_level']?.toString() ?? 'Medium';
    final disclaimer = analysis['disclaimer']?.toString() ??
        'AdvocateAI provides informational support and not formal legal advice.';

    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'AI Case Summary',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _Pill(text: 'Legal area: ${legalArea.isEmpty ? 'N/A' : legalArea}'),
                _Pill(text: 'Issue type: ${issueType.isEmpty ? 'N/A' : issueType}'),
                _Pill(text: 'Urgency: $urgency'),
                _Pill(text: 'Confidence: $confidence'),
              ],
            ),
            const SizedBox(height: 12),
            Text(aiSummary),
            if (reasoning.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text('Reasoning: $reasoning'),
            ],
            if (action.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Recommended action: $action'),
            ],
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF6D8),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(disclaimer),
            ),
          ],
        ),
      ),
    );
  }
}

class _CaseBriefCard extends StatelessWidget {
  final Map<String, dynamic> caseBrief;

  const _CaseBriefCard({required this.caseBrief});

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Structured Case Brief',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
            ),
            const SizedBox(height: 12),
            _BriefGroup(title: 'Summary', values: [caseBrief['case_summary']?.toString() ?? '']),
            _BriefGroup(title: 'Key Entities', values: _readList(caseBrief['key_entities'])),
            _BriefGroup(title: 'Timeline', values: _readList(caseBrief['timeline'])),
            _BriefGroup(title: 'Documents', values: _readList(caseBrief['documents'])),
            _BriefGroup(
              title: 'Recommended Next Steps',
              values: _readList(caseBrief['recommended_next_steps']),
            ),
          ],
        ),
      ),
    );
  }
}

class _BriefGroup extends StatelessWidget {
  final String title;
  final List<String> values;

  const _BriefGroup({required this.title, required this.values});

  @override
  Widget build(BuildContext context) {
    final items = values.where((item) => item.trim().isNotEmpty).toList();
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text('• $item'),
            ),
          ),
        ],
      ),
    );
  }
}

class _SuggestedLawyerCard extends StatelessWidget {
  final Map<String, dynamic> item;

  const _SuggestedLawyerCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final reasons = _readList(item['match_reason']);
    final rawMatchScore = item['match_score'] ?? item['score'];
    final matchScore = rawMatchScore is num ? rawMatchScore.toDouble() : null;
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const CircleAvatar(child: Icon(Icons.gavel)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item['name']?.toString() ?? '',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      const SizedBox(height: 4),
                      Text('${item['city'] ?? ''} • Rating ${item['rating'] ?? '-'}'),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (matchScore != null) _Pill(text: 'Match ${matchScore.toStringAsFixed(2)}'),
                if ((item['availability_status']?.toString() ?? '').isNotEmpty)
                  _Pill(text: 'Status ${item['availability_status']}'),
                if (item['responsiveness_score'] != null)
                  _Pill(text: 'Responsiveness ${item['responsiveness_score']}'),
              ],
            ),
            if (reasons.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text('Matched because', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 6),
              ...reasons.map(
                (reason) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $reason'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  final String text;

  const _Pill({required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F6FD),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(text),
    );
  }
}

List<String> _readList(dynamic raw) {
  if (raw is List) {
    return raw.map((item) => item.toString()).where((item) => item.trim().isNotEmpty).toList();
  }
  if (raw is String && raw.trim().isNotEmpty) {
    return [raw.trim()];
  }
  return <String>[];
}