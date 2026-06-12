import 'package:flutter/material.dart';

class CustomCommandPage extends StatefulWidget {
  const CustomCommandPage({super.key});

  @override
  State<CustomCommandPage> createState() => _CustomCommandPageState();
}

class _CustomCommandPageState extends State<CustomCommandPage> {
  final TextEditingController _commandController = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _commandController.dispose();
    super.dispose();
  }

  Future<void> _sendCommand() async {
    final commandText = _commandController.text.trim();
    if (commandText.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please type a custom command first.')),
      );
      return;
    }

    setState(() {
      _sending = true;
    });

    await Future.delayed(const Duration(milliseconds: 400));

    if (!mounted) return;

    setState(() {
      _sending = false;
      _commandController.clear();
    });

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('Command sent: "$commandText"')));

    // TODO: Replace this with actual command send logic, e.g. API call or MQTT publish.
    debugPrint('Custom command sent: $commandText');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Custom Commands'),
        backgroundColor: Colors.teal,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Type a custom command and send it to your edge controller.',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _commandController,
              maxLines: 4,
              decoration: InputDecoration(
                labelText: 'Enter command',
                hintText: 'e.g. Turn on the AC in 5 minutes',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
                fillColor: Colors.white,
              ),
              textInputAction: TextInputAction.newline,
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _sending ? null : _sendCommand,
              icon: _sending
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.send),
              label: Text(_sending ? 'Sending...' : 'Send Command'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Example commands',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              '- Turn on the AC in 5 minutes\n- Set living room light to 30%\n- Start charging the battery at 10:00 PM',
              style: TextStyle(fontSize: 14, color: Colors.black87),
            ),
          ],
        ),
      ),
    );
  }
}
