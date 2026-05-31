================================================================================
  RENTAL MANAGEMENT SYSTEM — README
  Project: rental-management
  Path:    ClaudeHome/Personal/rental-management/
  Stack:   Python + Flask + SQLite + Bootstrap 5
================================================================================


--------------------------------------------------------------------------------
  HOW TO RUN THE APP
--------------------------------------------------------------------------------

Step 1 — Open terminal and go to the project folder:

    cd /Users/sopheak.l/ClaudeHome/Personal/rental-management

Step 2 — Start the app:

    venv/bin/python run.py

Step 3 — Open your browser and go to:

    http://localhost:8080


--------------------------------------------------------------------------------
  LOGIN CREDENTIALS (DEFAULT)
--------------------------------------------------------------------------------

  Username : admin
  Password : admin123

  NOTE: Change the password after first login if needed.


--------------------------------------------------------------------------------
  CREATE A NEW ADMIN USER (OPTIONAL)
--------------------------------------------------------------------------------

  If you need to add another admin user, run this command:

    FLASK_APP=run.py venv/bin/flask create-admin <username> <password> --name "Full Name"

  Example:

    FLASK_APP=run.py venv/bin/flask create-admin sopheak mypassword --name "Sopheak"


--------------------------------------------------------------------------------
  SUGGESTED FIRST STEPS (QUICK START)
--------------------------------------------------------------------------------

  1. Login at http://localhost:5000

  2. Go to Buildings  --> Add your first building (name + address)

  3. Go to Rooms      --> Add rooms (assign to building, set price & deposit)

  4. Go to Utilities  --> Set Water price per unit
                         Set Electricity price per unit

  5. Go to a Room     --> Click "Add Tenant" to move in a tenant

  6. Go to Receipts   --> Click "Generate Receipt"
                         Select room, fill in meter readings, generate

  7. On the receipt   --> Click "Print PDF (80mm)" to print via Bluetooth printer


--------------------------------------------------------------------------------
  PROJECT STRUCTURE
--------------------------------------------------------------------------------

  rental-management/
  |-- run.py                      <-- Entry point (start app from here)
  |-- config.py                   <-- App configuration (secret key, DB path)
  |-- requirements.txt            <-- Python dependencies
  |-- README.txt                  <-- This file
  |-- REQUIREMENTS.md             <-- Full feature requirements document
  |-- instance/
  |   |-- rental.db               <-- SQLite database (auto-created on first run)
  |-- venv/                       <-- Python virtual environment
  |-- app/
      |-- __init__.py             <-- App factory
      |-- models.py               <-- Database models (all tables)
      |-- routes/
      |   |-- auth.py             <-- Login / Logout
      |   |-- dashboard.py        <-- Dashboard
      |   |-- buildings.py        <-- Buildings CRUD
      |   |-- rooms.py            <-- Rooms CRUD
      |   |-- tenants.py          <-- Tenant add / edit / checkout
      |   |-- utilities.py        <-- Utility price management
      |   |-- receipts.py         <-- Receipt generation + payment
      |   |-- reports.py          <-- Reports (revenue, overdue, occupancy)
      |-- utils/
      |   |-- pdf.py              <-- 80mm thermal receipt PDF generator
      |-- templates/              <-- All HTML pages (Khmer + English)
      |-- static/
          |-- css/style.css       <-- Custom styles
          |-- js/main.js          <-- JavaScript utilities


--------------------------------------------------------------------------------
  MODULES AVAILABLE
--------------------------------------------------------------------------------

  Dashboard       --> Overview stats, monthly revenue, recent payments
  Buildings       --> Add / Edit / Delete buildings
  Rooms           --> Add / Edit rooms, view tenant + receipt history
  Utilities       --> Set water & electricity price per unit (with history)
  Receipts        --> Generate monthly receipts, record payments, print PDF
  Reports         --> Monthly revenue, overdue list, occupancy rate


--------------------------------------------------------------------------------
  RECEIPT FEATURES
--------------------------------------------------------------------------------

  - Auto-fills previous electricity/water meter reading from last receipt
  - Auto-calculates units used and total cost
  - Option to input final price directly (skip meter readings)
  - Auto-carries due balance from previous month
  - Supports: Paid / Partial / Unpaid status
  - Remaining balance auto-carries to next month's receipt
  - PDF export formatted for 80mm Bluetooth thermal receipt printer


--------------------------------------------------------------------------------
  DATABASE
--------------------------------------------------------------------------------

  Database type : SQLite (file-based, no server needed)
  Location      : instance/rental.db
  Backup        : Simply copy the rental.db file to back up all data


--------------------------------------------------------------------------------
  REINSTALL DEPENDENCIES (IF NEEDED)
--------------------------------------------------------------------------------

  If venv is missing or broken, recreate it:

    python3 -m venv venv
    venv/bin/pip install -r requirements.txt


================================================================================
  Built by: Lucy (Claude Code) for Sopheak — QA Tester
  Date:     2026-05-28
================================================================================
