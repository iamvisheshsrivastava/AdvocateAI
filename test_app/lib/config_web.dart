import 'package:web/web.dart' as web;

String getBaseUrl() {
  final host = web.window.location.host;
  if (host.contains('localhost') || host.contains('127.0.0.1')) {
    return 'http://localhost:8000';
  }
  return 'http://$host/api';
}