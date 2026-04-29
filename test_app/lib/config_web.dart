import 'package:web/web.dart' as web;

const String _apiBaseUrlOverride = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: '',
);

String getBaseUrl() {
  if (_apiBaseUrlOverride.isNotEmpty) {
    return _apiBaseUrlOverride;
  }

  final host = web.window.location.host;
  if (host.contains('localhost') || host.contains('127.0.0.1')) {
    return 'http://localhost:8000';
  }
  return 'http://$host/api';
}

String getWebSocketBaseUrl() {
  if (_apiBaseUrlOverride.isNotEmpty) {
    final uri = Uri.parse(_apiBaseUrlOverride);
    final scheme = uri.scheme == 'https' ? 'wss' : 'ws';
    return uri.replace(scheme: scheme).toString();
  }

  final host = web.window.location.host;
  final scheme = web.window.location.protocol == 'https:' ? 'wss' : 'ws';
  if (host.contains('localhost') || host.contains('127.0.0.1')) {
    return '$scheme://localhost:8000';
  }
  return '$scheme://$host/api';
}