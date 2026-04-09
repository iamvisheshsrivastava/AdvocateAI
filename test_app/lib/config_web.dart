import 'package:web/web.dart' as web;

String getBaseUrl() {
  final host = web.window.location.host;
  if (host.contains('localhost') || host.contains('127.0.0.1')) {
    return 'http://localhost:8000';
  }
  return 'http://$host/api';
}

String getWebSocketBaseUrl() {
  final host = web.window.location.host;
  final scheme = web.window.location.protocol == 'https:' ? 'wss' : 'ws';
  if (host.contains('localhost') || host.contains('127.0.0.1')) {
    return '$scheme://localhost:8000';
  }
  return '$scheme://$host/api';
}