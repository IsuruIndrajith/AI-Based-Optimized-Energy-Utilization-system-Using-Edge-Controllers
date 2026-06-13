// lib/pages/home_page.dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:async';
import '../services/firestore_service.dart';
import 'custom_command_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  Map<String, dynamic> analysis = {};
  Map<String, List<int>> schedules = {};
  bool loading = true;
  String? errorMessage;
  DateTime? lastUpdated;

  @override
  void initState() {
    super.initState();
    fetchData();
    Timer.periodic(const Duration(minutes: 30), (_) => fetchData());
  }

  Future<void> fetchData() async {
    try {
      setState(() {
        loading = true;
        errorMessage = null;
      });
      final combined = await FirestoreService.fetchCombinedData();
      final rawAnalysis = combined['analysis'] as Map<String, dynamic>? ?? {};
      setState(() {
        // Filter to only appliance entries (Maps)
        analysis = Map.fromEntries(
          rawAnalysis.entries.where((e) => e.value is Map),
        );
        schedules =
            combined['schedules'] as Map<String, List<int>>? ?? {};
        loading = false;
        lastUpdated = DateTime.now();
      });
    } catch (e) {
      setState(() {
        loading = false;
        errorMessage = e.toString().replaceAll('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blueGrey[50],
      appBar: AppBar(
        title: const Text('Energy Dashboard',
            style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.teal,
        elevation: 0,
        actions: [
          IconButton(
            onPressed: fetchData,
            icon: const Icon(Icons.refresh, color: Colors.white),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : errorMessage != null
              ? _buildErrorWidget()
              : _buildDashboard(),
    );
  }

  Widget _buildErrorWidget() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off, size: 56, color: Colors.grey),
            const SizedBox(height: 16),
            const Text('Could not load dashboard data',
                style:
                    TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(
              errorMessage ?? 'Unknown error',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: fetchData,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.teal),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDashboard() {
    final summary = FirestoreService.computeSummary(analysis);
    final totalOriginal = summary['original']!;
    final totalOptimized = summary['optimized']!;
    final totalSavings = summary['savings']!;
    final savingsPercent = summary['savingsPercent']!;

    // Total active appliances right now (current hour)
    final currentHour = DateTime.now().hour;
    int activeNow = 0;
    schedules.forEach((_, arr) {
      if (arr.length > currentHour && arr[currentHour] == 1) activeNow++;
    });

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Last updated chip
          if (lastUpdated != null)
            Align(
              alignment: Alignment.centerRight,
              child: Chip(
                avatar: const Icon(Icons.access_time, size: 14),
                label: Text(
                  'Updated ${lastUpdated!.hour.toString().padLeft(2, '0')}:${lastUpdated!.minute.toString().padLeft(2, '0')}',
                  style: const TextStyle(fontSize: 11),
                ),
                backgroundColor: Colors.white,
                padding: EdgeInsets.zero,
              ),
            ),
          const SizedBox(height: 6),

          // ── Section 1: Savings hero card ──────────────────────────────
          _buildSavingsHeroCard(
              totalOriginal, totalOptimized, totalSavings, savingsPercent),
          const SizedBox(height: 16),

          // ── Section 2: Quick stat cards ───────────────────────────────
          _buildQuickStats(analysis, activeNow),
          const SizedBox(height: 16),

          // ── Section 3: Per-appliance cost bar chart ───────────────────
          _buildApplianceCostChart(analysis),
          const SizedBox(height: 16),

          // ── Section 4: Active appliances right now ────────────────────
          _buildCurrentHourCard(schedules, currentHour),
          const SizedBox(height: 16),

          // ── Section 5: Custom command shortcut ───────────────────────
          _buildCustomCommandCard(context),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  // ── Savings hero ──────────────────────────────────────────────────────────
  Widget _buildSavingsHeroCard(double original, double optimized,
      double savings, double percent) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      elevation: 4,
      color: Colors.teal[700],
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: const [
                Icon(Icons.bolt, color: Colors.yellowAccent, size: 28),
                SizedBox(width: 8),
                Text(
                  'Energy Cost Overview',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _heroMetric('Original', 'Rs.${original.toStringAsFixed(0)}',
                    Colors.red[200]!),
                Container(width: 1, height: 40, color: Colors.white24),
                _heroMetric('Optimized', 'Rs.${optimized.toStringAsFixed(0)}',
                    Colors.blue[200]!),
                Container(width: 1, height: 40, color: Colors.white24),
                _heroMetric('Saved', 'Rs.${savings.toStringAsFixed(0)}',
                    Colors.greenAccent),
              ],
            ),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: (percent / 100).clamp(0.0, 1.0),
                backgroundColor: Colors.white24,
                valueColor:
                    const AlwaysStoppedAnimation<Color>(Colors.greenAccent),
                minHeight: 10,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${percent.toStringAsFixed(1)}% total savings from optimization',
              style: const TextStyle(
                  color: Colors.white70, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _heroMetric(String label, String value, Color color) {
    return Column(
      children: [
        Text(value,
            style: TextStyle(
                fontSize: 19, fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 4),
        Text(label,
            style:
                const TextStyle(color: Colors.white60, fontSize: 12)),
      ],
    );
  }

  // ── Quick stat cards ──────────────────────────────────────────────────────
  Widget _buildQuickStats(
      Map<String, dynamic> analysis, int activeNow) {
    final totalAppliances = analysis.length;
    double bestSavings = 0;
    String bestAppliance = '—';
    analysis.forEach((key, value) {
      if (value is Map<String, dynamic>) {
        final s = (value['savings'] as num?)?.toDouble() ?? 0;
        if (s > bestSavings) {
          bestSavings = s;
          bestAppliance = key.replaceAll('_Power', '');
        }
      }
    });

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.4,
      children: [
        _statCard(
          icon: Icons.devices,
          label: 'Appliances Tracked',
          value: '$totalAppliances',
          color: Colors.blue,
        ),
        _statCard(
          icon: Icons.power,
          label: 'Active Right Now',
          value: '$activeNow of $totalAppliances',
          color: activeNow > 0 ? Colors.green : Colors.grey,
        ),
        _statCard(
          icon: Icons.emoji_events,
          label: 'Best Saving',
          value: _formatName(bestAppliance),
          color: Colors.orange,
        ),
        _statCard(
          icon: Icons.savings,
          label: 'Best Savings Amount',
          value: 'Rs.${bestSavings.toStringAsFixed(0)}',
          color: Colors.teal,
        ),
      ],
    );
  }

  Widget _statCard({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: const [
          BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 3))
        ],
      ),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 26),
          const Spacer(),
          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: color,
            ),
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(label,
              style: const TextStyle(fontSize: 11, color: Colors.black45)),
        ],
      ),
    );
  }

  // ── Appliance cost bar chart ───────────────────────────────────────────────
  Widget _buildApplianceCostChart(Map<String, dynamic> analysis) {
    if (analysis.isEmpty) return const SizedBox();

    final entries = analysis.entries
        .where((e) => e.value is Map)
        .toList();

    // Build bar data: one group per appliance, 2 bars (original & optimized)
    List<BarChartGroupData> groups = [];
    List<String> labels = [];

    for (int i = 0; i < entries.length; i++) {
      final data = entries[i].value as Map<String, dynamic>;
      final orig = (data['original_cost'] as num?)?.toDouble() ?? 0;
      final opt = (data['optimized_cost'] as num?)?.toDouble() ?? 0;
      labels.add(_shortName(entries[i].key));
      groups.add(
        BarChartGroupData(
          x: i,
          groupVertically: false,
          barRods: [
            BarChartRodData(
              toY: orig,
              color: Colors.red[300],
              width: 10,
              borderRadius: BorderRadius.circular(3),
            ),
            BarChartRodData(
              toY: opt,
              color: Colors.teal[400],
              width: 10,
              borderRadius: BorderRadius.circular(3),
            ),
          ],
          barsSpace: 3,
        ),
      );
    }

    double maxY = 0;
    for (final g in groups) {
      for (final rod in g.barRods) {
        if (rod.toY > maxY) maxY = rod.toY;
      }
    }
    maxY = (maxY * 1.2).ceilToDouble();

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 3))
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Cost per Appliance',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              _legendDot(Colors.red[300]!),
              const SizedBox(width: 4),
              const Text('Original',
                  style: TextStyle(fontSize: 11, color: Colors.black54)),
              const SizedBox(width: 12),
              _legendDot(Colors.teal[400]!),
              const SizedBox(width: 4),
              const Text('Optimized',
                  style: TextStyle(fontSize: 11, color: Colors.black54)),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 180,
            child: BarChart(
              BarChartData(
                maxY: maxY,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (v) =>
                      FlLine(color: Colors.grey[200]!, strokeWidth: 1),
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  topTitles:
                      const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles:
                      const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 36,
                      getTitlesWidget: (value, _) => Text(
                        'Rs.${value.toInt()}',
                        style: const TextStyle(
                            fontSize: 9, color: Colors.black45),
                      ),
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 28,
                      getTitlesWidget: (value, _) {
                        final idx = value.toInt();
                        if (idx < 0 || idx >= labels.length) {
                          return const SizedBox();
                        }
                        return Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            labels[idx],
                            style: const TextStyle(
                                fontSize: 9, color: Colors.black54),
                            overflow: TextOverflow.ellipsis,
                          ),
                        );
                      },
                    ),
                  ),
                ),
                barGroups: groups,
                barTouchData: BarTouchData(enabled: true),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _legendDot(Color color) {
    return Container(
      width: 12,
      height: 12,
      decoration: BoxDecoration(
          color: color, borderRadius: BorderRadius.circular(3)),
    );
  }

  // ── Current hour active appliances ───────────────────────────────────────
  Widget _buildCurrentHourCard(
      Map<String, List<int>> schedules, int currentHour) {
    if (schedules.isEmpty) return const SizedBox();

    final active = <String>[];
    final inactive = <String>[];

    schedules.forEach((name, arr) {
      final isOn = arr.length > currentHour && arr[currentHour] == 1;
      if (isOn) {
        active.add(name);
      } else {
        inactive.add(name);
      }
    });

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 3))
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.access_time, color: Colors.teal, size: 20),
              const SizedBox(width: 8),
              Text(
                'Status at ${currentHour.toString().padLeft(2, '0')}:00',
                style: const TextStyle(
                    fontSize: 15, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (active.isNotEmpty) ...[
            Text('🟢 Active Now (${active.length})',
                style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Colors.green)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: active.map((n) => _applianceChip(n, true)).toList(),
            ),
            const SizedBox(height: 12),
          ],
          if (inactive.isNotEmpty) ...[
            Text('⚫ Inactive (${inactive.length})',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey[600])),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: inactive.map((n) => _applianceChip(n, false)).toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _applianceChip(String name, bool active) {
    return Chip(
      avatar: Icon(
        _getApplianceIcon(name),
        size: 16,
        color: active ? Colors.teal : Colors.grey,
      ),
      label: Text(
        _formatName(name),
        style: TextStyle(
            fontSize: 11,
            color: active ? Colors.teal[800] : Colors.grey[600]),
      ),
      backgroundColor:
          active ? Colors.teal[50] : Colors.grey[100],
      side: BorderSide(
          color: active ? Colors.teal[200]! : Colors.grey[300]!),
      padding: EdgeInsets.zero,
    );
  }

  // ── Custom command ─────────────────────────────────────────────────────────
  Widget _buildCustomCommandCard(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const CustomCommandPage()),
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: const [
            BoxShadow(
                color: Colors.black12, blurRadius: 8, offset: Offset(0, 4))
          ],
        ),
        child: Row(
          children: const [
            Icon(Icons.keyboard_alt, size: 32, color: Colors.teal),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Send a Custom Command',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
            Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
          ],
        ),
      ),
    );
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  String _formatName(String name) {
    return name
        .replaceAll('_Power', '')
        .replaceAll('_', ' ')
        .replaceAllMapped(
          RegExp(r'([a-z])([A-Z])'),
          (m) => '${m.group(1)} ${m.group(2)}',
        );
  }

  String _shortName(String name) {
    return name
        .replaceAll('_Power', '')
        .replaceAll('WashingMachine', 'Washer')
        .replaceAll('VehicleCharger', 'EV')
        .replaceAll('VacuumCleaner', 'Vacuum')
        .replaceAll('Heater', 'Heater')
        .replaceAll('AC', 'AC');
  }

  IconData _getApplianceIcon(String appliance) {
    final name = appliance.toLowerCase();
    if (name.contains('washing')) return Icons.local_laundry_service;
    if (name.contains('heater')) return Icons.local_fire_department;
    if (name.contains('ac')) return Icons.ac_unit;
    if (name.contains('vehicle') || name.contains('charger')) {
      return Icons.electric_car;
    }
    if (name.contains('vacuum')) return Icons.cleaning_services;
    return Icons.devices;
  }
}
