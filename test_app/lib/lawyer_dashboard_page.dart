import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'case_workspace_page.dart';
import 'config.dart';
import 'login_page.dart';
import 'notifications_page.dart';

class LawyerDashboardPage extends StatefulWidget {
  const LawyerDashboardPage({super.key});

  @override
  State<LawyerDashboardPage> createState() => _LawyerDashboardPageState();
}

class _LawyerDashboardPageState extends State<LawyerDashboardPage> {
  int? lawyerId;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadLawyer();
  }

  Future<void> _loadLawyer() async {
    final prefs = await SharedPreferences.getInstance();
    final id = prefs.getInt('user_id');
    if (!mounted) return;
    setState(() {
      lawyerId = id;
      isLoading = false;
    });
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => LoginPage()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading || lawyerId == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Lawyer Dashboard'),
        actions: [
          NotificationBellAction(userId: lawyerId!),
          TextButton.icon(
            onPressed: _logout,
            icon: const Icon(Icons.logout),
            label: const Text('Logout'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadLawyer,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _HeroBanner(lawyerId: lawyerId!),
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (context, constraints) {
                final twoColumns = constraints.maxWidth >= 980;
                if (!twoColumns) {
                  return Column(
                    children: [
                      LawyerProfileCard(lawyerId: lawyerId!),
                      const SizedBox(height: 16),
                      OpenCasesCard(lawyerId: lawyerId!),
                      const SizedBox(height: 16),
                      RecommendedCasesCard(lawyerId: lawyerId!),
                      const SizedBox(height: 16),
                      LawyerApplicationsCard(lawyerId: lawyerId!),
                    ],
                  );
                }

                return Column(
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: LawyerProfileCard(lawyerId: lawyerId!)),
                        const SizedBox(width: 16),
                        Expanded(child: OpenCasesCard(lawyerId: lawyerId!)),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: RecommendedCasesCard(lawyerId: lawyerId!)),
                        const SizedBox(width: 16),
                        Expanded(child: LawyerApplicationsCard(lawyerId: lawyerId!)),
                      ],
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroBanner extends StatelessWidget {
  final int lawyerId;

  const _HeroBanner({required this.lawyerId});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0D3B66), Color(0xFF1E63E9)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Manage discovery, applications, and client communication in one place.',
            style: TextStyle(
              color: Colors.white,
              fontSize: 28,
              fontWeight: FontWeight.bold,
              height: 1.15,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Lawyer ID: #$lawyerId',
            style: const TextStyle(color: Colors.white70),
          ),
        ],
      ),
    );
  }
}

class LawyerProfileCard extends StatefulWidget {
  final int lawyerId;

  const LawyerProfileCard({super.key, required this.lawyerId});

  @override
  State<LawyerProfileCard> createState() => _LawyerProfileCardState();
}

class _LawyerProfileCardState extends State<LawyerProfileCard> {
  final nameController = TextEditingController();
  final cityController = TextEditingController();
  final practiceController = TextEditingController();
  final languagesController = TextEditingController();
  final experienceController = TextEditingController();
  final ratingController = TextEditingController();
  final bioController = TextEditingController();

  String availabilityStatus = 'available';
  double responseTimeHours = 0;
  int applicationsSent = 0;
  int casesAccepted = 0;
  double responsivenessScore = 0;
  bool isLoading = true;
  bool isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void dispose() {
    nameController.dispose();
    cityController.dispose();
    practiceController.dispose();
    languagesController.dispose();
    experienceController.dispose();
    ratingController.dispose();
    bioController.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/lawyer/profile/${widget.lawyerId}'),
    );

    if (!mounted) return;

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      setState(() {
        nameController.text = data['name']?.toString() ?? '';
        cityController.text = data['city']?.toString() ?? '';
        practiceController.text = data['practice_areas']?.toString() ?? '';
        languagesController.text = data['languages']?.toString() ?? '';
        experienceController.text = data['experience_years']?.toString() ?? '0';
        ratingController.text = data['rating']?.toString() ?? '0';
        bioController.text = data['bio']?.toString() ?? '';
        availabilityStatus = data['availability_status']?.toString() ?? 'available';
        responseTimeHours = _toDouble(data['response_time_hours']);
        applicationsSent = _toInt(data['applications_sent']);
        casesAccepted = _toInt(data['cases_accepted']);
        responsivenessScore = _toDouble(data['responsiveness_score']);
        isLoading = false;
      });
      return;
    }

    setState(() => isLoading = false);
  }

  Future<void> _saveProfile() async {
    setState(() => isSaving = true);

    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/lawyer/profile'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'lawyer_id': widget.lawyerId,
        'name': nameController.text.trim(),
        'city': cityController.text.trim(),
        'practice_areas': practiceController.text
            .split(',')
            .map((item) => item.trim())
            .where((item) => item.isNotEmpty)
            .toList(),
        'languages': languagesController.text
            .split(',')
            .map((item) => item.trim())
            .where((item) => item.isNotEmpty)
            .toList(),
        'experience_years': int.tryParse(experienceController.text.trim()) ?? 0,
        'rating': double.tryParse(ratingController.text.trim()) ?? 0,
        'bio': bioController.text.trim(),
        'availability_status': availabilityStatus,
      }),
    );

    if (!mounted) return;

    setState(() => isSaving = false);

    if (response.statusCode == 200) {
      await _loadProfile();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile saved.')),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Failed to save profile.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: isLoading
            ? const SizedBox(
                height: 260,
                child: Center(child: CircularProgressIndicator()),
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Profile and Availability',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _MetricPill(label: 'Responsiveness', value: responsivenessScore.toStringAsFixed(2)),
                      _MetricPill(label: 'Avg response', value: '${responseTimeHours.toStringAsFixed(1)}h'),
                      _MetricPill(label: 'Applications', value: '$applicationsSent'),
                      _MetricPill(label: 'Accepted', value: '$casesAccepted'),
                    ],
                  ),
                  const SizedBox(height: 14),
                  TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Name')),
                  TextField(controller: cityController, decoration: const InputDecoration(labelText: 'City')),
                  TextField(
                    controller: practiceController,
                    decoration: const InputDecoration(labelText: 'Practice areas (comma separated)'),
                  ),
                  TextField(
                    controller: languagesController,
                    decoration: const InputDecoration(labelText: 'Languages (comma separated)'),
                  ),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: experienceController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: 'Experience years'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                          controller: ratingController,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: const InputDecoration(labelText: 'Rating'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: availabilityStatus,
                    decoration: const InputDecoration(labelText: 'Availability status'),
                    items: const [
                      DropdownMenuItem(value: 'available', child: Text('Available')),
                      DropdownMenuItem(value: 'busy', child: Text('Busy')),
                      DropdownMenuItem(value: 'not accepting cases', child: Text('Not accepting cases')),
                    ],
                    onChanged: (value) {
                      if (value == null) return;
                      setState(() => availabilityStatus = value);
                    },
                  ),
                  TextField(
                    controller: bioController,
                    maxLines: 4,
                    decoration: const InputDecoration(labelText: 'Bio'),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: isSaving ? null : _saveProfile,
                      icon: const Icon(Icons.save_outlined),
                      label: Text(isSaving ? 'Saving...' : 'Save Profile'),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class OpenCasesCard extends StatelessWidget {
  final int lawyerId;

  const OpenCasesCard({super.key, required this.lawyerId});

  @override
  Widget build(BuildContext context) {
    return _CaseFeedCard(
      title: 'Open Cases',
      endpoint: '${ApiConfig.baseUrl}/cases/open',
      lawyerId: lawyerId,
      emptyMessage: 'No open marketplace cases right now.',
    );
  }
}

class RecommendedCasesCard extends StatelessWidget {
  final int lawyerId;

  const RecommendedCasesCard({super.key, required this.lawyerId});

  @override
  Widget build(BuildContext context) {
    return _CaseFeedCard(
      title: 'Recommended Cases',
      endpoint: '${ApiConfig.baseUrl}/cases/recommended/$lawyerId',
      lawyerId: lawyerId,
      emptyMessage: 'Recommendations will appear after your profile is complete.',
      showMatchReasons: true,
    );
  }
}

class _CaseFeedCard extends StatefulWidget {
  final String title;
  final String endpoint;
  final int lawyerId;
  final String emptyMessage;
  final bool showMatchReasons;

  const _CaseFeedCard({
    required this.title,
    required this.endpoint,
    required this.lawyerId,
    required this.emptyMessage,
    this.showMatchReasons = false,
  });

  @override
  State<_CaseFeedCard> createState() => _CaseFeedCardState();
}

class _CaseFeedCardState extends State<_CaseFeedCard> {
  bool isLoading = true;
  List<dynamic> cases = [];

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    final response = await http.get(Uri.parse(widget.endpoint));
    if (!mounted) return;
    if (response.statusCode == 200) {
      setState(() {
        cases = jsonDecode(response.body) as List<dynamic>;
        isLoading = false;
      });
      return;
    }
    setState(() => isLoading = false);
  }

  Future<void> _applyToCase(int caseId) async {
    final controller = TextEditingController();
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Apply to case'),
        content: TextField(
          controller: controller,
          maxLines: 4,
          decoration: const InputDecoration(
            hintText: 'Consultation message',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final response = await http.post(
                Uri.parse('${ApiConfig.baseUrl}/cases/apply'),
                headers: {'Content-Type': 'application/json'},
                body: jsonEncode({
                  'case_id': caseId,
                  'lawyer_id': widget.lawyerId,
                  'message': controller.text.trim(),
                }),
              );

              if (!dialogContext.mounted) return;
              Navigator.pop(dialogContext);

              if (response.statusCode == 200) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Application submitted.')),
                );
                _loadCases();
              } else {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Failed to submit application.')),
                );
              }
            },
            child: const Text('Submit'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(widget.title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                const Spacer(),
                IconButton(onPressed: _loadCases, icon: const Icon(Icons.refresh)),
              ],
            ),
            const SizedBox(height: 10),
            if (isLoading)
              const SizedBox(height: 220, child: Center(child: CircularProgressIndicator()))
            else if (cases.isEmpty)
              SizedBox(height: 180, child: Center(child: Text(widget.emptyMessage)))
            else
              ...cases.take(4).map((item) {
                final caseItem = item as Map<String, dynamic>;
                final reasons = _stringList(caseItem['match_reason']);
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFE4E8F0)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        caseItem['title']?.toString() ?? '',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      const SizedBox(height: 6),
                      Text(caseItem['description']?.toString() ?? ''),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _MetricPill(label: 'Area', value: caseItem['legal_area']?.toString() ?? 'General'),
                          _MetricPill(label: 'City', value: caseItem['city']?.toString() ?? 'Unknown'),
                          _MetricPill(label: 'Status', value: caseItem['status']?.toString() ?? 'Open'),
                          if (caseItem['match_score'] != null)
                            _MetricPill(label: 'Match', value: _toDouble(caseItem['match_score']).toStringAsFixed(2)),
                        ],
                      ),
                      if (widget.showMatchReasons && reasons.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        const Text('Why this case matches', style: TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 6),
                        ...reasons.map((reason) => Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Text('• $reason'),
                            )),
                      ],
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: [
                          ElevatedButton.icon(
                            onPressed: () => _applyToCase(caseItem['case_id'] as int),
                            icon: const Icon(Icons.assignment_turned_in_outlined),
                            label: const Text('Apply'),
                          ),
                          OutlinedButton.icon(
                            onPressed: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => CaseWorkspacePage(
                                    caseId: caseItem['case_id'] as int,
                                    currentUserId: widget.lawyerId,
                                  ),
                                ),
                              );
                            },
                            icon: const Icon(Icons.chat_bubble_outline),
                            label: const Text('Open Workspace'),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

class LawyerApplicationsCard extends StatefulWidget {
  final int lawyerId;

  const LawyerApplicationsCard({super.key, required this.lawyerId});

  @override
  State<LawyerApplicationsCard> createState() => _LawyerApplicationsCardState();
}

class _LawyerApplicationsCardState extends State<LawyerApplicationsCard> {
  bool isLoading = true;
  List<dynamic> applications = [];

  @override
  void initState() {
    super.initState();
    _loadApplications();
  }

  Future<void> _loadApplications() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/cases/applications/${widget.lawyerId}'),
    );

    if (!mounted) return;

    if (response.statusCode == 200) {
      setState(() {
        applications = jsonDecode(response.body) as List<dynamic>;
        isLoading = false;
      });
      return;
    }

    setState(() => isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('My Applications', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                const Spacer(),
                IconButton(onPressed: _loadApplications, icon: const Icon(Icons.refresh)),
              ],
            ),
            const SizedBox(height: 10),
            if (isLoading)
              const SizedBox(height: 220, child: Center(child: CircularProgressIndicator()))
            else if (applications.isEmpty)
              const SizedBox(height: 180, child: Center(child: Text('No applications submitted yet.')))
            else
              ...applications.take(5).map((item) {
                final application = item as Map<String, dynamic>;
                return ListTile(
                  contentPadding: const EdgeInsets.symmetric(vertical: 6),
                  leading: const CircleAvatar(child: Icon(Icons.mail_outline)),
                  title: Text(application['title']?.toString() ?? ''),
                  subtitle: Text(
                    '${application['legal_area'] ?? ''} • ${application['city'] ?? ''}\n${application['message'] ?? ''}',
                  ),
                  isThreeLine: true,
                );
              }),
          ],
        ),
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  final String label;
  final String value;

  const _MetricPill({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F6FD),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text('$label: $value'),
    );
  }
}

double _toDouble(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '0') ?? 0;
}

int _toInt(dynamic value) {
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '0') ?? 0;
}

List<String> _stringList(dynamic raw) {
  if (raw is List) {
    return raw.map((item) => item.toString()).where((item) => item.trim().isNotEmpty).toList();
  }
  if (raw is String && raw.trim().isNotEmpty) {
    return [raw.trim()];
  }
  return <String>[];
}