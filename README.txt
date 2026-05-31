================================================================================
  ROOM RENTAL MANAGEMENT SYSTEM — README
  Project: room-rental-management-system
  GitHub:  https://github.com/sopheak1/room-rental-management-system
  Stack:   Python 3.9 + Flask + SQLite + Bootstrap 5
  Updated: 2026-05-31
================================================================================


--------------------------------------------------------------------------------
  HOW TO RUN THE APP (Mac / Local)
--------------------------------------------------------------------------------

Step 1 — Go to the project folder:

    cd /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system

Step 2 — Create venv (first time only):

    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
    venv/bin/playwright install chromium

Step 3 — Start the app:

    venv/bin/python run.py

Step 4 — Open in browser:

    http://localhost:8080

Step 5 — Access from phone (same WiFi):

    http://192.168.50.24:8080


--------------------------------------------------------------------------------
  LOGIN CREDENTIALS (DEFAULT)
--------------------------------------------------------------------------------

  Username : admin
  Password : admin123

  To create a new admin:
    FLASK_APP=run.py venv/bin/flask create-admin <username> <password> --name "Full Name"


--------------------------------------------------------------------------------
  QUICK START
--------------------------------------------------------------------------------

  1. Login
  2. Buildings  → Add your building (name + address)
  3. Rooms      → Add rooms (assign building, set price & deposit)
  4. Utilities  → Set Water & Electricity price per unit (in ៛)
  5. Room       → Click "Add Tenant" → fill in tenant info + move-in date
  6. Home       → See Overdue / Upcoming / Paid tabs
  7. Receipts   → Click "Generate Receipt" → select room → fill meters → generate
  8. Receipt    → Click "Print (PT-210)" to print via Android Print Bridge


--------------------------------------------------------------------------------
  ANDROID PRINT BRIDGE (PT-210 Bluetooth Printer)
--------------------------------------------------------------------------------

  The app includes an Android companion app for wireless receipt printing.

  APK location: print-bridge-android/app/build/outputs/apk/debug/app-debug.apk

  Build APK:
    cd print-bridge-android
    export ANDROID_HOME=~/Library/Android/sdk
    export JAVA_HOME=$(/usr/libexec/java_home -v 17)
    ./gradlew assembleDebug

  How to use:
    1. Install APK on Android phone
    2. Open "Print Bridge" → Select PT-210 printer → Start Bridge
    3. Minimize the app (keep running in background)
    4. Open Chrome or the Print Bridge WebView → go to any receipt
    5. Tap "Print (PT-210)" → prints instantly via Bluetooth

  Printer specs: Goojprt PT-210, 58mm paper, ESC/POS protocol
  Khmer printing: Playwright renders HTML → PNG → ESC/POS bitmap (full Khmer support)


--------------------------------------------------------------------------------
  PROJECT STRUCTURE
--------------------------------------------------------------------------------

  room-rental-management-system/
  |-- run.py                        Entry point
  |-- config.py                     App config (secret key, DB, exchange rate)
  |-- requirements.txt              Python dependencies
  |-- README.txt                    This file
  |-- REQUIREMENTS.md               Full feature specification
  |-- instance/
  |   |-- rental.db                 SQLite database (auto-created on first run)
  |-- app/
  |   |-- __init__.py               App factory + Jinja2 filters (khr, usd)
  |   |-- models.py                 DB models: User, Building, Room, Tenant,
  |   |                               TenantHistory, UtilityPrice, Receipt,
  |   |                               PaymentLog
  |   |-- routes/
  |   |   |-- auth.py               Login / Logout
  |   |   |-- dashboard.py          Mobile home (Overdue/Upcoming/Paid tabs)
  |   |   |-- buildings.py          Buildings CRUD
  |   |   |-- rooms.py              Rooms CRUD
  |   |   |-- tenants.py            Tenant add / edit / checkout
  |   |   |-- utilities.py          Utility price management
  |   |   |-- receipts.py           Receipt generation, payment, ESC/POS printing
  |   |   |-- reports.py            Summary, Revenue, Overdue, Occupancy reports
  |   |-- templates/                Mobile-first HTML templates (Khmer + English)
  |   |-- static/
  |       |-- css/style.css         Mobile-first styles + language toggle
  |       |-- js/main.js            Global JS utilities
  |-- print-bridge-android/         Android Print Bridge app (Bluetooth printing)
      |-- app/src/main/java/...     MainActivity.java, PrintServer.java
      |-- app/src/main/res/...      Layouts, manifest


--------------------------------------------------------------------------------
  KEY FEATURES
--------------------------------------------------------------------------------

  Mobile-first UI
    - Card-based layout for all screens (no tables on mobile)
    - Collapsible sections, sticky action bars, filter chips
    - Optimised for phone use (large touch targets)

  Language Toggle
    - Switch between Khmer (ខ្មែរ) and English in the navbar
    - Preference stored in session, no rebuild needed

  Dashboard (Home)
    - 3 tabs: ⚠️ Overdue · 🕐 Upcoming · ✅ Paid
    - Only shows rooms with receipts for current month
    - Tap any card → receipt detail

  Generate Receipt
    - Room info & Previous month data collapsed by default
    - Late Fee & Discount hidden (optional, expand on demand)
    - Money inputs auto-format with commas (200,000 ៛)
    - Sticky total bar always visible

  Receipt Printing
    - Android Print Bridge app (Bluetooth, no third-party app needed)
    - Full Khmer rendering via Playwright → ESC/POS bitmap
    - 58mm thermal paper (Goojprt PT-210)
    - Browser fallback via localhost:9100

  Payment Tracking
    - Partial payment carry-over to next month
    - Payment log per receipt (cumulative history)
    - Defer to next month (hides from overdue report)

  Summary Report
    - Filter by any month/year
    - Collection rate progress bar
    - Receipts grouped by status (Unpaid → Partial → Paid → Deferred)

  Due Date Logic
    - Each tenant's payment due day = day of move-in date
    - Overdue report auto-calculates based on today vs due day


--------------------------------------------------------------------------------
  CURRENCY & PRINTING
--------------------------------------------------------------------------------

  Currency     : ៛ (Khmer Riel) — all amounts stored as integers
  Exchange rate: 1 USD = 4,000 ៛ (config.py → EXCHANGE_RATE)
  Receipt print: ៛ primary, USD secondary (≈ $xx.xx) for grand total only
  Paper size   : 58mm (Goojprt PT-210)
  Font         : Noto Sans Khmer 400/700 (Google Fonts)


--------------------------------------------------------------------------------
  DATABASE
--------------------------------------------------------------------------------

  Type     : SQLite (file-based, no server needed)
  Location : instance/rental.db
  Backup   : Copy instance/rental.db to back up all data


================================================================================
  Built by: Lucy (Claude Code AI Assistant) for Sopheak
  Date:     2026-05-31
================================================================================
