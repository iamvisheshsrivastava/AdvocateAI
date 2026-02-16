import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'config.dart';

class WatchListPage extends StatefulWidget {
  final int userId;

  const WatchListPage({super.key, required this.userId});

  @override
  State<WatchListPage> createState() => _WatchListPageState();
}

class _WatchListPageState extends State<WatchListPage> {
  List watchlist = [];
  List professionals = [];
  Set<int> selected = {};

  @override
  void initState() {
    super.initState();
    loadData();
  }

  Future<void> loadData() async {
    final watchRes = await http.get(
      Uri.parse("${ApiConfig.baseUrl}/watchlist/${widget.userId}"),
    );

    final proRes = await http.get(
      Uri.parse("${ApiConfig.baseUrl}/professionals/${widget.userId}"),
    );

    if (watchRes.statusCode == 200 && proRes.statusCode == 200) {
      setState(() {
        watchlist = jsonDecode(watchRes.body);
        professionals = jsonDecode(proRes.body);
      });
    }
  }
  
  Future<void> addToWatchlist() async {
    await http.post(
      Uri.parse("${ApiConfig.baseUrl}/watchlist/add"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "user_id": widget.userId,
        "professional_ids": selected.toList(),
      }),
    );

    selected.clear();
    loadData();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("WatchList")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            /// TOP: WATCHLIST
            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                "Your WatchList",
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 10),

            Expanded(
              child: SingleChildScrollView(
                child: DataTable(
                  columns: const [
                    DataColumn(label: Text("Name")),
                    DataColumn(label: Text("City")),
                    DataColumn(label: Text("Category")),
                    DataColumn(label: Text("Rating")),
                    DataColumn(label: Text("Reviews")),
                  ],
                  rows: watchlist.map<DataRow>((pro) {
                    return DataRow(cells: [
                      DataCell(Text(pro["name"])),
                      DataCell(Text(pro["city"] ?? "")),
                      DataCell(Text(pro["category"] ?? "")),
                      DataCell(Text(pro["rating"].toString())),
                      DataCell(Text(pro["reviews"].toString())),
                    ]);
                  }).toList(),
                ),
              ),
            ),

            const Divider(height: 30),

            /// BOTTOM: PROFESSIONAL LIST
            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                "Add Professionals to WatchList",
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 10),

            Expanded(
              child: ListView(
                children: professionals.map((pro) {
                  final id = pro["id"];

                  return CheckboxListTile(
                    value: selected.contains(id),
                    onChanged: (val) {
                      setState(() {
                        if (val == true) {
                          selected.add(id);
                        } else {
                          selected.remove(id);
                        }
                      });
                    },
                    title: Text(pro["name"]),
                    subtitle: Text(
                        "${pro["city"]} • Rating: ${pro["rating"]}"),
                  );
                }).toList(),
              ),
            ),

            const SizedBox(height: 10),

            ElevatedButton(
              onPressed: selected.isEmpty ? null : addToWatchlist,
              child: const Text("Add to WatchList"),
            )
          ],
        ),
      ),
    );
  }
}
