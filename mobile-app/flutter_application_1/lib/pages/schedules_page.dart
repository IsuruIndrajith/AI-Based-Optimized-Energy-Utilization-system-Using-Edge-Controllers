// lib/pages/schedules_page.dart
import 'package:flutter/material.dart';
import 'dart:async';
import '../services/firestore_service.dart';

class SchedulesPage extends StatefulWidget {
  const SchedulesPage({super.key});

  @override
  State<SchedulesPage> createState() => _SchedulesPageState();
}

class _SchedulesPageState extends State<SchedulesPage> {
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
      final data = await FirestoreService.fetchSchedules();
      setState(() {
        schedules = data;
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
        title: const Text('Energy Schedules'),
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
              : _buildSchedulesView(),
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
          Text('Failed to load schedules',
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

  Widget _buildSchedulesView() {
    if (schedules.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.info_outline, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            Text('No schedules available',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            const Text('Run the optimization agent to generate schedules.'),
          ],
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Legend card
        _buildLegendCard(),
        const SizedBox(height: 16),
        // Per-appliance schedule cards
        ...schedules.entries.map((entry) {
          return _buildApplianceScheduleCard(entry.key, entry.value);
        }),
        const SizedBox(height: 80),
      ],
    );
  }

  Widget _buildLegendCard() {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            const Icon(Icons.schedule, color: Colors.teal),
            const SizedBox(width: 10),
            Text(
              'Optimized 24-Hour Appliance Schedules',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildApplianceScheduleCard(String appliance, List<int> schedule) {
    final onHours = <int>[];
    for (int i = 0; i < schedule.length; i++) {
      if (schedule[i] == 1) onHours.add(i);
    }
    final totalOn = onHours.length;
    final totalOff = 24 - totalOn;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 3,
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
                // ON/OFF badges
                _buildBadge('$totalOn ON', Colors.green),
                const SizedBox(width: 6),
                _buildBadge('$totalOff OFF', Colors.grey),
              ],
            ),
            const SizedBox(height: 16),

            // 24-hour grid
            _build24HourGrid(schedule),
            const SizedBox(height: 14),

            // Active hours chips
            if (onHours.isNotEmpty) ...[
              Text(
                'Active Hours:',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey[700],
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: onHours.map((h) {
                  return Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.teal[600],
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '${h.toString().padLeft(2, '0')}:00',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ] else
              Text(
                'No active hours scheduled',
                style: TextStyle(color: Colors.grey[500], fontSize: 13),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: color == Colors.grey ? Colors.grey[700] : color,
        ),
      ),
    );
  }

  Widget _build24HourGrid(List<int> schedule) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Hour labels row (0, 6, 12, 18, 23)
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: ['00', '06', '12', '18', '23']
              .map((h) => Text(h,
                  style: TextStyle(fontSize: 10, color: Colors.grey[500])))
              .toList(),
        ),
        const SizedBox(height: 4),
        // Grid of 24 cells (2 rows × 12 columns)
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 12,
            crossAxisSpacing: 3,
            mainAxisSpacing: 3,
            childAspectRatio: 1,
          ),
          itemCount: 24,
          itemBuilder: (context, index) {
            final isOn = index < schedule.length && schedule[index] == 1;
            return Tooltip(
              message:
                  '${index.toString().padLeft(2, '0')}:00 — ${isOn ? 'ON ✓' : 'OFF'}',
              child: Container(
                decoration: BoxDecoration(
                  color: isOn ? Colors.teal[500] : Colors.grey[200],
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: isOn ? Colors.teal[700]! : Colors.grey[300]!,
                    width: 0.5,
                  ),
                ),
                child: Center(
                  child: Text(
                    index.toString().padLeft(2, '0'),
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: isOn ? Colors.white : Colors.grey[500],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
        const SizedBox(height: 8),
        // Legend
        Row(
          children: [
            _legendDot(Colors.teal[500]!),
            const SizedBox(width: 4),
            Text('Active (ON)',
                style: TextStyle(fontSize: 11, color: Colors.grey[600])),
            const SizedBox(width: 16),
            _legendDot(Colors.grey[300]!),
            const SizedBox(width: 4),
            Text('Inactive (OFF)',
                style: TextStyle(fontSize: 11, color: Colors.grey[600])),
          ],
        ),
      ],
    );
  }

  Widget _legendDot(Color color) {
    return Container(
      width: 14,
      height: 14,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(3),
      ),
    );
  }

  String _formatName(String name) {
    // "WashingMachine_Power" → "Washing Machine"
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
