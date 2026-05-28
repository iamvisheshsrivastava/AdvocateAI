import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'landing_page.dart';
import 'role_home_page.dart';
import 'theme.dart';

void main() {
  runApp(const AdvocateApp());
}

class AdvocateApp extends StatelessWidget {
  const AdvocateApp({super.key});

  Future<Map<String, dynamic>> _getSessionState() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token') ?? '';
    final role = prefs.getString('user_role') ?? 'client';

    if (token.isEmpty) return {'active': false, 'role': role};
    return {'active': true, 'role': role};
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AdvocateAI',
      theme: buildAppTheme(),
      home: FutureBuilder<Map<String, dynamic>>(
        future: _getSessionState(),
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Scaffold(
              body: Center(
                child: CircularProgressIndicator(),
              ),
            );
          }
          final active = snapshot.data!['active'] == true;
          final role = (snapshot.data!['role'] ?? 'client').toString();
          return active ? RoleHomePage(role: role) : const LandingPage();
        },
      ),
    );
  }
}
