import 'package:flutter/material.dart';
import '../widgets/stat_card.dart';
import 'package:fl_chart/fl_chart.dart';
import 'custom_command_page.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blueGrey[50],
      appBar: AppBar(
        title: const Text("Hi User", style: TextStyle(color: Colors.black87)),
        backgroundColor: Colors.teal,
        elevation: 0,
        actions: [
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.logout, color: Colors.black87),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Box 1: Power Usage
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black12,
                    blurRadius: 8,
                    offset: Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.bolt, size: 32, color: Colors.orange),
                      SizedBox(width: 12),
                      Text(
                        "Power Usage",
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  LinearProgressIndicator(
                    value: 0.65, // example percentage
                    minHeight: 10,
                    backgroundColor: Colors.grey[200],
                    color: Colors.orange,
                  ),
                  const SizedBox(height: 6),
                  const Align(
                    alignment: Alignment.centerRight,
                    child: Text(
                      "65%",
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Box 2: 2x2 stats grid
            SizedBox(
              height: 350, // compact height
              child: GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 1.2,
                children: const [
                  StatCard(
                    title: "Energy Saved",
                    icon: Icons.bolt,
                    value: "120 kWh",
                    color: Colors.green,
                  ),
                  StatCard(
                    title: "Energy Consumed",
                    icon: Icons.energy_savings_leaf,
                    value: "450 kWh",
                    color: Colors.red,
                  ),
                  StatCard(
                    title: "Unit Pricing",
                    icon: Icons.attach_money,
                    value: "\$0.15 /kWh",
                    color: Colors.blue,
                  ),
                  StatCard(
                    title: "Unit Cost Saved",
                    icon: Icons.savings,
                    value: "\$35",
                    color: Colors.orange,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Box 3: Graph
            Container(
              height: 200, // compact height
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black12,
                    blurRadius: 8,
                    offset: Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "Consumption Prediction",
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: LineChart(
                      LineChartData(
                        gridData: FlGridData(
                          show: true,
                          drawVerticalLine: true,
                          getDrawingHorizontalLine: (value) =>
                              FlLine(color: Colors.grey[300], strokeWidth: 1),
                          getDrawingVerticalLine: (value) =>
                              FlLine(color: Colors.grey[300], strokeWidth: 1),
                        ),
                        titlesData: FlTitlesData(
                          show: true,
                          bottomTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 28,
                              getTitlesWidget: (value, meta) => Text(
                                "Day ${value.toInt() + 1}",
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.grey[600],
                                ),
                              ),
                            ),
                          ),
                          leftTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 32,
                              getTitlesWidget: (value, meta) => Text(
                                "${value.toInt()} kWh",
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.grey[600],
                                ),
                              ),
                            ),
                          ),
                        ),
                        borderData: FlBorderData(show: false),
                        lineBarsData: [
                          LineChartBarData(
                            spots: const [
                              FlSpot(0, 2),
                              FlSpot(1, 3),
                              FlSpot(2, 1.5),
                              FlSpot(3, 4),
                              FlSpot(4, 3.2),
                              FlSpot(5, 5),
                            ],
                            isCurved: true,
                            barWidth: 3,
                            color: Colors.blue,
                            dotData: FlDotData(show: true),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Box 4: Custom Command
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const CustomCommandPage(),
                  ),
                );
              },
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black12,
                      blurRadius: 8,
                      offset: Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  children: const [
                    Icon(Icons.keyboard_alt, size: 32, color: Colors.teal),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        "Send a Custom Command",
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    Icon(Icons.arrow_forward_ios, size: 18, color: Colors.grey),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
