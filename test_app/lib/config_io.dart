String getBaseUrl() => const String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

String getWebSocketBaseUrl() {
  final uri = Uri.parse(getBaseUrl());
  final scheme = uri.scheme == 'https' ? 'wss' : 'ws';
  return uri.replace(scheme: scheme).toString();
}