import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

class CaseWorkspacePage extends StatefulWidget {
  final int caseId;
  final int currentUserId;

  const CaseWorkspacePage({
    super.key,
    required this.caseId,
    required this.currentUserId,
  });

  @override
  State<CaseWorkspacePage> createState() => _CaseWorkspacePageState();
}

class _CaseWorkspacePageState extends State<CaseWorkspacePage> {
  final TextEditingController messageController = TextEditingController();
  final ScrollController scrollController = ScrollController();

  Map<String, dynamic>? caseData;
  List<dynamic> messages = [];
  List<dynamic> timelineEvents = [];
  List<Map<String, dynamic>> contacts = [];
  int? selectedReceiverId;
  bool isLoading = true;
  bool isSending = false;
  bool isAddingEvent = false;
  String timelineSummary = '';
  Timer? refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadWorkspace();
    refreshTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      _loadMessages();
      _loadNotificationsTargets();
    });
  }

  @override
  void dispose() {
    refreshTimer?.cancel();
    messageController.dispose();
    scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadWorkspace() async {
    setState(() => isLoading = true);
    await Future.wait([
      _loadCaseDetail(),
      _loadMessages(),
      _loadTimeline(),
      _loadNotificationsTargets(),
    ]);
    if (!mounted) return;
    setState(() => isLoading = false);
  }

  Future<void> _loadCaseDetail() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/cases/${widget.caseId}'),
    );
    if (!mounted || response.statusCode != 200) return;
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    setState(() {
      caseData = data;
    });
  }

  Future<void> _loadMessages() async {
    final response = await http.get(
      Uri.parse(
        '${ApiConfig.baseUrl}/messages/${widget.caseId}?user_id=${widget.currentUserId}',
      ),
    );
    if (!mounted || response.statusCode != 200) return;
    final items = jsonDecode(response.body) as List<dynamic>;
    setState(() {
      messages = items;
    });
    Future<void>.delayed(const Duration(milliseconds: 100), () {
      if (!scrollController.hasClients) return;
      scrollController.animateTo(
        scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _loadTimeline() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/cases/${widget.caseId}/events'),
    );
    if (!mounted || response.statusCode != 200) return;
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    setState(() {
      timelineEvents = (data['items'] as List<dynamic>? ?? <dynamic>[]);
      timelineSummary = data['timeline_summary']?.toString() ?? '';
    });
  }

  Future<void> _loadNotificationsTargets() async {
    if (caseData == null) {
      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/cases/${widget.caseId}'),
      );
      if (response.statusCode == 200) {
        caseData = jsonDecode(response.body) as Map<String, dynamic>;
      }
    }

    final clientId = caseData?['client_id'] as int?;
    final isClient = clientId == widget.currentUserId;
    final List<Map<String, dynamic>> resolvedContacts = [];

    if (!isClient && clientId != null) {
      resolvedContacts.add({
        'id': clientId,
        'name': 'Client',
      });
    }

    if (isClient) {
      final applicationsResponse = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/cases/${widget.caseId}/applications'),
      );
      if (applicationsResponse.statusCode == 200) {
        final items = jsonDecode(applicationsResponse.body) as List<dynamic>;
        for (final item in items) {
          resolvedContacts.add({
            'id': item['lawyer_id'],
            'name': item['lawyer_name'] ?? 'Lawyer',
          });
        }
      }

      if (resolvedContacts.isEmpty) {
        final recommendationsResponse = await http.get(
          Uri.parse('${ApiConfig.baseUrl}/lawyers/recommended/${widget.caseId}'),
        );
        if (recommendationsResponse.statusCode == 200) {
          final items = jsonDecode(recommendationsResponse.body) as List<dynamic>;
          for (final item in items) {
            resolvedContacts.add({
              'id': item['lawyer_id'] ?? item['id'],
              'name': item['name'] ?? 'Lawyer',
            });
          }
        }
      }
    }

    final uniqueContacts = <int, Map<String, dynamic>>{};
    for (final item in resolvedContacts) {
      final id = item['id'];
      if (id is int && id != widget.currentUserId) {
        uniqueContacts[id] = item;
      }
    }

    if (!mounted) return;
    setState(() {
      contacts = uniqueContacts.values.toList();
      if (contacts.isNotEmpty && !contacts.any((item) => item['id'] == selectedReceiverId)) {
        selectedReceiverId = contacts.first['id'] as int;
      }
    });
  }

  Future<void> _sendMessage() async {
    final content = messageController.text.trim();
    if (content.isEmpty || selectedReceiverId == null) {
      return;
    }

    setState(() => isSending = true);
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/messages/send'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'case_id': widget.caseId,
        'sender_id': widget.currentUserId,
        'receiver_id': selectedReceiverId,
        'content': content,
      }),
    );

    if (!mounted) return;

    setState(() => isSending = false);

    if (response.statusCode == 200) {
      messageController.clear();
      await _loadMessages();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to send message.')),
      );
    }
  }

  Future<void> _addTimelineEvent() async {
    final descriptionController = TextEditingController();
    DateTime selectedDate = DateTime.now();

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Add Timeline Event'),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: descriptionController,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Event description',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: () async {
                        final picked = await showDatePicker(
                          context: dialogContext,
                          firstDate: DateTime(2000),
                          lastDate: DateTime(2100),
                          initialDate: selectedDate,
                        );
                        if (picked == null) return;
                        setDialogState(() {
                          selectedDate = picked;
                        });
                      },
                      icon: const Icon(Icons.event),
                      label: Text(
                        '${selectedDate.year}-${selectedDate.month.toString().padLeft(2, '0')}-${selectedDate.day.toString().padLeft(2, '0')}',
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () async {
                    if (descriptionController.text.trim().isEmpty) return;
                    Navigator.pop(dialogContext);
                    setState(() => isAddingEvent = true);
                    final response = await http.post(
                      Uri.parse('${ApiConfig.baseUrl}/cases/${widget.caseId}/events'),
                      headers: {'Content-Type': 'application/json'},
                      body: jsonEncode({
                        'description': descriptionController.text.trim(),
                        'event_date': '${selectedDate.year}-${selectedDate.month.toString().padLeft(2, '0')}-${selectedDate.day.toString().padLeft(2, '0')}',
                      }),
                    );
                    if (!mounted) return;
                    setState(() => isAddingEvent = false);
                    if (response.statusCode == 200) {
                      await _loadTimeline();
                    }
                  },
                  child: const Text('Save Event'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final caseBrief = (caseData?['case_brief'] as Map<String, dynamic>?) ?? <String, dynamic>{};

    return Scaffold(
      appBar: AppBar(
        title: Text(caseData?['title']?.toString() ?? 'Case Workspace'),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadWorkspace,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                    child: Padding(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            caseData?['title']?.toString() ?? 'Case',
                            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          Text(caseData?['description']?.toString() ?? ''),
                          const SizedBox(height: 14),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _InfoChip(label: 'Legal Area', value: caseData?['legal_area']?.toString() ?? 'General Legal'),
                              _InfoChip(label: 'Issue Type', value: caseData?['issue_type']?.toString() ?? 'General Inquiry'),
                              _InfoChip(label: 'Urgency', value: caseData?['urgency']?.toString() ?? 'Medium'),
                              _InfoChip(label: 'City', value: caseData?['city']?.toString() ?? 'Unknown'),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Card(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                    child: Padding(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Structured Case Brief',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 10),
                          _BriefSection(title: 'Summary', values: [caseBrief['case_summary']?.toString() ?? 'No summary generated yet.']),
                          _BriefSection(title: 'Key Entities', values: _asStringList(caseBrief['key_entities'])),
                          _BriefSection(title: 'Timeline', values: _asStringList(caseBrief['timeline'])),
                          _BriefSection(title: 'Documents', values: _asStringList(caseBrief['documents'])),
                          _BriefSection(title: 'Recommended Next Steps', values: _asStringList(caseBrief['recommended_next_steps'])),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final isNarrow = constraints.maxWidth < 880;
                      if (isNarrow) {
                        return Column(
                          children: [
                            _buildMessagesCard(),
                            const SizedBox(height: 14),
                            _buildTimelineCard(),
                          ],
                        );
                      }

                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(child: _buildMessagesCard()),
                          const SizedBox(width: 14),
                          Expanded(child: _buildTimelineCard()),
                        ],
                      );
                    },
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildMessagesCard() {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text(
                  'Messaging',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                if (contacts.isNotEmpty)
                  DropdownButton<int>(
                    value: selectedReceiverId,
                    hint: const Text('Select recipient'),
                    items: contacts
                        .map(
                          (item) => DropdownMenuItem<int>(
                            value: item['id'] as int,
                            child: Text(item['name']?.toString() ?? 'Contact'),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      setState(() => selectedReceiverId = value);
                    },
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              height: 340,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF7F8FC),
                borderRadius: BorderRadius.circular(14),
              ),
              child: messages.isEmpty
                  ? const Center(
                      child: Text('No messages yet. Start the conversation from this case workspace.'),
                    )
                  : ListView.builder(
                      controller: scrollController,
                      itemCount: messages.length,
                      itemBuilder: (context, index) {
                        final message = messages[index] as Map<String, dynamic>;
                        final isMine = message['is_mine'] == true;
                        return Align(
                          alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 360),
                            margin: const EdgeInsets.symmetric(vertical: 6),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: isMine ? const Color(0xFF1E63E9) : Colors.white,
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  message['content']?.toString() ?? '',
                                  style: TextStyle(color: isMine ? Colors.white : Colors.black87),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  message['sender_name']?.toString() ?? '',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: isMine ? Colors.white70 : Colors.black54,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: messageController,
                    minLines: 1,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      hintText: 'Write a secure case message',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton.icon(
                  onPressed: isSending || selectedReceiverId == null ? null : _sendMessage,
                  icon: const Icon(Icons.send),
                  label: Text(isSending ? 'Sending...' : 'Send'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineCard() {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text(
                  'Case Timeline',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                ElevatedButton.icon(
                  onPressed: isAddingEvent ? null : _addTimelineEvent,
                  icon: const Icon(Icons.add),
                  label: Text(isAddingEvent ? 'Saving...' : 'Add Event'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (timelineSummary.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF8E6),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(timelineSummary),
              ),
            const SizedBox(height: 12),
            if (timelineEvents.isEmpty)
              const Text('No timeline events have been added yet.')
            else
              ...timelineEvents.map(
                (item) => Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE1E6F0)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 12,
                        height: 12,
                        margin: const EdgeInsets.only(top: 4),
                        decoration: const BoxDecoration(
                          color: Color(0xFF1E63E9),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item['description']?.toString() ?? '',
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 4),
                            Text(item['event_date']?.toString() ?? ''),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final String label;
  final String value;

  const _InfoChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F6FD),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text('$label: $value'),
    );
  }
}

class _BriefSection extends StatelessWidget {
  final String title;
  final List<String> values;

  const _BriefSection({required this.title, required this.values});

  @override
  Widget build(BuildContext context) {
    final normalized = values.where((item) => item.trim().isNotEmpty).toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          if (normalized.isEmpty)
            const Text('No details yet.')
          else
            ...normalized.map((item) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $item'),
                )),
        ],
      ),
    );
  }
}

List<String> _asStringList(dynamic raw) {
  if (raw is List) {
    return raw.map((item) => item.toString()).where((item) => item.trim().isNotEmpty).toList();
  }
  if (raw is String && raw.trim().isNotEmpty) {
    return [raw.trim()];
  }
  return <String>[];
}