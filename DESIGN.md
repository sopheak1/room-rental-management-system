# Design Layout & Component Reference

**App:** Room Rental Management System  
**Stack:** Python / Flask · Bootstrap 5 · Noto Sans Khmer  
**Last updated:** 2026-06-06

---

## 1. Global Layout

### Shell Structure

```
┌─────────────────────────────────────────────┐
│  TOP NAVBAR (fixed, full width, z-index 1040)│
├──────────────┬──────────────────────────────┤
│  SIDEBAR     │  MAIN CONTENT                │
│  (desktop    │  padding-top = navbar height  │
│   only,      │  padding: 12px–16px           │
│   230px,     │                               │
│   fixed)     │  container-fluid              │
│              │                               │
└──────────────┴──────────────────────────────┘
```

- **Navbar height** is dynamic — set via JS `ResizeObserver` into `--navbar-h` CSS variable
- On mobile (`< 992px`): sidebar is hidden, replaced by Bootstrap **offcanvas** drawer
- On desktop (`≥ 992px`): fixed left sidebar at 230px width; main content has `margin-left: 230px`
- Background color: `#f1f5f9` (light slate)
- Font: `Noto Sans Khmer` (supports Khmer + Latin)
- Language: bilingual Khmer/English, toggled via `lang` session variable
  - `body.lang-km` → hides `.en` elements
  - `body.lang-en` → hides `.km` elements

---

## 2. Top Navbar

**Color:** `bg-primary` (Bootstrap blue, `#1d4ed8`)  
**Position:** `fixed-top`, full width  
**Height:** dynamic (measured by JS, stored in `--navbar-h`)

| Left side | Right side |
|-----------|------------|
| Hamburger (mobile only) | Language toggle (ខ្មែរ / EN) |
| App logo icon + name | Username (desktop only) |
| | Logout button |

---

## 3. Sidebar (Desktop)

**Width:** 230px  
**Color:** `#1e293b` (dark slate)  
**Position:** fixed left, below navbar

### Nav Link Style
- Default: `color: #94a3b8`, `border-left: 3px solid transparent`
- Hover: `color: #f1f5f9`, `background: rgba(255,255,255,0.07)`, `border-left: #475569`
- Active: `color: #fff`, `background: rgba(59,130,246,0.18)`, `border-left: #3b82f6`

### Menu Items
| # | Icon | Label |
|---|------|-------|
| 1 | `bi-speedometer2` | Dashboard |
| 2 | `bi-buildings` | Buildings |
| 3 | `bi-door-closed` | Rooms |
| 4 | `bi-lightning-charge` | Utilities |
| 5 | `bi-receipt` | Receipts |
| 6 | `bi-calendar-month` | Summary |
| 7 | `bi-bar-chart-steps` | Breakdown |
| 8 | `bi-bar-chart-line` | Reports |
| 9 | `bi-gear` | Settings |

---

## 4. Reusable UI Components

### 4.1 Section Card — `.m-section`

Collapsible white card used throughout all pages.

```
┌────────────────────────────────────┐  ← border-radius: 14px, shadow
│ HEADER  [Icon] Label      [chevron]│  ← clickable, toggles body
├────────────────────────────────────┤
│ BODY                               │  ← padding: 14px 16px
│ (collapsible: adds .collapsed)     │
└────────────────────────────────────┘
```

- **Collapsed state:** chevron rotates -90°, body `display: none`
- **Shadow:** `0 1px 4px rgba(0,0,0,0.07)`
- **Margin-bottom:** 12px

---

### 4.2 List Card — `.m-card`

Used for room list, receipt list, building list items.

```
┌─────────────────────────────────────────────┐
│ [colored left border]                        │
│  BODY (flex:1)           RIGHT     [arrow >] │
│  .m-card-title           amount              │
│  .m-card-sub             badge               │
│  .m-card-meta                                │
└─────────────────────────────────────────────┘
```

- `border-left: 4px solid` — color indicates status
- Entire card is a `<a>` link (tappable)
- `border-radius: 12px`, `padding: 14px 16px`, `margin-bottom: 10px`

**Left border colors by status:**

| Status | Color |
|--------|-------|
| paid / available | `#16a34a` (green) |
| unpaid | `#f8d7da` (light red) |
| partial | `#d97706` (amber) |
| deferred | `#e2e8f0` (gray) |
| occupied | `#3b82f6` (blue) |
| maintenance | `#d97706` (amber) |

---

### 4.3 Detail Row — `.m-detail-row`

Used in all detail pages to show label + value pairs.

```
Label (grey, left)           Value (bold, right)
─────────────────────────────────────────────────
```

- `padding: 10px 0`, `border-bottom: 1px solid #f1f5f9`
- Last row has no border
- Label: `color: #64748b`
- Value: `font-weight: 600`, `text-align: right`

---

### 4.4 Form Input — `.m-input`

Standard input field used across all forms.

- `padding: 12px 14px`
- `border: 2px solid #e2e8f0`
- `border-radius: 10px`
- `background: #f8fafc`
- Focus: `border-color: #3b82f6`, `background: #fff`

**Money input group — `.m-input-group`**

```
┌──────────────────────────┐
│ ៛  │  1,500              │
└──────────────────────────┘
```

- Prefix `៛` in grey, input takes remaining width
- Same border/radius as `.m-input`, focus state on the group container

**Label — `.m-label`**
- `font-size: 0.78rem`, `font-weight: 600`, `color: #64748b`
- Uppercase, `letter-spacing: 0.3px`

---

### 4.5 Filter Bar — `.m-filter-bar`

Horizontally scrollable chip strip used on list pages.

```
[ All ] [ Occupied ] [ Available ] [ Maintenance ] [ Building A ] →
```

- Chip: `padding: 7px 14px`, `border-radius: 20px`, `background: #f1f5f9`
- Active chip: `background: #1d4ed8`, `color: #fff`
- Overflow: horizontal scroll, no scrollbar visible

---

### 4.6 Tab Bar — `.home-tabs`

Used on Dashboard and Room Detail pages.

```
┌─────────────────────────────────────────┐
│ [ Overdue 3 ]  [ Upcoming 5 ]  [ Paid ] │
└─────────────────────────────────────────┘
```

- Container: `background: #f1f5f9`, `border-radius: 10px`, `padding: 4px`
- Active tab: `background: #fff`, `color: #1d4ed8`, shadow
- Count badge: small `#e2e8f0` pill, active turns `#dbeafe`

---

### 4.7 Page Header — `.m-page-header`

Used on all inner pages (add, edit, detail).

```
← [back]   Page Title (h5 bold)        [optional action button]
```

- Back link: `color: #64748b`, `font-size: 1.2rem`
- Title: `font-size: 1.2rem`, `font-weight: 700`, `color: #1e293b`

---

### 4.8 Sticky Action Bar — `.m-action-bar`

Used on form pages (Add, Edit).

```
┌─────────────────────────────────────────┐
│  [ Cancel ]        [ Save / Create ]    │  ← sticky bottom
└─────────────────────────────────────────┘
```

- `position: sticky; bottom: 0`
- `background: #fff`, `border-top: 1px solid #e2e8f0`
- Buttons fill equally (`flex: 1`)

---

### 4.9 Amount Big Display — `.m-amount-big`

Used on Room Detail and Receipt Detail for prominent price display.

- `font-size: 2rem`, `font-weight: 800`, `color: #1e293b`
- Shown inside a centered white `.m-section-body`

---

### 4.10 Status Badges

| Status | Background | Text Color |
|--------|-----------|------------|
| available / paid | `#16a34a` | `#fff` |
| occupied | `#2563eb` | `#fff` |
| maintenance / partial | `#d97706` | `#fff` |
| unpaid | `#f8d7da` | `#58151c` |
| deferred | `#e2e8f0` | `#475569` |

Labels are bilingual via `|status_label` Jinja2 filter (reads `lang` from session).

---

### 4.11 Empty State — `.m-empty`

Shown when a list has no items.

```
        🚪
   No rooms found
   [ Add one ]
```

- Centered, `padding: 50px 20px`
- Icon: `font-size: 3rem`, color `#94a3b8`

---

### 4.12 Flash Messages (Alerts)

Shown at the top of main content after any form submission.

- Auto-dismissible Bootstrap alerts
- Icons per type: ✓ success, △ danger, ⚠ warning, ℹ info
- `border-radius: 10px`

---

### 4.13 Sticky Totals Bar (Generate / Edit Receipt)

```
┌─────────────────────────────────────┐
│  Total                              │  ← dark background #1e293b
│  1,500,000 ៛      [ Generate ]     │
└─────────────────────────────────────┘
```

- `position: sticky; bottom: 0`, `z-index: 100`
- Amount updates live via JS as user fills fields
- Turns red if total < already-paid amount (Edit page)

---

## 5. Page-by-Page Layout

---

### 5.1 Login

- Full-screen centered card (`max-width: 400px`)
- Gradient background: `#1d4ed8 → #1e3a5f`
- `border-radius: 16px`, `padding: 5rem`
- Language toggle top-right
- App icon + name heading
- Fields: Username, Password
- Submit button full width

---

### 5.2 Dashboard

**Header block** (gradient `#1d4ed8 → #1e3a5f`, white text):
- Current month/year
- App name
- 3 stat chips: Overdue (yellow) / Upcoming (blue) / Paid (green)

**Generate Receipt** — full-width primary button below header

**3-tab panel:** Overdue / Upcoming / Paid
- Each tab: filter chips by due day + room cards
- Room card shows: Room number, Building, Tenant, Amount, Status badge

---

### 5.3 Buildings List

- Page header + Add button (top right)
- List of `.m-card` items: Building name, address, room count

### 5.4 Building Add / Edit

- Single `.m-section` form
- Fields: Building Name*, Address
- Sticky action bar: Cancel / Save

---

### 5.5 Rooms List

- Page header + Add button
- Filter bar: All / Occupied / Available / Maintenance + per-building filters
- List of `.m-card` items with left border by status
  - Shows: Room number, Building, Floor, Type, Tenant name, Price, Status badge

### 5.6 Room Detail

**Page header:** Room number + status badge + Edit button

**Price card** — centered large amount display:
- Price/month (`.m-amount-big`)
- Deposit amount (small muted)

**Action buttons** (2-column row):
- Add Tenant (if vacant)
- Generate Receipt

**3-tab panel:**

| Tab | Content |
|-----|---------|
| Tenant | Full tenant details — name, gender, tel, NID, roommates, move-in, contract, deposit. Edit + Check Out buttons |
| Receipts | List of receipt cards for this room |
| History | Past tenant records — move-in/out dates, deposit refunded, reason |

### 5.7 Room Add / Edit

- Page header
- Fields: Building*, Room Number*, Floor, Type, Status (edit only), Price*, Deposit
- Sticky action bar: Cancel / Save

---

### 5.8 Tenant Add / Edit

3 collapsible sections:

| Section | Fields |
|---------|--------|
| Personal Info | Full Name*, Gender, Roommates, NID, Phone |
| Emergency Contact *(collapsed)* | Name, Phone |
| Contract & Deposit | Move-in Date, Duration, Deposit Paid |

- Move-in date change shows inline warning about due-day update
- Sticky action bar: Cancel / Add Tenant (or Save)

### 5.9 Tenant Check Out

3-step guided flow:

**Step 1 — Outstanding Balances**
- Lists unpaid receipts with amounts
- Write Off All button (marks as paid with note)

**Step 2 — Final Receipt**
- Shows current month receipt if exists, or link to generate one

**Step 3 — Complete Checkout**
- Fields: Move-out Date*, Deposit Refunded, Move-out Reason
- Inline warning if refund amount differs from deposit paid
- Confirm Check Out button (danger, full width)

---

### 5.10 Utilities

**3 info cards** (2-column grid for elec + water, 1 for fee):
- Current Electricity price/kWh
- Current Water price/m³
- Current Service Fee (used on Direct Input mode)

**Update Price form** (collapsible section):
- Fields: Type (Electricity / Water / Service Fee)*, Price per Unit*, Effective Date*

**Price History** (collapsed by default):
- Electricity and Water history lists with dates and current badge

---

### 5.11 Receipts List

- Page header + Generate button
- Filter bar: Month (select) + Year (number) + Unpaid / Partial / Paid chips
- Overdue alert banner (if any)
- List of receipt `.m-card` items
  - Left border color = payment status
  - Shows: Receipt number, Room, Building, Tenant, Amount (remaining or total), Status badge

### 5.12 Receipt Generate

6 collapsible sections + sticky total bar:

| # | Section | Fields |
|---|---------|--------|
| 1 | Room & Month | Room (select)*, Month (select)*, Year (readonly) |
| 2 | Room Info *(collapsed)* | Tenant, Room Price, Prev. meter readings, Due Balance — read only |
| 3 | Electricity | Toggle: Direct / Meter mode<br>**Direct:** Amount (money input), Service Fee sub-line shown<br>**Meter:** From, To, Units (readonly), Price/Unit (readonly), Subtotal |
| 4 | Water | Same as Electricity (meter mode default) |
| 5 | Due Balance | Amount (auto-filled from previous receipt, collapsed if 0) |
| 6 | Late Fee & Discount *(collapsed)* | Late Fee, Discount, Notes |

- Warning banner at top if receipt already exists for this tenant/month
- Sticky bar: Grand Total (live calc) + Generate button

### 5.13 Receipt Edit

3 collapsible sections + sticky bar:

| Section | Fields |
|---------|--------|
| Electricity | Direct mode: Amount. Meter mode: From, To, Price/kWh, Subtotal |
| Water | Same as above |
| Adjustments | Room Price, Due Balance, Service Fee, Late Fee, Discount, Notes |

- Warning banner if receipt is fully paid
- Sticky bar: New Total + Paid amount + Save button
- Validation: blocks save if new total < already paid amount

### 5.14 Receipt Detail

**Page header:** Receipt number, Billing month, Room, Building + Status badge

**2 action buttons (side by side):**
- Edit (outline grey) — hidden if locked
- Print Receipt (blue, printer icon)

**Total Amount** — centered `.m-amount-big` with remaining balance and paid amount

**4 collapsible sections:**

| Section | Content |
|---------|---------|
| Tenant Info | Tenant, Tel, Room, Building, Created date |
| Line Items | Room Rent, Electricity (with meter detail if applicable), Water (with meter detail), Due Balance, Late Fee, Discount, Notes |
| Payment Info | Record Payment form (Status select, Amount, Method, Date) OR Paid/Deferred status display |
| Payment Log *(collapsed)* | History of all payments with running balance and delete button for latest |

- Lock banner shown if next month's receipt already exists (edit/delete disabled)
- Defer to Next Month button available for unpaid/partial receipts

### 5.15 Print Receipt (58mm Thermal)

Standalone page, no navbar/sidebar, 58mm width.

```
      វិក័យប័ត្រប្រចាំបន្ទប់
      Tel: 010 938 012 / 011 938 012
══════════════════════════════════
លេខ          RCP-2026-001
អ្នកជួល      Sopheak
ទូរស័ព្ទ     012 345 678
បន្ទប់       101 · Building A
──────────────────────────────────
⚡ អគ្គិសនី
   ចាស់:100 → ថ្មី:120 = 20 kWh
   សរុបភ្លើង          28,000 ៛
──────────────────────────────────
💧 ទឹក
   ចាស់:50 → ថ្មី:53 = 3 m³
   សរុបទឹក            6,000 ៛
──────────────────────────────────
🏠 ថ្លៃបន្ទប់
   ថ្លៃបន្ទប់         200,000 ៛
══════════════════════════════════
សរុប                 234,000 ៛
══════════════════════════════════
```

- Font: Noto Sans Khmer, 17px base
- Toolbar (no-print): Print, PT-210 thermal bridge, Close

---

### 5.16 Reports — Summary

- Month/Year filter bar
- Summary table: Room, Tenant, Electricity, Water, Room Price, Total, Status, Remaining
- Footer row: total revenue

### 5.17 Reports — Breakdown

- Month/Year filter bar
- Detailed per-item breakdown table

### 5.18 Reports — Overdue

- List of all rooms with outstanding balances
- Shows: Room, Tenant, Overdue since, Balance amount

---

### 5.19 Settings

**Section 1 — Database Backup & Restore**
- Download Database button (`.db` file)
- Restore: file input + Restore button (with confirm dialog)
- Warning: restore replaces current DB, old saved as `.db.prev`

**Section 2 — Google Drive Backup**
- Status badge: Connected / Not Connected
- **If not connected** — 3-step setup:
  1. Upload OAuth Client JSON file
  2. Enter Google Drive Folder ID (text input)
  3. Connect Google Account button (enabled only after steps 1+2)
- **If connected:**
  - Backup Now button
  - Test Connection button
  - Disconnect button
  - Folder ID display

---

## 6. Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| Primary blue | `#1d4ed8` | Navbar, active nav, primary buttons |
| Dark slate | `#1e293b` | Sidebar, totals bar |
| Mid slate | `#475569` | Secondary text |
| Light slate | `#64748b` | Labels, muted text |
| Border gray | `#e2e8f0` | Input borders, dividers |
| Page bg | `#f1f5f9` | Body background |
| Input bg | `#f8fafc` | Form input background |
| Green | `#16a34a` | Paid, available |
| Amber | `#d97706` | Partial, maintenance |
| Light red | `#f8d7da` / `#58151c` | Unpaid, danger (custom override) |
| Info blue | `#0ea5e9` | Water, info elements |

---

## 7. Typography

| Element | Size | Weight |
|---------|------|--------|
| Body | 0.9rem | 400 |
| `.m-page-title` | 1.2rem | 700 |
| `.m-amount-big` | 2rem | 800 |
| `.m-card-title` | 1rem | 700 |
| `.m-card-sub` | 0.78rem | 400 |
| `.m-label` | 0.78rem | 600 (uppercase) |
| `.m-detail-row` label | 0.9rem | 400 |
| `.m-detail-row` value | 0.9rem | 600 |
| Status badge | Bootstrap default | 500 |

---

## 8. JS Behaviors

| Behavior | Trigger | Detail |
|----------|---------|--------|
| Navbar height sync | Page load + resize | JS measures `.navbar.offsetHeight`, sets `--navbar-h` CSS var |
| Money formatter | DOMContentLoaded | Formats all `.money-input` values to `1,500` format using `parseFloat` |
| Section collapse | Click `.m-section-header` | Toggles `.collapsed` on header + body |
| Tab switch | Click `.home-tab` | Shows matching `.tab-panel`, hides others |
| Day filter | Click `.m-filter-chip` | Shows/hides `.room-card` items by `data-day` attribute |
| Live total calc | Any field input on Generate/Edit | Sums all line items, updates sticky bar amount |
| Meter ↔ Direct toggle | Toggle switch on Generate | Shows/hides meter fields vs direct input field |
| Deposit refund check | Input on checkout | Shows warning if refund ≠ deposit paid |
| Move-in date warning | Date change on tenant edit | Shows old → new due-day change warning |
| Print bridge | Print button | Sends to Android bridge or `localhost:9100` ESC/POS server |
