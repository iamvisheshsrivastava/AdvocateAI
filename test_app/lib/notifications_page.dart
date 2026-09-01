import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'config.dart';

class NotificationSocketClient {
  NotificationSocketClient({
    required this.userId,
    required this.onNotification,
  });

  final int userId;
  final VoidCallback onNotification;

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _reconnectTimer;
  bool _disposed = false;

  void connect() async {
    if (_disposed || _channel != null) {
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token') ?? '';
    if (token.isEmpty || _disposed || _channel != null) {
      return;
    }

    final uri = Uri.parse(
      '${ApiConfig.webSocketBaseUrl}/ws/notifications/$userId?token=$token',
    );
    _channel = WebSocketChannel.connect(uri);
    _subscription = _channel!.stream.listen(
      (event) {
        if (_disposed) {
          return;
        }

        try {
          final decoded = event is String ? jsonDecode(event) : event;
          if (decoded is Map<String, dynamic> && decoded['event'] != 'notification.created') {
            return;
          }
        } catch (_) {
          return;
        }

        onNotification();
      },
      onError: (_) => _scheduleReconnect(),
      onDone: _scheduleReconnect,
      cancelOnError: true,
    );
  }

  void _scheduleReconnect() {
    if (_disposed) {
      return;
    }

    _closeChannel();
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 5), connect);
  }

  void _closeChannel() {
    _subscription?.cancel();
    _subscription = null;
    _channel?.sink.close();
    _channel = null;
  }

  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _closeChannel();
  }
}

class NotificationsPage extends StatefulWidget {
  final int userId;

  const NotificationsPage({super.key, required this.userId});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  bool isLoading = true;
  List<dynamic> notifications = [];
  late final NotificationSocketClient socketClient;

  @override
  void initState() {
    super.initState();
    socketClient = NotificationSocketClient(
      userId: widget.userId,
      onNotification: () {
        if (!mounted) {
          return;
        }

        _loadNotifications(markAsRead: true);
      },
    );
    _loadNotifications(markAsRead: true);
    socketClient.connect();
  }

  @override
  void dispose() {
    socketClient.dispose();
    super.dispose();
  }

  Future<void> _loadNotifications({bool markAsRead = false}) async {
    try {
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
    } catch (_) {
      if (!mounted) return;
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
                          subtitle: Text(_formatDate(item['created_at']?.toString())),
                        ),
                      );
                    },
                  ),
                ),
    );
  }

  String _formatDate(String? isoString) {
    if (isoString == null || isoString.isEmpty) return '';
    try {
      final dt = DateTime.parse(isoString).toLocal();
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inSeconds < 60) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      final month = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
      ][dt.month - 1];
      return '${dt.day} $month ${dt.year}';
    } catch (_) {
      return isoString ?? '';
    }
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
  late final NotificationSocketClient socketClient;

  @override
  void initState() {
    super.initState();
    socketClient = NotificationSocketClient(
      userId: widget.userId,
      onNotification: () {
        if (mounted) {
          _loadUnreadCount();
        }
      },
    );
    _loadUnreadCount();
    timer = Timer.periodic(const Duration(seconds: 20), (_) => _loadUnreadCount());
    socketClient.connect();
  }

  @override
  void dispose() {
    socketClient.dispose();
    timer?.cancel();
    super.dispose();
  }

  Future<void> _loadUnreadCount() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/notifications?user_id=${widget.userId}'),
      );
      if (!mounted || response.statusCode != 200) return;
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      setState(() {
        unreadCount = data['unread_count'] as int? ?? 0;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        unreadCount = 0;
      });
    }
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
