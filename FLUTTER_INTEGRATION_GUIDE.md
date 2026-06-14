# Flutter Energy Optimization App - Integration Guide

## Overview
Your Flutter app has been updated to display the energy optimization schedules and cost savings directly from Firestore through your Flask REST API. The integration includes 3 new/updated pages with comprehensive visualizations.

---

## Data Structure (from Python Agent)

The Python backend writes to Firestore:

```json
// Firestore: analysis/latest
{
  "WashingMachine": {
    "original_cost": 50.00,
    "optimized_cost": 40.00,
    "savings": 10.00
  },
  "AC": {
    "original_cost": 120.00,
    "optimized_cost": 100.00,
    "savings": 20.00
  },
  "Heater": {
    "original_cost": 200.00,
    "optimized_cost": 150.00,
    "savings": 50.00
  },
  "updated_at": "2026-06-12T10:30:45.123Z"
}

// Firestore: schedules/latest
{
  "WashingMachine": [0,0,0,1,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  "AC": [0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,1,1,1,1,1,0,0],
  "Heater": [1,1,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0]
}
```

---

## Three Display Pages

### 1. **Dashboard Page** (NEW - Overview)
📍 File: `lib/pages/dashboard_page.dart`

**Purpose**: Quick overview of overall savings and per-device status

**Features**:
- **KPI Card**: Shows total savings amount, percentage, and device count
- **Device List**: Quick rows showing:
  - Device icon & name
  - Original cost (strikethrough)
  - Optimized cost
  - Savings amount & percentage badge

**Usage**: Add to navigation for quick status check (best for home screen)

```dart
// In your main navigation
DashboardPage()
```

---

### 2. **Predictions Page** (UPDATED - Analysis View)
📍 File: `lib/pages/predictions_page.dart`

**Purpose**: Detailed cost analysis for each device

**Features**:
- **Summary Card**: Shows total appliances, total savings, best saving %
- **Per-Device Cards** with:
  - Appliance name & icon
  - Savings badge (amount + percentage)
  - Cost boxes (Original | Optimized | Savings)
  - Progress bar showing % savings
  - Active hours section with time chips (05:00, 06:00, etc.)
  - 24-hour mini bar visualization

**Usage**: Best for detailed analysis of cost benefits

```dart
// In your main navigation
PredictionsPage()
```

---

### 3. **Schedules Page** (UPDATED - Schedule View)
📍 File: `lib/pages/schedules_page.dart`

**Purpose**: Visual 24-hour schedule for each device

**Features**:
- **Total Summary Card**: Overall original cost → optimized cost → total savings
- **Expandable Device Cards** with:
  - Device name & savings badge
  - Cost breakdown section
  - **24-hour grid visualization**: 12×2 grid showing ON (green) / OFF (gray) hours
  - Hour numbers displayed in each cell
  - Active hours as clickable chips
  - Hourly breakdown

**Usage**: Best for understanding when devices run

```dart
// In your main navigation
SchedulesPage()
```

---

## Implementation Steps

### Step 1: Add Service Layer ✅
**File Created**: `lib/services/firestore_service.dart`

This service handles all API calls:
```dart
// Fetch both data sources
final data = await FirestoreService.fetchCombinedData();
// Returns: {
//   'analysis': {...},
//   'schedules': {...},
//   'timestamp': '2026-06-12...'
// }
```

### Step 2: Update Navigation
Add the pages to your main app navigation (typically in `main.dart` or navigation file):

```dart
import 'pages/dashboard_page.dart';
import 'pages/predictions_page.dart';
import 'pages/schedules_page.dart';

// Then in your navigation/drawer:
NavigationDestination(
  icon: Icon(Icons.dashboard),
  label: 'Dashboard',
  // Navigate to DashboardPage()
),
NavigationDestination(
  icon: Icon(Icons.analytics),
  label: 'Predictions',
  // Navigate to PredictionsPage()
),
NavigationDestination(
  icon: Icon(Icons.schedule),
  label: 'Schedules',
  // Navigate to SchedulesPage()
),
```

### Step 3: Update pubspec.yaml (if needed)
Make sure you have these dependencies:
```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0  # For API calls
  # Remove if not used: fl_chart (was removed from predictions_page)
```

### Step 4: Test
1. Run your Python agent to populate Firestore
2. Start Flutter app
3. Navigate to each page
4. Pull-to-refresh or click FAB to reload data

---

## Data Flow Diagram

```
┌─────────────────┐
│  Python Agent   │
│ (agent.py)      │
└────────┬────────┘
         │
         ▼ Writes to Firestore
┌─────────────────┐
│   Firestore     │
│ analysis/latest │
│schedules/latest │
└────────┬────────┘
         │
         ▼ REST API (/analysis, /schedules)
┌─────────────────┐
│  Flask Server   │
└────────┬────────┘
         │
         ▼ HTTP GET
┌──────────────────────────────┐
│  FirestoreService            │
│ • fetchAnalysis()            │
│ • fetchSchedules()           │
│ • fetchCombinedData()        │
└────────┬─────────────────────┘
         │
         ▼ Parsed JSON
┌────────────────────────────────────┐
│  Flutter Pages                      │
│ • DashboardPage (overview)          │
│ • PredictionsPage (analysis)        │
│ • SchedulesPage (schedules)         │
└────────────────────────────────────┘
```

---

## Key Features Explained

### 24-Hour Grid Visualization
```
Each cell = 1 hour (00:00 to 23:00)
Layout: 12 columns × 2 rows = 24 cells

Green (ON)  = Device is scheduled to run
Gray (OFF)  = Device is off
Numbers    = Hour index (00, 01, 02, ... 23)
```

### Cost Calculations
```
Savings Percentage = (Savings / Original Cost) × 100

Example:
Original: ₹100
Optimized: ₹80
Savings: ₹20
% Saved: (20/100) × 100 = 20%
```

### Active Hours Display
Hours are shown as chips/badges:
```
Format: HH:00 (24-hour format)
Example: 05:00, 06:00, 18:00, 22:00
```

---

## Troubleshooting

### Issue: "Failed to load data" error
**Causes**:
1. Python agent hasn't run yet (no Firestore data)
2. Flask server is down
3. Network connectivity issue
4. CORS blocked

**Fix**:
1. Check Python agent logs
2. Verify Flask server is running: `curl https://energy-api-632525537450.asia-south1.run.app/analysis`
3. Check device network connectivity
4. Verify CORS headers in Flask

### Issue: Empty data/No appliances
**Cause**: Python agent hasn't run optimization yet

**Fix**:
```bash
# Run the agent
cd src/agent
python agent.py
# or if using shell scripts
python ../agent/agent.py
```

### Issue: Wrong currency symbol
**Solution**: Change `₹` to `LKR` in the code:
```dart
// Before
'₹${savings.toStringAsFixed(2)}'

// After
'LKR ${savings.toStringAsFixed(2)}'
```

---

## Customization Options

### Change Refresh Interval
```dart
// In each page, modify:
Timer.periodic(const Duration(minutes: 30), (timer) {
  fetchData();
});
```

### Change Currency Symbol
Search for `₹` and replace with your currency:
- LKR (Sri Lanka) = ₨
- INR (India) = ₹
- USD = $
- EUR = €

### Change Colors
The app uses `Colors.teal` as primary. Change in:
```dart
appBar: AppBar(
  backgroundColor: Colors.teal,  // Change this
)
```

### Add More Appliance Icons
Update `_getApplianceIcon()` method:
```dart
IconData _getApplianceIcon(String appliance) {
  final name = appliance.toLowerCase();
  if (name.contains('fridge')) return Icons.kitchen;
  if (name.contains('microwave')) return Icons.microwave;
  // Add more...
}
```

---

## Next Steps

1. **Test the Integration**
   - Run Python agent
   - Check Firestore has data
   - Open Flutter app and navigate to each page

2. **Add to Main Navigation**
   - Integrate pages into your app's main navigation

3. **Customize Styling** (Optional)
   - Adjust colors to match your app theme
   - Modify card layouts if needed

4. **Monitor Performance**
   - Each page refreshes every 30 minutes by default
   - Manual refresh via FAB (floating action button)
   - Loading indicator shows during fetch

---

## Support Files

- **Service**: `lib/services/firestore_service.dart` - API communication
- **Pages**: 
  - `lib/pages/dashboard_page.dart` - Overview
  - `lib/pages/predictions_page.dart` - Detailed analysis
  - `lib/pages/schedules_page.dart` - Schedule visualization
