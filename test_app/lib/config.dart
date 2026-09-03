import 'package:shared_preferences/shared_preferences.dart';

import 'config_base.dart'
    if (dart.library.html) 'config_web.dart'
    if (dart.library.io) 'config_io.dart' as config_impl;

class ApiConfig {
  static String get baseUrl => config_impl.getBaseUrl();

  static String get webSocketBaseUrl => config_impl.getWebSocketBaseUrl();

  /// Standard JSON headers plus the caller's Bearer token (read from the
  /// session stored at login/signup), for requests to endpoints that now
  /// require authentication.
  static Future<Map<String, String>> authHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token') ?? '';
    return {
      'Content-Type': 'application/json',
      if (token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }
}