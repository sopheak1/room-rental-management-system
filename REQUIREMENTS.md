# Room Rental Management System — Requirements

**Project:** room-rental-management-system  
**GitHub:** https://github.com/sopheak1/room-rental-management-system  
**Created:** 2026-05-28  
**Last Updated:** 2026-05-31  
**Owner:** Sopheak  
**Stack:** Python 3.9 · Flask · SQLite · Bootstrap 5 · SQLAlchemy · Flask-Login

---

## Overview

A mobile-first web-based room rental management system designed to be used primarily on a phone. Supports Khmer and English with a language toggle. Built for a single admin managing multiple rental buildings.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python 3.9 + Flask | Blueprints per module |
| Database | SQLite via SQLAlchemy ORM | Single-admin, no concurrent writes. Migrate to PostgreSQL if scale grows. |
| Frontend | HTML + Bootstrap 5 | Mobile-first card layout |
| UI Language | Khmer + English | Toggle in navbar, stored in session |
| Thermal Print | Playwright → PNG → ESC/POS bitmap | ReportLab/WeasyPrint cannot shape Khmer. Browser renders correctly. |
| Android App | Java (Android WebView + Bluetooth SPP) | Print Bridge companion app |
| Auth | Flask-Login | Session-based, single admin |
| Password Hash | `pbkdf2:sha256` | scrypt unavailable on Python 3.9 / macOS |
| Port | 8080 | Port 5000 conflicts with AirPlay on macOS |

---

## Currency

- **System currency: ៛ (Khmer Riel)** — all amounts stored as integers
- Exchange rate: **1 USD = 4,000 ៛** (`config.py → EXCHANGE_RATE`)
- Receipt print: ៛ primary for all line items; USD secondary `(≈ $xx.xx)` for grand total
- Template filters: `|khr` → `200,000 ៛` · `|usd` → `$50.00`

---

## UI Design Principles

- **Mobile-first** — designed for phone use, not desktop
- **Card-based layout** — no tables on mobile, everything is tap-friendly cards
- **Collapsible sections** — less-used fields (room info, late fee, discount) hidden by default
- **Sticky action bars** — save/generate buttons always visible at bottom
- **Scrollable filter chips** — quick status/building filters
- **Large inputs** — 48px+ touch targets, `1rem+` font size

---

## Modules & Features

### 1. Authentication
- Login with username + password (Flask-Login, session-based)
- All pages protected — redirect to login if not authenticated
- CLI command to create admin: `flask create-admin`

### 2. Dashboard (Mobile Home)
- **3 tabs**: ⚠️ Overdue · 🕐 Upcoming · ✅ Paid
- Only shows rooms **with receipts** for current month (no receipt = excluded)
- Gradient header with month name + collection stats
- Each card: Room # · Building · Tenant · Amount — tap → receipt detail
- Big "Generate Receipt" button always at top

### 3. Building Management
- Add / Edit / Delete building (name + address)
- Mobile card list with inline edit/delete buttons

### 4. Room Management
- Add / Edit room with fields: Building, Room #, Floor, Type, Price (៛), Deposit (៛), Status
- Status: Available / Occupied / Maintenance
- Room detail: 3 tabs — Tenant · Receipts · History
- Scrollable status/building filter chips on list screen

### 5. Tenant Management

#### 5.1 Tenant Info
- Name, Gender, NID, Phone, Roommates
- Emergency contact (collapsed by default in form)
- Move-in date, Contract duration, Deposit paid (all in ៛)

#### 5.2 Due Date Logic
- **Payment due day = day of tenant's move-in date**
- Example: moved in on 10th → pays on 10th every month
- Auto-updates when move-in date is edited (with warning)

#### 5.3 Tenant History
- Checkout records: name, move-in, move-out, deposit refunded, reason

### 6. Utility Price Management
- Set price per unit for Water (m³) and Electricity (kWh) — in ៛
- Price history kept (never deleted when updated)
- Same-day tiebreaker: most recently inserted row wins (`id DESC`)
- Current price auto-fills receipt generation

### 7. Receipt Management

#### 7.1 Receipt List
- Scrollable filter chips: month/year, status (Unpaid / Partial / Paid)
- Cards with left-border colour by status
- Overdue alert banner at top

#### 7.2 Generate Receipt (Mobile-optimised)
- **Room Info section**: collapsed by default (tenant, price, previous readings)
- **Electricity**: defaults to Direct Input (override) mode
- **Water**: defaults to meter reading mode
- **From (previous)**: auto-filled from previous receipt's `electricity_to`/`water_to`
- Warning message appears if auto-filled fields are changed
- **Due Balance**: always visible (auto-filled from previous receipt)
- **Late Fee & Discount**: collapsed by default ("optional" label)
- Money inputs: auto-format with commas as you type
- **Sticky bottom bar**: running total + Generate button always visible
- Previous receipt info: yellow reference card + "View Full Receipt" modal

#### 7.3 Receipt Detail (Mobile)
- Big amount display at top
- Collapsible sections: Tenant Info · Line Items · Payment Panel · Payment Log
- Bluetooth print button in header → calls Android bridge or localhost:9100

#### 7.4 Payment Features
- Status: Unpaid / Partial / Paid / **Deferred**
- **Partial payment**: cumulative — each payment adds to `paid_amount`
- **Payment Log**: per-receipt history of all payments made
- **Defer to next month**: hides from overdue report, balance still carries over
- Remaining balance auto-carries as "Due Balance" on next month's receipt

#### 7.5 Receipt Number Format
- `RCP-YYYYMM-XXXX` (e.g. `RCP-202605-0001`)

#### 7.6 Thermal Receipt Print (58mm, Khmer)
- **Playwright** renders `print.html` (Noto Sans Khmer) → PNG at 2× scale
- **PIL** scales image to 384 dots wide (48mm at 203 DPI)
- **python-escpos** formats as ESC/POS bitmap
- `/receipts/<id>/escpos` endpoint returns raw bytes
- **Khmer-only labels** on receipt
- ៛ primary · `≈ $xx.xx` secondary for grand total
- Font: Noto Sans Khmer 400 weight, 16px base

### 8. Reports

#### 8.1 Monthly Summary Report (Mobile)
- Filter by any month/year via scrollable chips + year prev/next
- Collection rate progress bar
- Stat chips: Total · Paid · Pending · Deferred
- Receipts grouped: Unpaid/Partial first → Paid → Deferred
- Each card links to receipt detail

#### 8.2 Revenue Report
- Annual view, filter by year
- Monthly table: Expected · Collected · Outstanding · Count · Rate

#### 8.3 Overdue Report
- 3 sections: Current Month Overdue · Current Month Upcoming · Past Months Overdue
- Uses tenant start date as due day
- Deferred receipts excluded
- Generate/Pay buttons per row

#### 8.4 Occupancy Report
- Per-building: Total · Occupied · Vacant · Maintenance · Rate

### 9. Android Print Bridge App

#### Architecture
```
Android App (WebView + Bluetooth)
  ├── WebView → loads Flask web app (configurable server URL)
  ├── JavascriptInterface → Android.print(receiptId)
  ├── Fetches /receipts/<id>/escpos using WebView session cookie
  └── Sends ESC/POS bytes to PT-210 via Bluetooth SPP
```

#### Features
- Full-screen WebView showing the web app
- Bottom bar: bridge status + reload + settings
- Settings dialog: Server URL (configurable, no rebuild needed) + printer selection + bridge toggle
- NanoHTTPD server on port 9100 (fallback for Chrome browser)
- Auto-starts bridge on launch if printer was previously configured
- Back button navigates WebView history

#### Printer
- **Model**: Goojprt PT-210
- **Paper**: 58mm, 48mm print area, 203 DPI (384 dots wide)
- **Protocol**: Bluetooth Classic SPP (UUID: 00001101-...)
- **Language**: Khmer via image mode (not text mode)

---

## Data Models

```
users
  id, username, password_hash, full_name, created_at

buildings
  id, name, address, created_at

rooms
  id, building_id, room_number, floor, room_type, price, deposit_amount, status, created_at

tenants
  id, room_id, name, gender, nid, tel, emergency_contact_name, emergency_contact_tel,
  num_roommates, contract_duration, move_in_date, deposit_paid, is_active, created_at

tenant_history
  id, room_id, name, gender, nid, tel, num_roommates, move_in_date, move_out_date,
  move_out_reason, deposit_paid, deposit_refunded, created_at

utility_prices
  id, utility_type (water/electricity), price_per_unit (Float ៛), effective_date, created_at

receipts
  id, receipt_number, room_id, tenant_id, billing_month, billing_year,
  room_price, electricity_from, electricity_to, electricity_units,
  electricity_price_per_unit, electricity_total, water_from, water_to,
  water_units, water_price_per_unit, water_total, previous_balance, late_fee,
  discount, total_amount, paid_amount, remaining_balance,
  payment_status (unpaid/paid/partial/deferred), payment_method, payment_date,
  notes, created_at

payment_logs
  id, receipt_id, amount, payment_method, payment_date, created_at
```

---

## Decisions Log

| # | Decision | Reason |
|---|---|---|
| 1 | Currency in ៛ | Local market; USD shown as secondary reference only |
| 2 | Browser print → Playwright ESC/POS | ReportLab/WeasyPrint cannot shape Khmer complex script |
| 3 | Android companion app | No browser API for direct Bluetooth SPP; avoids third-party print apps |
| 4 | 58mm paper | Goojprt PT-210 uses 58mm, not 80mm |
| 5 | Khmer via image mode | Thermal printers have no Khmer ROM; image mode works on any ESC/POS printer |
| 6 | Due day = move-in day | Natural for tenants; no extra field needed |
| 7 | Most recent prev receipt (not just prev month) | Handles skipped months correctly |
| 8 | `is not none` check for meter readings | `0.0` is falsy; explicit none check prevents missing zero readings |
| 9 | Electricity defaults to Direct Input | Most landlords enter total directly, not meter readings |
| 10 | Defer status | Tenant confirms next-month payment; hides from overdue without losing balance |
| 11 | Payment log table | Track cumulative partial payments per receipt |
| 12 | SQLite | Single admin, no concurrent writes. Migrate to PostgreSQL for scale. |
| 13 | Port 8080 | Port 5000 conflicts with macOS AirPlay Receiver |
| 14 | pbkdf2:sha256 | scrypt unavailable on Python 3.9 / macOS |
| 15 | Configurable server URL in APK | No rebuild needed when moving from Mac to VPS |
| 16 | Mobile-first redesign | Primary user (mother) uses phone, not desktop |
| 17 | Language toggle (km/en) | CSS class on body + span pairs; no i18n library needed at this scale |

---

## Out of Scope (v1)

- Multi-user roles (single admin only)
- SMS / email notifications
- Online payment integration
- VPS deployment (planned for v2)
- Play Store distribution of Android app (sideload only)
