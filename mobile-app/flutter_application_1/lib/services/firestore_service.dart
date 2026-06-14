// lib/services/firestore_service.dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class FirestoreService {
  static const String baseUrl =
      'https://energy-api-632525537450.asia-south1.run.app';

  /// Fetch analysis data (cost savings per appliance).
  /// Returns a Map like: { "WashingMachine_Power": { "original_cost": 205.8, ... }, ... }
  static Future<Map<String, dynamic>> fetchAnalysis() async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/analysis'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        // Unwrap nested 'analysis' key if present
        if (data is Map<String, dynamic> && data.containsKey('analysis')) {
          return data['analysis'] as Map<String, dynamic>;
        }
        return data as Map<String, dynamic>;
      } else {
        throw Exception('Failed to fetch analysis: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching analysis: $e');
    }
  }

  /// Fetch schedules data.
  /// Handles two formats from the API:
  ///   1. Firestore/JSON format: { "WashingMachine": [1,0,0,...], ... }
  ///   2. Legacy text format:    { "schedules": "--- WashingMachine_Power ---\nStates: [1,0,...]" }
  static Future<Map<String, List<int>>> fetchSchedules() async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/schedules'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        Map<String, List<int>> schedules = {};

        if (data is Map<String, dynamic>) {
          // ── Case 1: legacy text-blob format ─────────────────────────────
          // The API returns { "schedules": "<multiline text>" }
          if (data.containsKey('schedules') && data['schedules'] is String) {
            schedules = _parseTextSchedules(data['schedules'] as String);
          } else {
            // ── Case 2: Firestore/JSON format ────────────────────────────
            // Possibly nested under 'schedules' key as a map, or flat map
            final raw = data.containsKey('schedules') && data['schedules'] is Map
                ? data['schedules'] as Map<String, dynamic>
                : data;

            raw.forEach((key, value) {
              // Skip non-schedule fields like 'updated_at', 'error'
              if (value is List) {
                schedules[key] = List<int>.from(
                  value.map((e) => (e as num).toInt()),
                );
              }
            });
          }
        }

        return schedules;
      } else {
        throw Exception('Failed to fetch schedules: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching schedules: $e');
    }
  }

  /// Parse the legacy text format produced by server.py (reads output.txt).
  /// Input example:
  ///   "Optimised Appliance Schedules (24-hour ON/OFF)\n\n--- WashingMachine_Power ---\nStates: [1, 1, 0, ...]\n\n..."
  static Map<String, List<int>> _parseTextSchedules(String text) {
    final result = <String, List<int>>{};
    // Match every appliance block: "--- Name ---\nStates: [...]"
    final blockRegex = RegExp(
      r'---\s*(.+?)\s*---\s*\n\s*States:\s*(\[[^\]]+\])',
      multiLine: true,
    );
    for (final match in blockRegex.allMatches(text)) {
      final name = match.group(1)!.trim();
      final arrayText = match.group(2)!;
      try {
        final nums = arrayText
            .replaceAll('[', '')
            .replaceAll(']', '')
            .split(',')
            .map((s) => int.parse(s.trim()))
            .toList();
        result[name] = nums;
      } catch (_) {
        // Skip malformed entries
      }
    }
    return result;
  }

  /// Fetch both analysis and schedules data combined.
  static Future<Map<String, dynamic>> fetchCombinedData() async {
    try {
      final analysisData = await fetchAnalysis();
      final schedulesData = await fetchSchedules();

      return {
        'analysis': analysisData,
        'schedules': schedulesData,
        'timestamp': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      throw Exception('Error fetching combined data: $e');
    }
  }

  /// Convenience: compute summary totals across all appliances for the Home page.
  static Map<String, double> computeSummary(Map<String, dynamic> analysis) {
    double totalOriginal = 0;
    double totalOptimized = 0;
    double totalSavings = 0;

    analysis.forEach((key, value) {
      if (value is Map<String, dynamic>) {
        totalOriginal += (value['original_cost'] as num?)?.toDouble() ?? 0;
        totalOptimized += (value['optimized_cost'] as num?)?.toDouble() ?? 0;
        totalSavings += (value['savings'] as num?)?.toDouble() ?? 0;
      }
    });

    return {
      'original': totalOriginal,
      'optimized': totalOptimized,
      'savings': totalSavings,
      'savingsPercent': totalOriginal > 0 ? (totalSavings / totalOriginal * 100) : 0.0,
    };
  }
}
