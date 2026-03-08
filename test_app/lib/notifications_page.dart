import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

class NotificationsPage extends StatefulWidget {
  final int userId;

  const NotificationsPage({super.key, required this.userId});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  bool isLoading = true;
  List<dynamic> notifications = [];

  @override
  void initState() {
    super.initState();
    _loadNotifications(markAsRead: true);
  }

  Future<void> _loadNotifications({bool markAsRead = false}) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/notifications?user_id=${widget.userId}'),
    );

    if (!mounted) return;

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final items = data['items'] as List<dynamic>? ?? <dynamic>[];
      setState(() {
        notifications = items;
        isLoading = false;
      });

      if (markAsRead && items.any((item) => item['is_read'] == false)) {
        await http.post(
          Uri.parse('${ApiConfig.baseUrl}/notifications/read'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'user_id': widget.userId}),
        );
      }
    } else {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : notifications.isEmpty
              ? const Center(
                  child: Text(
                    'No notifications yet.',
                    style: TextStyle(fontSize: 16, color: Colors.grey),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadNotifications,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: notifications.length,
                    itemBuilder: (context, index) {
                      final item = notifications[index] as Map<String, dynamic>;
                      return Card(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: item['is_read'] == true
                                ? const Color(0xFFE9EEF8)
                                : const Color(0xFFFFE7C2),
                            child: Icon(
                              _iconForType(item['type']?.toString() ?? ''),
                              color: const Color(0xFF1E63E9),
                            ),
                          ),
                          title: Text(item['message']?.toString() ?? ''),
                          subtitle: Text(item['created_at']?.toString() ?? ''),
                        ),
                      );
                    },
                  ),
                ),
    );
  }

  IconData _iconForType(String type) {
    switch (type) {
      case 'application':
        return Icons.assignment_turned_in_outlined;
      case 'message':
        return Icons.mark_chat_unread_outlined;
      case 'recommendation':
        return Icons.recommend_outlined;
      default:
        return Icons.notifications_none;
    }
  }
}

class NotificationBellAction extends StatefulWidget {
  final int userId;

  const NotificationBellAction({super.key, required this.userId});

  @override
  State<NotificationBellAction> createState() => _NotificationBellActionState();
}

class _NotificationBellActionState extends State<NotificationBellAction> {
  int unreadCount = 0;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    _loadUnreadCount();
    timer = Timer.periodic(const Duration(seconds: 20), (_) => _loadUnreadCount());
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  Future<void> _loadUnreadCount() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/notifications?user_id=${widget.userId}'),
    );
    if (!mounted || response.statusCode != 200) return;
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    setState(() {
      unreadCount = data['unread_count'] as int? ?? 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        IconButton(
          onPressed: () async {
            await Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => NotificationsPage(userId: widget.userId),
              ),
            );
            _loadUnreadCount();
          },
          icon: const Icon(Icons.notifications_outlined),
        ),
        if (unreadCount > 0)
          Positioned(
            right: 8,
            top: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.redAccent,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                unreadCount > 9 ? '9+' : '$unreadCount',
                style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ),
          ),
      ],
    );
  }
}
