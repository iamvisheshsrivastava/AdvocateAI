import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';
import 'login_page.dart';

class LawyerDashboardPage extends StatelessWidget {
  const LawyerDashboardPage({super.key});

  Future<int?> _loadLawyerId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt('user_id');
  }

  Future<void> _logout(BuildContext context) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (!context.mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => LoginPage()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<int?>(
      future: _loadLawyerId(),
      builder: (context, snapshot) {
        final lawyerId = snapshot.data;
        if (lawyerId == null) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }

        return Scaffold(
          appBar: AppBar(
            title: const Text('Lawyer Dashboard'),
            actions: [
              TextButton.icon(
                onPressed: () => _logout(context),
                icon: const Icon(Icons.logout),
                label: const Text('Logout'),
              ),
            ],
          ),
          body: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1000),
              child: GridView.count(
                padding: const EdgeInsets.all(20),
                crossAxisCount: MediaQuery.of(context).size.width < 900 ? 1 : 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 2.4,
                children: [
                  _NavCard(
                    icon: Icons.person,
                    title: 'Lawyer Profile',
                    subtitle: 'Create or update your public profile',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => LawyerProfilePage(lawyerId: lawyerId),
                      ),
                    ),
                  ),
                  _NavCard(
                    icon: Icons.folder_open,
                    title: 'Open Cases',
                    subtitle: 'Browse all currently open legal cases',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const OpenCasesPage()),
                    ),
                  ),
                  _NavCard(
                    icon: Icons.recommend,
                    title: 'Recommended Cases',
                    subtitle: 'Cases matched to your practice areas',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => RecommendedCasesPage(lawyerId: lawyerId),
                      ),
                    ),
                  ),
                  _NavCard(
                    icon: Icons.mail,
                    title: 'Applications',
                    subtitle: 'Review your submitted applications',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => LawyerApplicationsPage(lawyerId: lawyerId),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _NavCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _NavCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: const Color(0xFFEEF4FF),
                child: Icon(icon, color: const Color(0xFF1E63E9)),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(subtitle),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LawyerProfilePage extends StatefulWidget {
  final int lawyerId;

  const LawyerProfilePage({super.key, required this.lawyerId});

  @override
  State<LawyerProfilePage> createState() => _LawyerProfilePageState();
}

class _LawyerProfilePageState extends State<LawyerProfilePage> {
  final nameController = TextEditingController();
  final cityController = TextEditingController();
  final practiceController = TextEditingController();
  final languagesController = TextEditingController();
  final experienceController = TextEditingController();
  final ratingController = TextEditingController();
  final bioController = TextEditingController();

  bool isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/lawyer/profile/${widget.lawyerId}'),
    );

    if (!mounted || response.statusCode != 200) return;

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (data.isEmpty) return;

    setState(() {
      nameController.text = data['name']?.toString() ?? '';
      cityController.text = data['city']?.toString() ?? '';
      practiceController.text = data['practice_areas']?.toString() ?? '';
      languagesController.text = data['languages']?.toString() ?? '';
      experienceController.text = data['experience_years']?.toString() ?? '';
      ratingController.text = data['rating']?.toString() ?? '';
      bioController.text = data['bio']?.toString() ?? '';
    });
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
        'practice_areas': practiceController.text.trim(),
        'languages': languagesController.text.trim(),
        'experience_years': int.tryParse(experienceController.text.trim()) ?? 0,
        'rating': double.tryParse(ratingController.text.trim()) ?? 0,
        'bio': bioController.text.trim(),
      }),
    );

    if (!mounted) return;

    setState(() => isSaving = false);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(data['success'] == true ? 'Profile saved.' : (data['message'] ?? 'Failed.'))),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Failed to save profile.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Lawyer Profile')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Name')),
                      TextField(controller: cityController, decoration: const InputDecoration(labelText: 'City')),
                      TextField(controller: practiceController, decoration: const InputDecoration(labelText: 'Practice areas (comma separated)')),
                      TextField(controller: languagesController, decoration: const InputDecoration(labelText: 'Languages (comma separated)')),
                      TextField(controller: experienceController, decoration: const InputDecoration(labelText: 'Experience years')),
                      TextField(controller: ratingController, decoration: const InputDecoration(labelText: 'Rating')),
                      TextField(controller: bioController, maxLines: 4, decoration: const InputDecoration(labelText: 'Bio')),
                      const SizedBox(height: 14),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: isSaving ? null : _saveProfile,
                          child: Text(isSaving ? 'Saving...' : 'Save Profile'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class OpenCasesPage extends StatefulWidget {
  const OpenCasesPage({super.key});

  @override
  State<OpenCasesPage> createState() => _OpenCasesPageState();
}

class _OpenCasesPageState extends State<OpenCasesPage> {
  bool isLoading = true;
  List<dynamic> cases = [];

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    final response = await http.get(Uri.parse('${ApiConfig.baseUrl}/cases/open'));
    if (!mounted) return;

    if (response.statusCode == 200) {
      setState(() {
        cases = jsonDecode(response.body) as List<dynamic>;
        isLoading = false;
      });
    } else {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _CaseListScaffold(title: 'Open Cases', isLoading: isLoading, cases: cases);
  }
}

class RecommendedCasesPage extends StatefulWidget {
  final int lawyerId;

  const RecommendedCasesPage({super.key, required this.lawyerId});

  @override
  State<RecommendedCasesPage> createState() => _RecommendedCasesPageState();
}

class _RecommendedCasesPageState extends State<RecommendedCasesPage> {
  bool isLoading = true;
  List<dynamic> cases = [];

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/cases/recommended/${widget.lawyerId}'),
    );

    if (!mounted) return;

    if (response.statusCode == 200) {
      setState(() {
        cases = jsonDecode(response.body) as List<dynamic>;
        isLoading = false;
      });
    } else {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _CaseListScaffold(
      title: 'Recommended Cases',
      isLoading: isLoading,
      cases: cases,
      showMatchScore: true,
      lawyerId: widget.lawyerId,
    );
  }
}

class LawyerApplicationsPage extends StatefulWidget {
  final int lawyerId;

  const LawyerApplicationsPage({super.key, required this.lawyerId});

  @override
  State<LawyerApplicationsPage> createState() => _LawyerApplicationsPageState();
}

class _LawyerApplicationsPageState extends State<LawyerApplicationsPage> {
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
    } else {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Applications')),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: applications.length,
              itemBuilder: (context, index) {
                final item = applications[index] as Map<String, dynamic>;
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.mark_email_read),
                    title: Text(item['title']?.toString() ?? ''),
                    subtitle: Text(
                      '${item['legal_area'] ?? ''} • ${item['city'] ?? ''}\n${item['message'] ?? ''}',
                    ),
                    isThreeLine: true,
                  ),
                );
              },
            ),
    );
  }
}

class _CaseListScaffold extends StatelessWidget {
  final String title;
  final bool isLoading;
  final List<dynamic> cases;
  final bool showMatchScore;
  final int? lawyerId;

  const _CaseListScaffold({
    required this.title,
    required this.isLoading,
    required this.cases,
    this.showMatchScore = false,
    this.lawyerId,
  });

  Future<void> _applyToCase(BuildContext context, int caseId) async {
    if (lawyerId == null) return;
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
                  'lawyer_id': lawyerId,
                  'message': controller.text.trim(),
                }),
              );

              if (!dialogContext.mounted) return;
              Navigator.pop(dialogContext);

              if (response.statusCode == 200) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Application submitted.')),
                );
              } else {
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
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: cases.length,
              itemBuilder: (context, index) {
                final item = cases[index] as Map<String, dynamic>;
                final score = item['match_score'];

                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item['title']?.toString() ?? '',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                        ),
                        const SizedBox(height: 6),
                        Text(item['description']?.toString() ?? ''),
                        const SizedBox(height: 8),
                        Text(
                          '${item['legal_area'] ?? 'General'} • ${item['city'] ?? ''} • ${item['status'] ?? ''}',
                        ),
                        if (showMatchScore && score != null) ...[
                          const SizedBox(height: 4),
                          Text('Match score: $score'),
                        ],
                        if (lawyerId != null) ...[
                          const SizedBox(height: 10),
                          Align(
                            alignment: Alignment.centerRight,
                            child: ElevatedButton(
                              onPressed: () => _applyToCase(context, item['case_id'] as int),
                              child: const Text('Apply'),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
