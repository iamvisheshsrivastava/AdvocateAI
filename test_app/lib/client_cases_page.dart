import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';

class CreateCasePage extends StatefulWidget {
  final String? initialTitle;
  final String? initialDescription;
  final String? initialCity;
  final String? initialLegalArea;
  final String? initialIssueType;
  final String? initialUrgency;
  final String? initialAiSummary;

  const CreateCasePage({
    super.key,
    this.initialTitle,
    this.initialDescription,
    this.initialCity,
    this.initialLegalArea,
    this.initialIssueType,
    this.initialUrgency,
    this.initialAiSummary,
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
        'publish_publicly': isPublic,
      }),
    );

    if (!mounted) return;

    setState(() => isSubmitting = false);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['success'] == true) {
        setState(() {
          aiSummary = data['ai_summary'] ?? '';
          legalArea = data['legal_area'] ?? '';
          issueType = data['issue_type'] ?? '';
          urgency = data['urgency'] ?? urgency;
          suggestions = data['suggested_lawyers'] ?? [];
          legalAreaController.text = legalArea;
          issueTypeController.text = issueType;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Case created successfully.')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['message'] ?? 'Failed to create case.')),
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
          constraints: const BoxConstraints(maxWidth: 900),
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                child: Padding(
                  padding: const EdgeInsets.all(18),
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
                        value: isPublic,
                        onChanged: (value) => setState(() => isPublic = value),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: isSubmitting ? null : _submitCase,
                          icon: const Icon(Icons.send),
                          label: Text(isSubmitting ? 'Submitting...' : 'Create Case'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (aiSummary.isNotEmpty || legalArea.isNotEmpty) ...[
                const SizedBox(height: 14),
                Card(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('AI Case Summary', style: TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        Text('Legal area: ${legalArea.isEmpty ? 'N/A' : legalArea}'),
                        const SizedBox(height: 6),
                        Text('Issue type: ${issueType.isEmpty ? 'N/A' : issueType}'),
                        const SizedBox(height: 6),
                        Text('Urgency: $urgency'),
                        const SizedBox(height: 6),
                        Text(aiSummary),
                      ],
                    ),
                  ),
                ),
              ],
              if (suggestions.isNotEmpty) ...[
                const SizedBox(height: 14),
                const Text('Suggested Lawyers', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                ...suggestions.map((item) => Card(
                      child: ListTile(
                        leading: const Icon(Icons.gavel),
                        title: Text(item['name']?.toString() ?? ''),
                        subtitle: Text('${item['city'] ?? ''} • Rating ${item['rating'] ?? '-'}'),
                      ),
                    )),
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
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.folder_open),
                    title: Text(c['title']?.toString() ?? ''),
                    subtitle: Text(
                      '${c['legal_area'] ?? 'General Legal'} • ${c['city'] ?? ''} • ${c['status'] ?? ''}',
                    ),
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
                maxCrossAxisExtent: 360,
                mainAxisExtent: 120,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: lawyers.length,
              itemBuilder: (context, index) {
                final lawyer = lawyers[index] as Map<String, dynamic>;
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.gavel, color: Colors.blue),
                    title: Text(lawyer['name']?.toString() ?? ''),
                    subtitle: Text(
                      '${lawyer['city'] ?? ''} • Rating ${lawyer['rating'] ?? '-'}',
                    ),
                  ),
                );
              },
            ),
    );
  }
}
