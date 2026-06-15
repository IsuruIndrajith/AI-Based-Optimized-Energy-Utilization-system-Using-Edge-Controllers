// lib/pages/dashboard_page.dart
import 'package:flutter/material.dart';
import 'dart:async';
import '../services/firestore_service.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, dynamic> combinedData = {};
  bool loading = true;
  String? errorMessage;
  DateTime? lastUpdated;

  @override
  void initState() {
    super.initState();
    fetchData();

    // Re-fetch every 15 minutes for dashboard
    Timer.periodic(const Duration(minutes: 15), (timer) {
      fetchData();
    });
  }

  Future<void> fetchData() async {
    try {
      setState(() {
        loading = true;
        errorMessage = null;
      });

      final data = await FirestoreService.fetchCombinedData();
      setState(() {
        combinedData = data;
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
      appBar: AppBar(
        title: const Text('Energy Dashboard'),
        backgroundColor: Colors.teal,
        elevation: 0,
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : errorMessage != null
          ? _buildErrorWidget()
          : _buildDashboard(),
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
          Text(
            'Failed to load dashboard',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              errorMessage ?? 'Unknown error',
              textAlign: TextAlign.center,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: Colors.red),
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

  Widget _buildDashboard() {
    final analysis = combinedData['analysis'] as Map<String, dynamic>? ?? {};

    if (analysis.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.info_outline, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              'No data available',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text('Run the optimization to see results.'),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: fetchData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (lastUpdated != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Row(
                children: [
                  const Icon(Icons.schedule, size: 16, color: Colors.grey),
                  const SizedBox(width: 8),
                  Text(
                    'Last update: ${lastUpdated!.hour.toString().padLeft(2, '0')}:${lastUpdated!.minute.toString().padLeft(2, '0')}',
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.grey),
                  ),
                ],
              ),
            ),
          _buildKPICard(analysis),
          const SizedBox(height: 24),
          Text(
            'Devices Status',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          ..._buildDeviceRows(analysis),
        ],
      ),
    );
  }

  Widget _buildKPICard(Map<String, dynamic> analysis) {
    double totalOriginal = 0;
    double totalOptimized = 0;
    double totalSavings = 0;
    int deviceCount = 0;

    analysis.forEach((key, value) {
      if (value is Map<String, dynamic> && key != 'updated_at') {
        deviceCount++;
        final original = (value['original_cost'] as num?)?.toDouble() ?? 0;
        final optimized = (value['optimized_cost'] as num?)?.toDouble() ?? 0;
        final savings = (value['savings'] as num?)?.toDouble() ?? 0;
        totalOriginal += original;
        totalOptimized += optimized;
        totalSavings += savings;
      }
    });

    final savingsPercent = totalOriginal > 0
        ? (totalSavings / totalOriginal * 100)
        : 0;

    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: 4,
      color: Colors.teal[50],
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Overall Savings',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(color: Colors.grey[700]),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Rs.${totalSavings.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: Colors.green,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${savingsPercent.toStringAsFixed(1)}% reduction',
                      style: TextStyle(fontSize: 14, color: Colors.green[700]),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '$deviceCount devices',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'optimized',
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildDeviceRows(Map<String, dynamic> analysis) {
    final devices = analysis.entries
        .where((e) => e.key != 'updated_at')
        .toList();

    return devices.map((entry) {
      final name = entry.key;
      final data = entry.value as Map<String, dynamic>? ?? {};
      final original = (data['original_cost'] as num?)?.toDouble() ?? 0;
      final optimized = (data['optimized_cost'] as num?)?.toDouble() ?? 0;
      final savings = (data['savings'] as num?)?.toDouble() ?? 0;
      final percent = original > 0 ? (savings / original * 100) : 0;

      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.grey[50],
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey[200]!),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.teal[100],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  _getApplianceIcon(name),
                  color: Colors.teal,
                  size: 24,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text(
                          'Rs.${original.toStringAsFixed(2)}',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                            decoration: TextDecoration.lineThrough,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Rs.${optimized.toStringAsFixed(2)}',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Colors.green[100],
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Column(
                  children: [
                    Text(
                      'Rs.${savings.toStringAsFixed(2)}',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.green[700],
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      '${percent.toStringAsFixed(0)}%',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: Colors.green[600],
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }).toList();
  }

  IconData _getApplianceIcon(String appliance) {
    final name = appliance.toLowerCase();
    if (name.contains('washing')) return Icons.local_laundry_service;
    if (name.contains('heater')) return Icons.local_fire_department;
    if (name.contains('ac')) return Icons.ac_unit;
    if (name.contains('vehicle') || name.contains('charger'))
      return Icons.ev_charger;
    if (name.contains('vacuum')) return Icons.cleaning_services;
    return Icons.devices;
  }
}
