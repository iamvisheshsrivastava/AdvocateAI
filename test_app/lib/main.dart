import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'home_page.dart';
import 'landing_page.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  Future<bool> _hasActiveSession() async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt("user_id");
    final expiresAt = prefs.getInt("session_expires_at");

    if (userId == null || expiresAt == null) {
      return false;
    }

    final isExpired = DateTime.now().millisecondsSinceEpoch >= expiresAt;
    if (isExpired) {
      await prefs.remove("user_id");
      await prefs.remove("user_email");
      await prefs.remove("session_expires_at");
      return false;
    }

    return true;
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: FutureBuilder<bool>(
        future: _hasActiveSession(),
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }

          return snapshot.data == true ? const HomePage() : const LandingPage();
        },
      ),
    );
  }
}
