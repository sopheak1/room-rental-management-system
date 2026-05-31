# Rental Management System — Requirements

**Project:** rental-management  
**Path:** ClaudeHome/Personal/rental-management/  
**Created:** 2026-05-28  
**Last Updated:** 2026-05-28  
**Owner:** Sopheak  
**Stack:** Python 3.9 · Flask · SQLite · Bootstrap 5 · SQLAlchemy · Flask-Login

---

## Overview

A web-based room rental management system with mobile-responsive UI.  
Supports Khmer and English. Designed for small-to-medium rental buildings.  
Accessible on mobile via local network (same WiFi).

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python 3.9 + Flask | Blueprints per module |
| Database | SQLite via SQLAlchemy ORM | Good for single-admin, small scale. Migrate to PostgreSQL if scale grows. |
| Frontend | HTML + Bootstrap 5 | Mobile responsive |
| UI Language | Khmer + English | Bilingual labels throughout the app |
| Receipt Print | Browser-based HTML (`@page { size: 80mm auto }`) | PDF libraries (ReportLab, WeasyPrint) do not support Khmer complex script shaping. Browser (HarfBuzz engine) renders Khmer correctly. |
| Receipt Language | Khmer only | Thermal receipt is Khmer-only labels |
| Auth | Flask-Login | Session-based, single admin |
| Password Hash | `pbkdf2:sha256` | `scrypt` unavailable on Python 3.9 / macOS |
| Port | 8080 | Port 5000 conflicts with AirPlay on macOS |

---

## Currency

- **System currency: ៛ (Khmer Riel)**
- All amounts stored and input in ៛ (integers)
- Exchange rate: **1 USD = 4,000 ៛** (configured in `config.py` as `EXCHANGE_RATE`)
- **Receipt print**: shows ៛ as primary for all line items; USD shown as secondary `(≈ $xx.xx)` for grand total only
- Template filters: `|khr` → formats as `200,000 ៛`; `|usd` → converts and formats as `$50.00`

---

## Modules & Features

---

### 1. Authentication

- Login with username + password
- Session-based auth (Flask-Login)
- All pages protected — redirect to login if not authenticated
- Logout
- Admin created via Flask CLI: `flask create-admin`

---

### 2. Dashboard

- Total rooms count
- Occupied rooms count
- Vacant rooms count
- Monthly revenue: collected vs expected (in ៛)
- Number of overdue rooms (unpaid from previous billing period)
- Recent payments list

---

### 3. Building Management

- Add / Edit / Delete building
- Fields:
  - Building name
  - Address

---

### 4. Room Management

- Add / Edit room
- Room status: **Available** / **Occupied** / **Maintenance**
- Fields:
  - Building (assigned to a specific building)
  - Room number
  - Floor number
  - Room type: Single / Double / Studio
  - Room price (monthly rent, in ៛)
  - Deposit amount (in ៛, collected at move-in)
- View all rooms (filterable by building, status)
- View single room detail (current tenant + history + receipts tabs)

---

### 5. Tenant Management

#### 5.1 Tenant Info (per room)

- Number of roommates
- Name
- Gender
- National ID (NID)
- Phone number (Tel)
- Emergency contact name + phone
- Contract duration (monthly / 6 months / 1 year)
- Move-in date
- Move-out date (set when tenant checks out)
- Move-out reason
- Deposit paid amount (in ៛)
- Deposit refunded amount (in ៛, set at checkout)

#### 5.2 Tenant History Log

- Every time a tenant checks out, a history record is saved
- History includes: name, NID, tel, move-in date, move-out date, move-out reason, deposit paid, deposit refunded
- Viewable per room under the History tab

---

### 6. Utility Price Management

- Set price per unit for:
  - **Electricity** (price per kWh, in ៛)
  - **Water** (price per m³, in ៛)
- Price history is kept — old prices are never deleted when updated
- Each price record has an effective date
- **Tiebreaker**: if two prices share the same effective date, the most recently inserted one (highest `id`) wins
- System auto-fills current price when generating receipts

---

### 7. Receipt Management

#### 7.1 Receipt List

- List all receipts by month/year
- Filter by: building, status (paid / unpaid / partial)
- Show overdue receipts (unpaid from a past billing period)
- Overdue section displayed separately at the bottom with a red alert banner

#### 7.2 Generate Receipt

**Page behavior:**
- Select room → page reloads with `room_id` in URL, preserving selected billing month/year
- Previous receipt is the most recent receipt for that room **before** the selected billing month (not limited to just the immediately preceding calendar month — handles skipped months)
- A **yellow reference card** displays previous month's data: Prev. Electricity reading, Prev. Water reading, Due Balance
- A **"View Full Receipt"** button opens a popup modal with the complete previous receipt (all line items, totals, payment status) — does not interrupt the generate form

**Inputs:**

| Field | Behavior |
|---|---|
| Select room | Dropdown — only occupied rooms shown |
| Billing month/year | Month + Year picker — preserved when changing room |
| Tenant | Auto-displayed from room (info card) |
| Room price | Auto-filled from room |
| Electricity — Mode | **Default: Direct input (override)** — toggle to meter reading mode |
| Electricity — From | Auto-filled from previous receipt's `electricity_to` (meter mode only) |
| Electricity — To | Manual input (meter mode only) |
| Electricity — Units | Auto-computed: To − From (meter mode only) |
| Electricity — Price/Unit | Auto-filled from current utility price (in ៛, meter mode only) |
| Electricity — Total | Auto-computed: Units × Price (meter mode) or direct input |
| Water — Mode | Default: meter reading mode — toggle to direct input |
| Water — From | Auto-filled from previous receipt's `water_to` (is not none check — handles 0 readings) |
| Water — To | Manual input |
| Water — Units | Auto-computed: To − From |
| Water — Price/Unit | Auto-filled from current utility price (in ៛) |
| Water — Total | Auto-computed: Units × Price |
| Due Balance | Auto-filled from previous receipt `remaining_balance` (in ៛) |
| Late Fee | Optional manual input (in ៛) |
| Discount | Optional manual input (in ៛) |
| Notes / Remarks | Optional text |
| Total | Auto-computed = room + electricity + water + due balance + late fee − discount |

**Payment fields:**

| Field | Options |
|---|---|
| Payment status | Unpaid / Paid / Partial |
| Paid amount | Manual input (in ៛, shown for partial) |
| Remaining balance | Auto-computed = total − paid |
| Payment method | Cash / Bank Transfer / QR |
| Payment date | Date picker |

**Live summary panel (right column):**
- Updates in real-time as inputs change
- Shows all line items and running total in ៛
- Sticky positioning — stays visible while scrolling

#### 7.3 Partial Payment — Balance Carry-Over

- If tenant pays partially, `remaining_balance` is saved on the receipt
- Next month's receipt auto-loads previous `remaining_balance` as **Due Balance**
- Chain continues until fully settled

#### 7.4 Receipt Number

- Auto-generated format: `RCP-YYYYMM-XXXX` (e.g., `RCP-202605-0001`)

#### 7.5 Receipt Detail Page

- View all line items and amounts
- Payment panel: record partial or full payment directly from detail page
- Link to print receipt

#### 7.6 Thermal Receipt Print (80mm)

- Opens in a new browser tab — browser handles printing
- CSS: `@page { size: 80mm auto; margin: 3mm 4mm; }`
- **Font**: Noto Sans Khmer (Google Fonts, weights 700 + 900)
- **All text bold** — `font-weight: 900` on body, inherits everywhere
- **Font size**: 17px body (50% larger than original 11px for readability on thermal paper)
- **Language**: Khmer-only labels
- Content:
  - Business header: ការគ្រប់គ្រងជួល
  - Receipt number, date, billing month (Khmer month name)
  - Room number + building, tenant name + phone
  - Line items table (in ៛): room rent, electricity (with meter sub-note), water (m³ sub-note), adjustments
  - Totals: grand total in ៛ + USD conversion `(≈ $xx.xx)`, paid amount, balance due
  - Payment status (in Khmer), payment method, payment date
  - Notes (if any)
  - Footer: អរគុណ!
- Print / Close buttons visible on screen, hidden when printing

---

### 8. Reports

- **Monthly Revenue Report**: expected vs collected vs outstanding per month (in ៛), collection rate progress bar
- **Overdue Report**: all rooms with unpaid/partial balance, total outstanding amount
- **Occupancy Report**: occupied vs vacant rooms by building

---

## Data Model

```
users
  id, username, password_hash, full_name, created_at

buildings
  id, name, address, created_at

rooms
  id, building_id, room_number, floor, room_type (single/double/studio),
  price (Float, ៛), deposit_amount (Float, ៛), status (available/occupied/maintenance), created_at

tenants (current active tenant per room)
  id, room_id, name, gender, nid, tel,
  emergency_contact_name, emergency_contact_tel,
  num_roommates, contract_duration (monthly/6months/1year),
  move_in_date, deposit_paid (Float, ៛), is_active, created_at

tenant_history (log of all past tenants per room)
  id, room_id, name, gender, nid, tel, num_roommates,
  move_in_date, move_out_date, move_out_reason,
  deposit_paid (Float, ៛), deposit_refunded (Float, ៛), created_at

utility_prices
  id, utility_type (water/electricity), price_per_unit (Float, ៛),
  effective_date, created_at

receipts
  id, receipt_number, room_id, tenant_id,
  billing_month, billing_year,
  room_price (Float, ៛),
  electricity_from, electricity_to, electricity_units,
  electricity_price_per_unit (Float, ៛), electricity_total (Float, ៛),
  water_from, water_to, water_units,
  water_price_per_unit (Float, ៛), water_total (Float, ៛),
  previous_balance (Float, ៛), late_fee (Float, ៛), discount (Float, ៛),
  total_amount (Float, ៛), paid_amount (Float, ៛), remaining_balance (Float, ៛),
  payment_status (unpaid/paid/partial), payment_method (cash/bank_transfer/qr),
  payment_date, notes, created_at
```

---

## UI Requirements

- Mobile responsive (Bootstrap 5)
- Bilingual labels: Khmer + English throughout (except thermal receipt print = Khmer only)
- Sidebar navigation (collapsible on mobile)
- Overdue receipts highlighted in red
- Status badges: paid (green), partial (yellow), unpaid (red)
- Currency displayed in ៛ throughout the app

---

## Out of Scope (v1)

- Multi-user roles (single admin only)
- SMS / email notifications
- Online payment integration
- Multi-language toggle (both shown simultaneously is sufficient)

---

## Decisions Log

| # | Item | Decision |
|---|---|---|
| 1 | Currency | ៛ (Khmer Riel) as system currency. USD shown as secondary on thermal receipt only (1 USD = 4,000 ៛). |
| 2 | Receipt printing | Browser-based HTML print — ReportLab/WeasyPrint cannot shape Khmer complex script. |
| 3 | Deposit tracking | Recorded at move-in; refund amount noted at move-out. Not a running balance. |
| 4 | Partial payment | Remaining balance carries over automatically to next month as Due Balance. |
| 5 | Electricity default mode | Direct input (override) is the default — most landlords enter the total directly. |
| 6 | Previous receipt lookup | Finds most recent receipt before billing month — not limited to exactly the previous calendar month, handles skipped months. |
| 7 | Water meter — zero value | Template uses `is not none` check (not falsy check) so a reading of 0 is correctly pre-filled. |
| 8 | Utility price tiebreaker | Same-day prices: most recently inserted row wins (`order_by effective_date DESC, id DESC`). |
| 9 | Password hashing | `pbkdf2:sha256` — `scrypt` is unavailable on Python 3.9 / macOS. |
| 10 | Database | SQLite — single admin, no concurrent writes. Migrate to PostgreSQL if scale grows. |
| 11 | Port | 8080 — port 5000 conflicts with macOS AirPlay Receiver. |
| 12 | Auth | Single admin login for v1. |
| 13 | Billing month/year on room change | Preserved in URL query params when room dropdown changes. |
| 14 | Previous receipt modal | Full previous receipt shown in popup modal on generate screen — doesn't interrupt the form. |
