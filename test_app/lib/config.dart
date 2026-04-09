import 'config_base.dart'
    if (dart.library.html) 'config_web.dart'
    if (dart.library.io) 'config_io.dart' as config_impl;

class ApiConfig {
  static String get baseUrl => config_impl.getBaseUrl();

  static String get webSocketBaseUrl => config_impl.getWebSocketBaseUrl();
}