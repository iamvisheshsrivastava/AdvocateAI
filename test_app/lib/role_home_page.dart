import 'package:flutter/material.dart';
import 'home_page.dart';
import 'lawyer_dashboard_page.dart';

class RoleHomePage extends StatelessWidget {
  final String role;

  const RoleHomePage({super.key, required this.role});

  @override
  Widget build(BuildContext context) {
    if (role.toLowerCase() == 'lawyer') {
      return const LawyerDashboardPage();
    }
    return const HomePage();
  }
}
