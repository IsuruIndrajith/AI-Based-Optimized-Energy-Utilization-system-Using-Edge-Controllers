# Flutter API Endpoint Update Guide

## Current Endpoint (Google Cloud Run)
```dart
https://energy-api-632525537450.asia-south1.run.app/analysis
```

## New Endpoints (Firestore-based)

### Option 1: Local Development (Your Computer)
When running `python backend/server_firestore.py` on your local machine:

#### For Android Emulator
```dart
// In lib/pages/predictions_page.dart
final response = await http.get(
  Uri.parse("http://10.0.2.2:8080/analysis"),  // 10.0.2.2 is the emulator's way to access host
);
```

#### For Physical Device (On Same Network)
1. Find your PC's IP address:
   ```powershell
   # Windows: Run in PowerShell
   ipconfig  # Look for IPv4 Address (e.g., 192.168.1.100)
   ```

2. Update Flutter:
   ```dart
   // Replace 192.168.1.100 with YOUR actual IP
   final response = await http.get(
     Uri.parse("http://192.168.1.100:8080/analysis"),
   );
   ```

---

### Option 2: Production Deployment (Google Cloud Run)

#### Deploy the Firestore API
1. Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install
2. Authenticate:
   ```powershell
   gcloud auth login
   gcloud config set project your-firebase-project-id
   ```
3. Deploy:
   ```powershell
   cd backend
   gcloud run deploy energy-api-firestore `
     --source . `
     --region asia-south1 `
     --allow-unauthenticated `
     --set-env-vars FLASK_ENV=production
   ```
4. Copy the deployed URL from output (e.g., `https://energy-api-firestore-xyz.asia-south1.run.app`)
5. Update Flutter:
   ```dart
   final response = await http.get(
     Uri.parse("https://energy-api-firestore-xyz.asia-south1.run.app/analysis"),
   );
   ```

---

## Complete Updated Code

### predictions_page.dart (Full Update)

Replace the `fetchApplianceData()` method:

```dart
Future<void> fetchApplianceData() async {
  try {
    // ========================================
    // CHOOSE YOUR ENDPOINT:
    // ========================================
    
    // Local (Android emulator)
    const apiUrl = "http://10.0.2.2:8080/analysis";
    
    // OR Local (physical device) - replace 192.168.1.100 with your PC's IP
    // const apiUrl = "http://192.168.1.100:8080/analysis";
    
    // OR Production Cloud Run
    // const apiUrl = "https://energy-api-firestore-xyz.asia-south1.run.app/analysis";
    
    // ========================================
    
    final response = await http.get(Uri.parse(apiUrl));
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      
      if (data is Map<String, dynamic>) {
        setState(() {
          // Filter out 'updated_at' field if present
          appliances = data.entries
            .where((entry) => entry.key != 'updated_at')
            .map<Map<String, dynamic>>((entry) {
              final value = entry.value;
              return {
                'name': entry.key,
                'original_cost': value != null && value['original_cost'] != null
                    ? value['original_cost']
                    : 0,
                'optimized_cost':
                    value != null && value['optimized_cost'] != null
                        ? value['optimized_cost']
                        : 0,
                'savings': value != null && value['savings'] != null
                    ? value['savings']
                    : 0,
              };
            })
            .toList();
          loading = false;
        });
      } else {
        print(
          "Unexpected response type: ${data.runtimeType} -> $data",
        );
        setState(() {
          appliances = [];
          loading = false;
        });
      }
    } else {
      print("API returned ${response.statusCode}: ${response.body}");
      setState(() {
        appliances = [];
        loading = false;
      });
    }
  } catch (e, st) {
    print("Error fetching data: $e\n$st");
    setState(() {
      appliances = [];
      loading = false;
    });
  }
}
```

---

## Testing Your Endpoint

### Test Locally
```powershell
# While server_firestore.py is running:
curl http://localhost:8080/analysis
curl http://localhost:8080/schedules
curl http://localhost:8080/health
```

### Test from Flutter

#### Android Emulator
1. Start the emulator
2. Start your Flask server: `python backend/server_firestore.py`
3. Run: `flutter run`
4. Check console output for API responses

#### Physical Device (WiFi)
1. Connect device to same WiFi as your PC
2. Find your PC's IP: `ipconfig` (e.g., 192.168.1.100)
3. Update Flutter code with that IP
4. Run: `flutter run`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Connection refused` | Flask server not running. Start it: `python backend/server_firestore.py` |
| `No route to host` | Wrong IP address. Run `ipconfig` and use correct IPv4 |
| Emulator can't reach host | Use `10.0.2.2` instead of `localhost` |
| Firestore error | Ensure `serviceAccountKey.json` is at project root |
| `analysis/latest` not found | Run `python src/agent/agent.py` to populate Firestore |
| API returns 404 | Collection/document doesn't exist in Firestore yet |

---

## Summary

**Replace this:**
```dart
final response = await http.get(
  Uri.parse("https://energy-api-632525537450.asia-south1.run.app/analysis"),
);
```

**With one of these:**
```dart
// Local development
final response = await http.get(Uri.parse("http://10.0.2.2:8080/analysis"));

// OR production
final response = await http.get(
  Uri.parse("https://your-deployed-api.asia-south1.run.app/analysis")
);
```
