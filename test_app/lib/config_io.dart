String getBaseUrl() => const String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);