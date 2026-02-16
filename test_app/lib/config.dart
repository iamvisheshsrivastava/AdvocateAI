import 'dart:html' as html;

class ApiConfig {
  static String get baseUrl {
    final host = html.window.location.host;

    // If running locally
    if (host.contains('localhost') || host.contains('127.0.0.1')) {
      return "http://localhost:8000";
    }

    // If running on server
    return "http://$host/api";
  }
}