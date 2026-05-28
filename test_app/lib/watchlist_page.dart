import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

import 'config.dart';
import 'theme.dart';

class WatchListPage extends StatefulWidget {
  final int userId;

  const WatchListPage({super.key, required this.userId});

  @override
  State<WatchListPage> createState() => _WatchListPageState();
}

class _WatchListPageState extends State<WatchListPage> {
  List<dynamic> watchlist = [];
  List<dynamic> professionals = [];
  Set<int> selected = {};
  bool _loading = true;
  bool _adding = false;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        http.get(Uri.parse('${ApiConfig.baseUrl}/watchlist/${widget.userId}')),
        http.get(Uri.parse('${ApiConfig.baseUrl}/professionals/${widget.userId}')),
      ]);

      if (!mounted) return;
      setState(() {
        if (results[0].statusCode == 200) {
          watchlist = jsonDecode(results[0].body) as List<dynamic>;
        }
        if (results[1].statusCode == 200) {
          professionals = jsonDecode(results[1].body) as List<dynamic>;
        }
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addToWatchlist() async {
    if (selected.isEmpty) return;
    setState(() => _adding = true);
    try {
      await http.post(
        Uri.parse('${ApiConfig.baseUrl}/watchlist/add'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_id': widget.userId,
          'professional_ids': selected.toList(),
        }),
      );
      selected.clear();
      await _loadData();
    } catch (_) {
      if (mounted) setState(() => _adding = false);
    }
  }

  List<dynamic> get _filteredProfessionals {
    if (_searchQuery.isEmpty) return professionals;
    final q = _searchQuery.toLowerCase();
    return professionals
        .where((p) =>
            (p['name'] ?? '').toLowerCase().contains(q) ||
            (p['city'] ?? '').toLowerCase().contains(q) ||
            (p['category'] ?? '').toLowerCase().contains(q))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          color: AppColors.textPrimary,
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'My Watchlist',
          style: GoogleFonts.poppins(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(height: 1, color: AppColors.border),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.blue))
          : _buildBody(),
    );
  }

  Widget _buildBody() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Saved Professionals ──────────────────────────────────────────
          _SectionHeader(
            icon: Icons.bookmark_rounded,
            title: 'Saved Professionals',
            count: watchlist.length,
          ),
          const SizedBox(height: 12),

          if (watchlist.isEmpty)
            _EmptyState(
              icon: Icons.bookmark_border_rounded,
              message: 'No professionals saved yet.',
              sub: 'Add professionals from the list below to keep track of them.',
            )
          else
            ...watchlist.map((pro) => _WatchlistCard(pro: pro)),

          const SizedBox(height: 32),

          // ── Add Professionals ────────────────────────────────────────────
          _SectionHeader(
            icon: Icons.people_alt_rounded,
            title: 'Add Professionals',
            count: null,
          ),
          const SizedBox(height: 12),

          // Search bar
          TextField(
            decoration: InputDecoration(
              hintText: 'Search by name, city, or specialty…',
              prefixIcon: const Icon(Icons.search, color: AppColors.textMuted, size: 20),
              filled: true,
              fillColor: AppColors.surface,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: AppColors.border),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: AppColors.border),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: AppColors.blue, width: 2),
              ),
            ),
            onChanged: (v) => setState(() => _searchQuery = v),
          ),
          const SizedBox(height: 12),

          if (professionals.isEmpty)
            _EmptyState(
              icon: Icons.people_outline,
              message: 'No professionals available.',
              sub: 'Professionals will appear here once matched to your cases.',
            )
          else if (_filteredProfessionals.isEmpty)
            _EmptyState(
              icon: Icons.search_off,
              message: 'No results for "$_searchQuery"',
              sub: 'Try a different name or city.',
            )
          else
            ...(_filteredProfessionals.map((pro) {
              final id = (pro['id'] as num?)?.toInt() ?? 0;
              final isOnWatchlist = watchlist.any(
                  (w) => (w['id'] as num?)?.toInt() == id);
              return _ProfessionalTile(
                pro: pro,
                selected: selected.contains(id),
                onWatchlist: isOnWatchlist,
                onChanged: isOnWatchlist
                    ? null
                    : (val) => setState(() {
                          if (val == true) {
                            selected.add(id);
                          } else {
                            selected.remove(id);
                          }
                        }),
              );
            })),

          const SizedBox(height: 20),

          if (selected.isNotEmpty)
            PrimaryButton(
              label: _adding
                  ? 'Saving…'
                  : 'Add ${selected.length} professional${selected.length > 1 ? 's' : ''} to Watchlist',
              icon: Icons.bookmark_add_rounded,
              onPressed: _adding ? null : _addToWatchlist,
              loading: _adding,
              width: double.infinity,
            ),

          const SizedBox(height: 40),
        ],
      ),
    );
  }
}

// ── Section Header ────────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  final int? count;

  const _SectionHeader({required this.icon, required this.title, this.count});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppColors.blue.withOpacity(0.1),
            borderRadius: AppRadius.sm,
          ),
          child: Icon(icon, size: 18, color: AppColors.blue),
        ),
        const SizedBox(width: 10),
        Text(
          title,
          style: GoogleFonts.poppins(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        if (count != null) ...[
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: AppColors.blue.withOpacity(0.1),
              borderRadius: AppRadius.full,
            ),
            child: Text(
              '$count',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppColors.blue,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

// ── Watchlist Card ────────────────────────────────────────────────────────────

class _WatchlistCard extends StatelessWidget {
  final dynamic pro;

  const _WatchlistCard({required this.pro});

  @override
  Widget build(BuildContext context) {
    final name = pro['name']?.toString() ?? 'Unknown';
    final city = pro['city']?.toString() ?? '';
    final category = pro['category']?.toString() ?? '';
    final rating = (pro['rating'] as num?)?.toDouble() ?? 0.0;
    final reviews = (pro['reviews'] as num?)?.toInt() ?? 0;
    final initials = name.isNotEmpty ? name[0].toUpperCase() : '?';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadius.md,
        border: Border.all(color: AppColors.border),
        boxShadow: AppShadows.card,
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 22,
            backgroundColor: AppColors.blue.withOpacity(0.12),
            child: Text(
              initials,
              style: GoogleFonts.poppins(
                fontWeight: FontWeight.w700,
                color: AppColors.blue,
                fontSize: 16,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: GoogleFonts.poppins(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    if (city.isNotEmpty) ...[
                      const Icon(Icons.location_on_outlined,
                          size: 12, color: AppColors.textMuted),
                      const SizedBox(width: 3),
                      Text(city,
                          style: GoogleFonts.inter(
                              fontSize: 12, color: AppColors.textSecondary)),
                      const SizedBox(width: 8),
                    ],
                    if (category.isNotEmpty)
                      StatusBadge(label: category, color: AppColors.blue),
                  ],
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                children: [
                  const Icon(Icons.star_rounded, size: 14, color: AppColors.gold),
                  const SizedBox(width: 2),
                  Text(
                    rating.toStringAsFixed(1),
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                '$reviews review${reviews != 1 ? 's' : ''}',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Professional Tile ─────────────────────────────────────────────────────────

class _ProfessionalTile extends StatelessWidget {
  final dynamic pro;
  final bool selected;
  final bool onWatchlist;
  final ValueChanged<bool?>? onChanged;

  const _ProfessionalTile({
    required this.pro,
    required this.selected,
    required this.onWatchlist,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final name = pro['name']?.toString() ?? 'Unknown';
    final city = pro['city']?.toString() ?? '';
    final rating = (pro['rating'] as num?)?.toDouble() ?? 0.0;
    final initials = name.isNotEmpty ? name[0].toUpperCase() : '?';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: selected
            ? AppColors.blue.withOpacity(0.05)
            : AppColors.surface,
        borderRadius: AppRadius.md,
        border: Border.all(
          color: selected ? AppColors.blue.withOpacity(0.3) : AppColors.border,
        ),
      ),
      child: CheckboxListTile(
        value: onWatchlist ? true : selected,
        onChanged: onWatchlist ? null : onChanged,
        activeColor: AppColors.blue,
        checkColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        title: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: AppColors.blue.withOpacity(0.12),
              child: Text(
                initials,
                style: GoogleFonts.poppins(
                  fontWeight: FontWeight.w700,
                  color: AppColors.blue,
                  fontSize: 13,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                name,
                style: GoogleFonts.inter(
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                  color: onWatchlist ? AppColors.textMuted : AppColors.textPrimary,
                ),
              ),
            ),
            if (onWatchlist)
              StatusBadge(label: 'Saved', color: AppColors.success),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(left: 46, top: 2),
          child: Row(
            children: [
              if (city.isNotEmpty) ...[
                const Icon(Icons.location_on_outlined,
                    size: 11, color: AppColors.textMuted),
                const SizedBox(width: 3),
                Text(city,
                    style: GoogleFonts.inter(
                        fontSize: 12, color: AppColors.textSecondary)),
                const SizedBox(width: 10),
              ],
              const Icon(Icons.star_rounded, size: 12, color: AppColors.gold),
              const SizedBox(width: 2),
              Text(
                rating.toStringAsFixed(1),
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Empty State ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String message;
  final String sub;

  const _EmptyState({
    required this.icon,
    required this.message,
    required this.sub,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadius.md,
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Icon(icon, size: 40, color: AppColors.textMuted),
          const SizedBox(height: 12),
          Text(
            message,
            textAlign: TextAlign.center,
            style: GoogleFonts.poppins(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            sub,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}
