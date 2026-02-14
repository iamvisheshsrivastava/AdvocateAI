import 'package:flutter/material.dart';

class SecondPage extends StatelessWidget {
  final List<Map<String, dynamic>> students;

  const SecondPage({super.key, required this.students});

  Widget studentCard(Map<String, dynamic> student) {
    return Card(
      elevation: 3,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.teal,
          child: Text(
            student['name'][0],
            style: const TextStyle(color: Colors.white),
          ),
        ),
        title: Text(
          student['name'],
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text("Age: ${student['age']}"),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Student Details"),
        centerTitle: true,
      ),
      body: students.isEmpty
          ? const Center(child: Text("No students available"))
          : ListView.builder(
              itemCount: students.length,
              itemBuilder: (context, index) {
                return studentCard(students[index]);
              },
            ),
    );
  }
}
