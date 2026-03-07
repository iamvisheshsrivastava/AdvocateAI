import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'landing_page.dart';
import 'role_home_page.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  Future<Map<String, dynamic>> _getSessionState() async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt("user_id");
    final expiresAt = prefs.getInt("session_expires_at");
    final role = prefs.getString("user_role") ?? "client";

    if (userId == null || expiresAt == null) {
      return {"active": false, "role": role};
    }

    final isExpired = DateTime.now().millisecondsSinceEpoch >= expiresAt;
    if (isExpired) {
      await prefs.remove("user_id");
      await prefs.remove("user_email");
      await prefs.remove("user_role");
      await prefs.remove("session_expires_at");
      return {"active": false, "role": role};
    }

    return {"active": true, "role": role};
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: FutureBuilder<Map<String, dynamic>>(
        future: _getSessionState(),
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }

          final active = snapshot.data!["active"] == true;
          final role = (snapshot.data!["role"] ?? "client").toString();

          return active ? RoleHomePage(role: role) : const LandingPage();
        },
      ),
    );
  }
}
