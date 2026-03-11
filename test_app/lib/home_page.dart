import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'case_intelligence_card.dart';
import 'watchlist_page.dart';
import 'notifications_page.dart';
import 'config.dart';
import 'login_page.dart';
import 'premium_page.dart';
import 'client_cases_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  final TextEditingController messageController = TextEditingController();
  final ScrollController scrollController = ScrollController();

  String userEmail = "";
  int? userId;
  bool isTyping = false;
  List<Map<String, String>> messages = [];
  Map<String, dynamic>? latestCaseAnalysis;
  Map<String, dynamic>? latestCaseIntelligence;
  Map<String, dynamic>? latestLegalActionGuide;
  List<dynamic> latestSuggestedLawyers = [];
  String lastUserProblem = "";
  bool showCaseAnalysis = false;
  bool isUploadingDocument = false;
  Map<String, dynamic>? latestDocumentAnalysis;
  Map<String, dynamic>? latestDocumentIntelligence;
  List<dynamic> latestDocumentRecommendedLawyers = [];
  List<_PendingUpload> pendingUploads = [];

  final ImagePicker imagePicker = ImagePicker();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _validateSessionAndLoadUser();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    messageController.dispose();
    scrollController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _enforceSessionTimeout();
    }
  }

  void scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (scrollController.hasClients) {
        scrollController.animateTo(
          scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> loadUser() async {
    final prefs = await SharedPreferences.getInstance();
    final email = prefs.getString("user_email") ?? "User";
    final id = prefs.getInt("user_id");

    if (id == null) {
      await logout();
      return;
    }

    if (!mounted) return;

    setState(() {
      userEmail = email;
      userId = id;
      messages.add({
        "role": "assistant",
        "text": "Hi $userEmail, how can I help you today?"
      });
    });
  }

  Future<void> _validateSessionAndLoadUser() async {
    final sessionExpired = await _isSessionExpired();
    if (sessionExpired) {
      await logout();
      return;
    }

    await loadUser();
  }

  Future<void> _enforceSessionTimeout() async {
    final sessionExpired = await _isSessionExpired();
    if (sessionExpired) {
      await logout();
    }
  }

  Future<bool> _isSessionExpired() async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt("user_id");
    final expiresAt = prefs.getInt("session_expires_at");

    if (userId == null || expiresAt == null) {
      return true;
    }

    return DateTime.now().millisecondsSinceEpoch >= expiresAt;
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();

    if (!mounted) return;

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => LoginPage()),
      (route) => false,
    );
  }

  Future<void> sendMessage({String? presetText}) async {
    final text = presetText ?? messageController.text.trim();
    if (text.isEmpty) return;

    lastUserProblem = text;

    setState(() {
      messages.add({"role": "user", "text": text});
      isTyping = true;
    });

    scrollToBottom();
    messageController.clear();

    final url = Uri.parse("${ApiConfig.baseUrl}/chat");

    final response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"message": text, "user_id": userId}),
    );

    String reply = "Error getting response";

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      reply = (data["response"] ?? "Error getting response").toString();
      latestLegalActionGuide = await _fetchLegalActionGuide(text);

      final analysis = data["analysis"];
      if (analysis is Map<String, dynamic>) {
        final intelligence = data["case_intelligence"];
        final canPostCase = data["can_post_case"] == true;
        if (canPostCase) {
          latestCaseAnalysis = analysis;
          latestCaseIntelligence = intelligence is Map<String, dynamic> ? intelligence : null;
          showCaseAnalysis = true;
        } else {
          latestCaseAnalysis = null;
          latestCaseIntelligence = null;
          showCaseAnalysis = false;
        }
      } else {
        latestCaseAnalysis = null;
        latestCaseIntelligence = null;
        showCaseAnalysis = false;
      }

      final suggestedLawyers = data["suggested_lawyers"];
      if (suggestedLawyers is List) {
        latestSuggestedLawyers = suggestedLawyers;
      } else {
        latestSuggestedLawyers = [];
      }
    } else {
      latestLegalActionGuide = await _fetchLegalActionGuide(text);
    }

    setState(() {
      isTyping = false;
      messages.add({"role": "assistant", "text": reply});
    });

    scrollToBottom();
  }

  Future<Map<String, dynamic>?> _fetchLegalActionGuide(String problemDescription) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/legal-action-guide'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'problem_description': problemDescription}),
    );
    if (response.statusCode != 200) {
      return null;
    }
    final data = jsonDecode(response.body);
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  Future<void> _openOfficialPortal(String portal) async {
    final uri = Uri.tryParse(portal);
    if (uri == null) {
      return;
    }
    final opened = await launchUrl(uri, mode: LaunchMode.platformDefault);
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not open the official portal.')),
      );
    }
  }

  Future<void> _pickDocumentFiles() async {
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'jpg', 'jpeg', 'png'],
      allowMultiple: true,
      withData: true,
    );

    if (picked == null || picked.files.isEmpty) return;

    final nextUploads = <_PendingUpload>[];
    for (final file in picked.files) {
      if ((file.bytes == null || file.bytes!.isEmpty) && (file.path == null || file.path!.isEmpty)) {
        continue;
      }
      nextUploads.add(
        _PendingUpload(
          name: file.name,
          bytes: file.bytes,
          path: file.path,
          mimeType: _guessMimeType(file.name),
        ),
      );
    }

    if (nextUploads.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not read selected files.')),
      );
      return;
    }

    setState(() {
      pendingUploads = nextUploads;
    });
  }

  Future<void> _captureWithCamera() async {
    if (kIsWeb) {
      await _pickDocumentFiles();
      return;
    }

    final picked = await imagePicker.pickImage(
      source: ImageSource.camera,
      imageQuality: 85,
    );
    if (picked == null) return;

    final bytes = await picked.readAsBytes();
    if (!mounted) return;
    setState(() {
      pendingUploads = [
        ...pendingUploads,
        _PendingUpload(
          name: picked.name,
          bytes: bytes,
          mimeType: _guessMimeType(picked.name),
        ),
      ];
    });
  }

  Future<void> _uploadAndAnalyzeDocument() async {
    if (pendingUploads.isEmpty) {
      await _pickDocumentFiles();
      if (pendingUploads.isEmpty) return;
    }

    setState(() {
      isUploadingDocument = true;
    });

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${ApiConfig.baseUrl}/documents/analyze'),
      );
      if (userId != null) {
        request.fields['user_id'] = '$userId';
      }

      for (int index = 0; index < pendingUploads.length; index++) {
        final file = pendingUploads[index];
        if (file.bytes != null && file.bytes!.isNotEmpty) {
          request.files.add(
            http.MultipartFile.fromBytes(
              index == 0 ? 'file' : 'files',
              file.bytes!,
              filename: file.name,
            ),
          );
        } else if (file.path != null) {
          request.files.add(
            await http.MultipartFile.fromPath(index == 0 ? 'file' : 'files', file.path!),
          );
        }
      }

      final streamed = await request.send();
      final response = await http.Response.fromStream(streamed);

      if (!mounted) return;

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        setState(() {
          latestDocumentAnalysis = {
            'document_type': data['document_type'] ?? 'Unknown',
            'legal_area': data['legal_area'] ?? 'General Legal',
            'key_dates': data['key_dates'] ?? <dynamic>[],
            'summary': data['summary'] ?? '',
            'potential_issue': data['potential_issue'] ?? '',
            'recommended_action': data['recommended_action'] ?? '',
            'confidence_level': data['confidence_level'] ?? 'Medium',
            'citations': data['citations'] ?? <dynamic>[],
            'case_brief': data['case_brief'] ?? <String, dynamic>{},
            'documents': data['documents'] ?? <dynamic>[],
          };
          final intelligence = data['case_intelligence'];
          latestDocumentIntelligence = intelligence is Map<String, dynamic> ? intelligence : null;
          final lawyers = data['recommended_lawyers'];
          latestDocumentRecommendedLawyers = lawyers is List ? lawyers : [];
          pendingUploads = [];
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Document analysis failed.')),
        );
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Error uploading document.')),
      );
    } finally {
      if (mounted) {
        setState(() {
          isUploadingDocument = false;
        });
      }
    }
  }

  void _removePendingUpload(_PendingUpload upload) {
    setState(() {
      pendingUploads = pendingUploads.where((item) => item != upload).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFF7F9FC), Color(0xFFEFF6FB)],
          ),
        ),
        child: SafeArea(
          child: Row(
            children: [
              // Left sidebar
              Container(
                width: 260,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: const BorderRadius.only(
                    topRight: Radius.circular(20),
                    bottomRight: Radius.circular(20),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.05),
                      blurRadius: 12,
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 8),
                    const Text(
                      'AdvocateAI',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E88E5),
                      ),
                    ),
                    const SizedBox(height: 14),
                    ListTile(
                      leading: const Icon(Icons.search_rounded, color: Colors.blue),
                      title: const Text('Quick Find'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {},
                    ),
                    ListTile(
                      leading: const Icon(Icons.post_add, color: Colors.blue),
                      title: const Text('Create Case'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const CreateCasePage(),
                          ),
                        );
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.recommend, color: Colors.blue),
                      title: const Text('Recommended Lawyers'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const RecommendedLawyersPage(),
                          ),
                        );
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.folder_open, color: Colors.blue),
                      title: const Text('My Cases'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const MyCasesPage(),
                          ),
                        );
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.book, color: Colors.blue),
                      title: const Text('WatchList'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {
                        if (userId != null) {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => WatchListPage(userId: userId!),
                            ),
                          );
                        }
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.notifications, color: Colors.blue),
                      title: const Text('Notifications'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {
                        if (userId == null) return;
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => NotificationsPage(userId: userId!),
                          ),
                        );
                      },
                    ),
                    const Spacer(),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => const PremiumPage(),
                            ),
                          );
                        },
                        icon: const Icon(Icons.upgrade),
                        label: const Text('Get Premium'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1E88E5),
                          foregroundColor: Colors.white,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Main content
              Expanded(
                child: Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(40),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 980),
                      child: Container(
                        padding: const EdgeInsets.all(28),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(18),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.06),
                              blurRadius: 20,
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                if (userId != null) NotificationBellAction(userId: userId!),
                                TextButton.icon(
                                  onPressed: logout,
                                  icon: const Icon(Icons.logout),
                                  label: const Text('Logout'),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              'Find exactly what you\'re looking for,\n in seconds.',
                              style: TextStyle(
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                height: 1.12,
                              ),
                            ),
                            const SizedBox(height: 8),
                            TextButton(
                              onPressed: () {},
                              child: const Text('See how it works.'),
                            ),

                            const SizedBox(height: 22),

                            // Action chips
                            Wrap(
                              spacing: 12,
                              runSpacing: 12,
                              children: [
                                _buildActionChip(Icons.description, 'Best criminal lawyer in Berlin'),
                                _buildActionChip(Icons.person_search, 'Top-rated immigration lawyer'),
                                _buildActionChip(Icons.lightbulb, 'English-speaking lawyer in Germany'),
                                _buildActionChip(Icons.email, 'Lawyer with highest reviews in Hamburg'),
                              ],
                            ),

                            if (showCaseAnalysis && latestCaseAnalysis != null) ...[
                              const SizedBox(height: 16),
                              _buildCaseAnalysisCard(context),
                            ],

                            if (showCaseAnalysis && (latestCaseIntelligence?.isNotEmpty ?? false)) ...[
                              const SizedBox(height: 16),
                              CaseIntelligenceCard(
                                data: latestCaseIntelligence!,
                                title: 'Intake Readiness',
                                accentColor: const Color(0xFF155EEF),
                              ),
                            ],

                            if (latestLegalActionGuide != null) ...[
                              const SizedBox(height: 16),
                              _buildLegalActionGuideCard(),
                            ],

                            const SizedBox(height: 16),
                            _buildDocumentCaptureCard(),

                            if (latestDocumentAnalysis != null) ...[
                              const SizedBox(height: 16),
                              _buildDocumentAnalysisCard(context),
                            ],

                            if (latestDocumentIntelligence?.isNotEmpty ?? false) ...[
                              const SizedBox(height: 16),
                              CaseIntelligenceCard(
                                data: latestDocumentIntelligence!,
                                title: 'Document Readiness',
                                accentColor: const Color(0xFF027A48),
                              ),
                            ],

                            SizedBox(
                              height: 300,
                              child: ListView.builder(
                                controller: scrollController,
                                itemCount: messages.length,
                                itemBuilder: (context, index) {
                                  final msg = messages[index];
                                  final isUser = msg["role"] == "user";

                                  return Align(
                                    alignment:
                                        isUser ? Alignment.centerRight : Alignment.centerLeft,
                                    child: Container(
                                      margin: const EdgeInsets.symmetric(vertical: 6),
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: isUser ? Colors.blue : Colors.grey.shade200,
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: MarkdownBody(
                                        data: msg["text"] ?? "",
                                        styleSheet: MarkdownStyleSheet(
                                          p: TextStyle(
                                            color: isUser ? Colors.white : Colors.black,
                                            fontSize: 15,
                                          ),
                                          strong: const TextStyle(fontWeight: FontWeight.bold),
                                          code: const TextStyle(
                                            backgroundColor: Color(0xFFEFEFEF),
                                            fontFamily: 'monospace',
                                          ),
                                          codeblockDecoration: BoxDecoration(
                                            color: const Color(0xFFF4F4F4),
                                            borderRadius: BorderRadius.circular(8),
                                          ),
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),

                            const SizedBox(height: 20),

                            // Central rounded input area
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: Colors.grey.shade200),
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFFFFFF), Color(0xFFF8FBFF)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: messageController,
                                      onSubmitted: (_) => sendMessage(),
                                      decoration: const InputDecoration(
                                        hintText: 'What are you looking for?',
                                        border: InputBorder.none,
                                      ),
                                    ),
                                  ),
                                  IconButton(
                                    onPressed: () {},
                                    icon: const Icon(Icons.mic, color: Colors.blue),
                                  ),
                                  ElevatedButton(
                                    onPressed: sendMessage,
                                    style: ElevatedButton.styleFrom(
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                    ),
                                    child: const Icon(Icons.arrow_forward),
                                  )
                                ],
                              ),
                            ),

                            const SizedBox(height: 18),

                            // small helper chips below
                            Row(
                              children: [
                                ActionChip(
                                  avatar: isUploadingDocument
                                      ? const SizedBox(
                                          width: 14,
                                          height: 14,
                                          child: CircularProgressIndicator(strokeWidth: 2),
                                        )
                                      : const Icon(Icons.attach_file, size: 18),
                                  label: Text(
                                    isUploadingDocument ? 'Analyzing...' : 'Analyze Documents',
                                  ),
                                  onPressed: isUploadingDocument ? null : _uploadAndAnalyzeDocument,
                                ),
                                const SizedBox(width: 8),
                                ActionChip(
                                  avatar: const Icon(Icons.photo_camera_outlined, size: 18),
                                  label: const Text('Camera'),
                                  onPressed: isUploadingDocument ? null : _captureWithCamera,
                                ),
                                const SizedBox(width: 8),
                                ActionChip(
                                  avatar: const Icon(Icons.collections_outlined, size: 18),
                                  label: const Text('Files'),
                                  onPressed: isUploadingDocument ? null : _pickDocumentFiles,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionChip(IconData icon, String label) {
    return ActionChip(
      backgroundColor: const Color(0xFFF3F8FF),
      labelPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: const Color(0xFF1E88E5)),
          const SizedBox(width: 8),
          Text(label),
        ],
      ),
      onPressed: () {
        sendMessage(presetText: label);
      },
    );
  }

  Widget _buildCaseAnalysisCard(BuildContext context) {
    final analysis = latestCaseAnalysis ?? <String, dynamic>{};
    final legalArea = (analysis['legal_area'] ?? 'N/A').toString();
    final issueType = (analysis['issue_type'] ?? 'N/A').toString();
    final location = (analysis['location'] ?? 'Unknown').toString();
    final urgency = (analysis['urgency'] ?? 'Medium').toString();
    final summary = (analysis['summary'] ?? '').toString();
    final confidence = (analysis['confidence_level'] ?? 'Medium').toString();
    final reasoning = (analysis['reasoning'] ?? '').toString();
    final recommendedAction = (analysis['recommended_action'] ?? '').toString();
    final disclaimer = (analysis['disclaimer'] ?? 'AdvocateAI provides informational support and not formal legal advice.').toString();
    final citations = _dynamicListToText(analysis['citations']);
    final caseBrief = Map<String, dynamic>.from(analysis['case_brief'] as Map? ?? <String, dynamic>{});

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: Colors.blue.shade100),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.analytics_outlined, color: Color(0xFF1E88E5)),
                SizedBox(width: 8),
                Text(
                  'Case Analysis',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text('Legal Area: $legalArea'),
            const SizedBox(height: 4),
            Text('Issue Type: $issueType'),
            const SizedBox(height: 4),
            Text('Location: $location'),
            const SizedBox(height: 4),
            Text('Urgency: $urgency'),
            const SizedBox(height: 4),
            Text('Confidence: $confidence'),
            if (summary.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                summary,
                style: const TextStyle(height: 1.35),
              ),
            ],
            if (reasoning.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Reasoning: $reasoning'),
            ],
            if (recommendedAction.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Recommended Action: $recommendedAction'),
            ],
            if (citations.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Citations: ${citations.join(' • ')}'),
            ],
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF7DA),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(disclaimer),
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => RecommendedLawyersPage(
                          initialLawyers: latestSuggestedLawyers,
                        ),
                      ),
                    );
                  },
                  icon: const Icon(Icons.people_alt_outlined),
                  label: const Text('Find Lawyers'),
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => CreateCasePage(
                          initialTitle: issueType == 'N/A' || issueType.isEmpty
                              ? 'Legal assistance request'
                              : issueType,
                          initialDescription: lastUserProblem,
                          initialCity: location == 'Unknown' ? '' : location,
                          initialLegalArea: legalArea == 'N/A' ? '' : legalArea,
                          initialIssueType: issueType == 'N/A' ? '' : issueType,
                          initialUrgency: urgency,
                          initialAiSummary: summary,
                          initialCaseBrief: caseBrief,
                          initialCaseIntelligence: latestCaseIntelligence,
                        ),
                      ),
                    );
                  },
                  icon: const Icon(Icons.post_add),
                  label: const Text('Post Case'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentAnalysisCard(BuildContext context) {
    final analysis = latestDocumentAnalysis ?? <String, dynamic>{};
    final documentType = (analysis['document_type'] ?? 'Unknown').toString();
    final legalArea = (analysis['legal_area'] ?? 'General Legal').toString();
    final summary = (analysis['summary'] ?? '').toString();
    final recommendedAction = (analysis['recommended_action'] ?? '').toString();
    final potentialIssue = (analysis['potential_issue'] ?? '').toString();
    final confidence = (analysis['confidence_level'] ?? 'Medium').toString();
    final citations = _dynamicListToText(analysis['citations']);
    final caseBrief = Map<String, dynamic>.from(analysis['case_brief'] as Map? ?? <String, dynamic>{});
    final documents = analysis['documents'] as List<dynamic>? ?? <dynamic>[];

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: Colors.green.shade100),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.description_outlined, color: Color(0xFF2E7D32)),
                SizedBox(width: 8),
                Text(
                  'Document Analysis',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text('Document Type: $documentType'),
            const SizedBox(height: 4),
            Text('Legal Area: $legalArea'),
            const SizedBox(height: 4),
            Text('Confidence: $confidence'),
            if (potentialIssue.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('Potential Issue: $potentialIssue'),
            ],
            if (summary.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(summary, style: const TextStyle(height: 1.35)),
            ],
            if (recommendedAction.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Recommended Action: $recommendedAction'),
            ],
            if (documents.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Documents analyzed: ${documents.length}'),
            ],
            if (citations.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Citations: ${citations.join(' • ')}'),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => RecommendedLawyersPage(
                          initialLawyers: latestDocumentRecommendedLawyers,
                        ),
                      ),
                    );
                  },
                  icon: const Icon(Icons.people_alt_outlined),
                  label: const Text('Find Lawyers'),
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => CreateCasePage(
                          initialTitle: potentialIssue.isEmpty
                              ? 'Legal document issue'
                              : potentialIssue,
                          initialDescription: summary,
                          initialLegalArea: legalArea,
                          initialIssueType: potentialIssue,
                          initialAiSummary: summary,
                          initialUrgency: 'Medium',
                          initialCaseBrief: caseBrief,
                          initialCaseIntelligence: latestDocumentIntelligence,
                        ),
                      ),
                    );
                  },
                  icon: const Icon(Icons.save_as_outlined),
                  label: const Text('Save as Case'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentCaptureCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.orange.shade100),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.document_scanner_outlined, color: Color(0xFFB76E00)),
                SizedBox(width: 8),
                Text(
                  'Document Capture',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Capture with camera or assemble a multi-page upload before analysis.',
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                OutlinedButton.icon(
                  onPressed: isUploadingDocument ? null : _captureWithCamera,
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: const Text('Camera Capture'),
                ),
                OutlinedButton.icon(
                  onPressed: isUploadingDocument ? null : _pickDocumentFiles,
                  icon: const Icon(Icons.file_open_outlined),
                  label: const Text('Select Files'),
                ),
                ElevatedButton.icon(
                  onPressed: isUploadingDocument || pendingUploads.isEmpty ? null : _uploadAndAnalyzeDocument,
                  icon: const Icon(Icons.analytics_outlined),
                  label: Text(isUploadingDocument ? 'Analyzing...' : 'Analyze Packet'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (pendingUploads.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFAEF),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text('No documents queued yet.'),
              )
            else
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: pendingUploads.map((item) {
                  return Container(
                    width: 220,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFFAEF),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(_iconForUpload(item.name), color: const Color(0xFFB76E00)),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                item.name,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontWeight: FontWeight.w600),
                              ),
                            ),
                            IconButton(
                              onPressed: isUploadingDocument ? null : () => _removePendingUpload(item),
                              icon: const Icon(Icons.close, size: 18),
                            ),
                          ],
                        ),
                        Text(item.path == null ? 'Ready from memory' : 'Ready from device'),
                      ],
                    ),
                  );
                }).toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildLegalActionGuideCard() {
    final guide = latestLegalActionGuide ?? <String, dynamic>{};
    final detectedIssue = (guide['detected_issue'] ?? 'Unknown Situation').toString();
    final issueType = (guide['issue_type'] ?? 'unknown').toString();
    final portal = (guide['portal'] ?? '').toString();
    final portalLabel = (guide['portal_label'] ?? 'Official Portal').toString();
    final disclaimer = (guide['disclaimer'] ?? 'This platform provides guidance only. All legal actions must be completed by the user on official government portals.').toString();
    final actions = _dynamicListToText(guide['actions']);
    final requiredInfo = _dynamicListToText(guide['required_info']);
    final notes = _dynamicListToText(guide['notes']);

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.indigo.shade100),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.alt_route_outlined, color: Color(0xFF3657C8)),
                SizedBox(width: 8),
                Text(
                  'Legal Action Guide',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text('Detected Issue: $detectedIssue'),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF4F7FF),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(disclaimer),
            ),
            const SizedBox(height: 16),
            const Text(
              'Recommended Legal Steps',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 10),
            if (actions.isEmpty)
              Text(
                issueType == 'unknown'
                    ? 'No official guided workflow was detected for this description yet.'
                    : 'No steps available.',
              )
            else
              LayoutBuilder(
                builder: (context, constraints) {
                  final maxWidth = constraints.maxWidth;
                  final cardWidth = maxWidth < 640 ? maxWidth : (maxWidth - 12) / 2;
                  return Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      for (int index = 0; index < actions.length; index++)
                        SizedBox(
                          width: cardWidth,
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF9FAFE),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: const Color(0xFFDDE4FB)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Step ${index + 1}',
                                  style: const TextStyle(
                                    color: Color(0xFF3657C8),
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  actions[index],
                                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  );
                },
              ),
            const SizedBox(height: 16),
            if (portal.isNotEmpty) ...[
              Text('Official Portal: $portalLabel'),
              const SizedBox(height: 6),
              SelectableText(
                portal,
                style: const TextStyle(color: Color(0xFF3657C8), fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: () => _openOfficialPortal(portal),
                icon: const Icon(Icons.open_in_new_outlined),
                label: const Text('Open Official Portal'),
              ),
              const SizedBox(height: 16),
            ],
            if (requiredInfo.isNotEmpty) ...[
              const Text(
                'Required Information',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 8),
              ...requiredInfo.map(
                (item) => CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: false,
                  onChanged: null,
                  controlAffinity: ListTileControlAffinity.leading,
                  title: Text(item),
                ),
              ),
            ],
            if (notes.isNotEmpty) ...[
              const SizedBox(height: 8),
              const Text(
                'Important Notes',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 8),
              ...notes.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('• $item'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class AnimatedText extends StatefulWidget {
  final String text;

  const AnimatedText(this.text, {super.key});

  @override
  State<AnimatedText> createState() => _AnimatedTextState();
}

class _AnimatedTextState extends State<AnimatedText> {
  String displayedText = "";
  int index = 0;

  @override
  void initState() {
    super.initState();
    typeText();
  }

  void typeText() async {
    while (index < widget.text.length) {
      await Future.delayed(const Duration(milliseconds: 15));
      setState(() {
        displayedText += widget.text[index];
        index++;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Text(displayedText);
  }
}

class _PendingUpload {
  final String name;
  final List<int>? bytes;
  final String? path;
  final String mimeType;

  const _PendingUpload({
    required this.name,
    this.bytes,
    this.path,
    required this.mimeType,
  });
}

String _guessMimeType(String fileName) {
  final normalized = fileName.toLowerCase();
  if (normalized.endsWith('.pdf')) return 'application/pdf';
  if (normalized.endsWith('.png')) return 'image/png';
  return 'image/jpeg';
}

List<String> _dynamicListToText(dynamic raw) {
  if (raw is List) {
    return raw.map((item) => item.toString()).where((item) => item.trim().isNotEmpty).toList();
  }
  if (raw is String && raw.trim().isNotEmpty) {
    return [raw.trim()];
  }
  return <String>[];
}

IconData _iconForUpload(String fileName) {
  final normalized = fileName.toLowerCase();
  if (normalized.endsWith('.pdf')) return Icons.picture_as_pdf_outlined;
  return Icons.image_outlined;
}
