import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'watchlist_page.dart';
import 'notifications_page.dart';
import 'config.dart';
import 'login_page.dart';
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController messageController = TextEditingController();
  final ScrollController scrollController = ScrollController();

  String userEmail = "";
  int? userId;
  bool isTyping = false;
  List<Map<String, String>> messages = [];

  @override
  void initState() {
    super.initState();
    loadUser();
  }

  void scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (scrollController.hasClients) {
        scrollController.animateTo(
          scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> loadUser() async {
    final prefs = await SharedPreferences.getInstance();
    final email = prefs.getString("user_email") ?? "User";
    final id = prefs.getInt("user_id");

    setState(() {
      userEmail = email;
      userId = id;
      messages.add({
        "role": "assistant",
        "text": "Hi $userEmail, how can I help you today?"
      });
    });
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();

    if (!mounted) return;

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => LoginPage()),
      (route) => false,
    );
  }

  Future<void> sendMessage({String? presetText}) async {
    final text = presetText ?? messageController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      messages.add({"role": "user", "text": text});
      isTyping = true;
    });

    scrollToBottom();
    messageController.clear();

    final url = Uri.parse("${ApiConfig.baseUrl}/chat");

    final response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"message": text}),
    );

    String reply = "Error getting response";

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      reply = data["response"];
    }

    setState(() {
      isTyping = false;
      messages.add({"role": "assistant", "text": reply});
    });

    scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFF7F9FC), Color(0xFFEFF6FB)],
          ),
        ),
        child: SafeArea(
          child: Row(
            children: [
              // Left sidebar
              Container(
                width: 260,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: const BorderRadius.only(
                    topRight: Radius.circular(20),
                    bottomRight: Radius.circular(20),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.05),
                      blurRadius: 12,
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 8),
                    const Text(
                      'AdvocateAI',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E88E5),
                      ),
                    ),
                    const SizedBox(height: 14),
                    ListTile(
                      leading: const Icon(Icons.search_rounded, color: Colors.blue),
                      title: const Text('Quick Find'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {},
                    ),
                    ListTile(
                      leading: const Icon(Icons.book, color: Colors.blue),
                      title: const Text('WatchList'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {
                        if (userId != null) {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => WatchListPage(userId: userId!),
                            ),
                          );
                        }
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.notifications, color: Colors.blue),
                      title: const Text('Notifications'),
                      contentPadding: EdgeInsets.zero,
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const NotificationsPage(),
                          ),
                        );
                      },
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEEF7FF),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        children: const [
                          Icon(Icons.upgrade, color: Color(0xFF1E88E5)),
                          SizedBox(width: 10),
                          Expanded(child: Text('Become Pro Access')),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              // Main content
              Expanded(
                child: Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(40),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 980),
                      child: Container(
                        padding: const EdgeInsets.all(28),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(18),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.06),
                              blurRadius: 20,
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                TextButton.icon(
                                  onPressed: logout,
                                  icon: const Icon(Icons.logout),
                                  label: const Text('Logout'),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              'Find exactly what you\'re looking for,\n in seconds.',
                              style: TextStyle(
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                height: 1.12,
                              ),
                            ),
                            const SizedBox(height: 8),
                            TextButton(
                              onPressed: () {},
                              child: const Text('See how it works.'),
                            ),

                            const SizedBox(height: 22),

                            // Action chips
                            Wrap(
                              spacing: 12,
                              runSpacing: 12,
                              children: [
                                _buildActionChip(Icons.description, 'Best criminal lawyer in Berlin'),
                                _buildActionChip(Icons.person_search, 'Top-rated immigration lawyer'),
                                _buildActionChip(Icons.lightbulb, 'English-speaking lawyer in Germany'),
                                _buildActionChip(Icons.email, 'Lawyer with highest reviews in Hamburg'),
                              ],
                            ),

                            SizedBox(
                              height: 300,
                              child: ListView.builder(
                                controller: scrollController,
                                itemCount: messages.length,
                                itemBuilder: (context, index) {
                                  final msg = messages[index];
                                  final isUser = msg["role"] == "user";

                                  return Align(
                                    alignment:
                                        isUser ? Alignment.centerRight : Alignment.centerLeft,
                                    child: Container(
                                      margin: const EdgeInsets.symmetric(vertical: 6),
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: isUser ? Colors.blue : Colors.grey.shade200,
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: MarkdownBody(
                                        data: msg["text"] ?? "",
                                        styleSheet: MarkdownStyleSheet(
                                          p: TextStyle(
                                            color: isUser ? Colors.white : Colors.black,
                                            fontSize: 15,
                                          ),
                                          strong: const TextStyle(fontWeight: FontWeight.bold),
                                          code: const TextStyle(
                                            backgroundColor: Color(0xFFEFEFEF),
                                            fontFamily: 'monospace',
                                          ),
                                          codeblockDecoration: BoxDecoration(
                                            color: const Color(0xFFF4F4F4),
                                            borderRadius: BorderRadius.circular(8),
                                          ),
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),

                            const SizedBox(height: 20),

                            // Central rounded input area
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: Colors.grey.shade200),
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFFFFFF), Color(0xFFF8FBFF)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: messageController,
                                      onSubmitted: (_) => sendMessage(),
                                      decoration: const InputDecoration(
                                        hintText: 'What are you looking for?',
                                        border: InputBorder.none,
                                      ),
                                    ),
                                  ),
                                  IconButton(
                                    onPressed: () {},
                                    icon: const Icon(Icons.mic, color: Colors.blue),
                                  ),
                                  ElevatedButton(
                                    onPressed: sendMessage,
                                    style: ElevatedButton.styleFrom(
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                    ),
                                    child: const Icon(Icons.arrow_forward),
                                  )
                                ],
                              ),
                            ),

                            const SizedBox(height: 18),

                            // small helper chips below
                            Row(
                              children: const [
                                Chip(label: Text('Attach')),
                                SizedBox(width: 8),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionChip(IconData icon, String label) {
    return ActionChip(
      backgroundColor: const Color(0xFFF3F8FF),
      labelPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: const Color(0xFF1E88E5)),
          const SizedBox(width: 8),
          Text(label),
        ],
      ),
      onPressed: () {
        sendMessage(presetText: label);
      },
    );
  }
}

class AnimatedText extends StatefulWidget {
  final String text;

  const AnimatedText(this.text, {super.key});

  @override
  State<AnimatedText> createState() => _AnimatedTextState();
}

class _AnimatedTextState extends State<AnimatedText> {
  String displayedText = "";
  int index = 0;

  @override
  void initState() {
    super.initState();
    typeText();
  }

  void typeText() async {
    while (index < widget.text.length) {
      await Future.delayed(const Duration(milliseconds: 15));
      setState(() {
        displayedText += widget.text[index];
        index++;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Text(displayedText);
  }
}
