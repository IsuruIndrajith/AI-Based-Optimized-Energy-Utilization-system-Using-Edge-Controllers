// lib/pages/predictions_page.dart
import 'package:flutter/material.dart';
import 'dart:async';
import '../services/firestore_service.dart';

class PredictionsPage extends StatefulWidget {
  const PredictionsPage({super.key});

  @override
  State<PredictionsPage> createState() => _PredictionsPageState();
}

class _PredictionsPageState extends State<PredictionsPage> {
  Map<String, dynamic> analysis = {};
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
      final data = await FirestoreService.fetchAnalysis();
      setState(() {
        // Filter out non-appliance fields like 'updated_at'
        analysis = Map.fromEntries(
          data.entries.where((e) => e.value is Map),
        );
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
        title: const Text('Cost Analysis'),
        backgroundColor: Colors.teal,
        elevation: 0,
        actions: [
          if (lastUpdated != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
              child: Text(
                'Updated ${lastUpdated!.hour.toString().padLeft(2, '0')}:${lastUpdated!.minute.toString().padLeft(2, '0')}',
                style: const TextStyle(fontSize: 12, color: Colors.white70),
              ),
            ),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : errorMessage != null
              ? _buildErrorWidget()
              : _buildAnalysisView(),
      floatingActionButton: FloatingActionButton(
        onPressed: fetchData,
        backgroundColor: Colors.teal,
        child: const Icon(Icons.refresh),
      ),
    );
  }

  Widget _buildErrorWidget() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 48, color: Colors.red),
          const SizedBox(height: 16),
          Text('Failed to load cost analysis',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              errorMessage ?? 'Unknown error',
              textAlign: TextAlign.center,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: Colors.red),
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: fetchData,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalysisView() {
    if (analysis.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.info_outline, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            Text('No cost data available',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            const Text('Run the optimization agent to generate predictions.'),
          ],
        ),
      );
    }

    final summary = FirestoreService.computeSummary(analysis);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildSummaryCard(summary),
        const SizedBox(height: 16),
        _buildBarChart(summary),
        const SizedBox(height: 16),
        ...analysis.entries.map((e) {
          final costData = e.value as Map<String, dynamic>;
          return _buildApplianceCostCard(e.key, costData);
        }),
        const SizedBox(height: 80),
      ],
    );
  }

  // ── Summary header card ────────────────────────────────────────────────────
  Widget _buildSummaryCard(Map<String, double> summary) {
    final original = summary['original']!;
    final optimized = summary['optimized']!;
    final savings = summary['savings']!;
    final percent = summary['savingsPercent']!;

    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: 4,
      color: Colors.teal[700],
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: const [
                Icon(Icons.insights, color: Colors.white, size: 26),
                SizedBox(width: 10),
                Text(
                  'Total Cost Summary',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildSummaryMetric('Original', 'Rs.${original.toStringAsFixed(0)}',
                    Colors.red[200]!),
                _buildDivider(),
                _buildSummaryMetric('Optimized', 'Rs.${optimized.toStringAsFixed(0)}',
                    Colors.blue[200]!),
                _buildDivider(),
                _buildSummaryMetric(
                    'Savings', 'Rs.${savings.toStringAsFixed(0)}', Colors.green[200]!),
              ],
            ),
            const SizedBox(height: 16),
            // Savings progress bar
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
              '${percent.toStringAsFixed(1)}% total savings achieved',
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryMetric(String label, String value, Color valueColor) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: valueColor,
          ),
        ),
        const SizedBox(height: 4),
        Text(label,
            style:
                const TextStyle(fontSize: 12, color: Colors.white60)),
      ],
    );
  }

  Widget _buildDivider() {
    return Container(width: 1, height: 40, color: Colors.white24);
  }

  // ── Horizontal bar chart card ──────────────────────────────────────────────
  Widget _buildBarChart(Map<String, double> summary) {
    final original = summary['original']!;
    final optimized = summary['optimized']!;

    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Original vs Optimized Cost',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildBar('Original', original, original, Colors.red[400]!),
            const SizedBox(height: 10),
            _buildBar('Optimized', optimized, original, Colors.teal[400]!),
          ],
        ),
      ),
    );
  }

  Widget _buildBar(String label, double value, double max, Color color) {
    final fraction = max > 0 ? (value / max).clamp(0.0, 1.0) : 0.0;
    return Row(
      children: [
        SizedBox(
          width: 80,
          child: Text(label,
              style: const TextStyle(fontSize: 12, color: Colors.black54)),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: fraction,
              backgroundColor: Colors.grey[200],
              valueColor: AlwaysStoppedAnimation<Color>(color),
              minHeight: 18,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'Rs.${value.toStringAsFixed(0)}',
          style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.bold, color: color),
        ),
      ],
    );
  }

  // ── Per-appliance cost card ────────────────────────────────────────────────
  Widget _buildApplianceCostCard(
      String appliance, Map<String, dynamic> costData) {
    final originalCost = (costData['original_cost'] as num?)?.toDouble() ?? 0;
    final optimizedCost =
        (costData['optimized_cost'] as num?)?.toDouble() ?? 0;
    final savings = (costData['savings'] as num?)?.toDouble() ?? 0;
    final savingsPercent = originalCost > 0
        ? (savings / originalCost * 100)
        : 0.0;

    final hasSavings = savings > 0;

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.teal[50],
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    _getApplianceIcon(appliance),
                    color: Colors.teal,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _formatName(appliance),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                // Savings badge
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: hasSavings ? Colors.green[50] : Colors.grey[100],
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color:
                          hasSavings ? Colors.green[300]! : Colors.grey[300]!,
                    ),
                  ),
                  child: Column(
                    children: [
                      Text(
                        'Rs.${savings.toStringAsFixed(0)} saved',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: hasSavings
                              ? Colors.green[700]
                              : Colors.grey[500],
                          fontSize: 11,
                        ),
                      ),
                      if (hasSavings)
                        Text(
                          '${savingsPercent.toStringAsFixed(1)}%',
                          style: TextStyle(
                            fontSize: 10,
                            color: Colors.green[600],
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Cost boxes
            Row(
              children: [
                _buildCostBox('Original', originalCost, Colors.red[50]!,
                    Colors.red[700]!),
                const SizedBox(width: 10),
                const Icon(Icons.arrow_forward, size: 18, color: Colors.grey),
                const SizedBox(width: 10),
                _buildCostBox('Optimized', optimizedCost, Colors.blue[50]!,
                    Colors.blue[700]!),
                const SizedBox(width: 10),
                const Text('=', style: TextStyle(fontSize: 18, color: Colors.grey)),
                const SizedBox(width: 10),
                _buildCostBox('Savings', savings, Colors.green[50]!,
                    Colors.green[700]!),
              ],
            ),
            const SizedBox(height: 14),

            // Progress bar
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: (savingsPercent / 100).clamp(0.0, 1.0),
                backgroundColor: Colors.grey[200],
                valueColor: AlwaysStoppedAnimation<Color>(
                  hasSavings ? Colors.green[600]! : Colors.grey[400]!,
                ),
                minHeight: 8,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              hasSavings
                  ? '${savingsPercent.toStringAsFixed(1)}% cost reduction'
                  : 'No savings — schedule is already optimal',
              style: TextStyle(
                fontSize: 12,
                color: hasSavings ? Colors.green[700] : Colors.grey[500],
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCostBox(
      String label, double value, Color bgColor, Color textColor) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          children: [
            Text(
              'Rs.${value.toStringAsFixed(1)}',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: textColor,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 3),
            Text(label,
                style: const TextStyle(fontSize: 10, color: Colors.black45)),
          ],
        ),
      ),
    );
  }

  String _formatName(String name) {
    return name
        .replaceAll('_Power', '')
        .replaceAll('_', ' ')
        .replaceAllMapped(
          RegExp(r'([a-z])([A-Z])'),
          (m) => '${m.group(1)} ${m.group(2)}',
        );
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
