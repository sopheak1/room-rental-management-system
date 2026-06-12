# htmx Instant Navigation — Phase 1 Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up htmx-based instant partial-page navigation and loading feedback (top progress bar + button spinners + active sidebar highlight) for the Dashboard → Generate Receipt → Receipt Detail pilot flow, with zero backend changes.

**Architecture:** App-shell pattern — `base.html`'s navbar/sidebar stay static, only `<main id="main-content">` swaps via `hx-boost`. A single structural change relocates `{% block scripts %}` inside `#main-content` so page-specific scripts re-execute after each swap. `main.js` gains three small, event-driven additions (progress bar, button spinner, active-nav highlight) that stay inert until `hx-boost`/`data-loading-text` are added to specific pilot elements.

**Tech Stack:** htmx 2.0.4 (CDN), existing Flask + Jinja2 + Bootstrap 5.3.2 stack, vanilla JS (`main.js`), no new dependencies.

**Spec:** `docs/superpowers/specs/2026-06-13-htmx-instant-navigation-design.md`

---

## Notes on scope vs. the spec (read before starting)

While researching exact file contents, a few details turned out simpler or different than the spec's wording — documented here so the plan doesn't look like it's deviating by accident:

- **"Script relocation for generate.html, detail.html, print_table.html" → ONE base.html change.** `{% block scripts %}{% endblock %}` is a single block definition in `base.html`; moving *where that block renders* (from outside `<main>` to inside `#main-content`) is a one-time structural edit (Task 1). It automatically applies to every template that defines `{% block scripts %}` — including `generate.html`, `detail.html`, and (as a bonus) `dashboard.html`'s `switchTab`/`applyFilters` script, which the spec didn't call out but which needs this too once Dashboard is reached via a boosted swap.
- **`print_table.html` needs no changes.** It doesn't `{% extends 'base.html' %}` — it's a standalone document loaded only via a hidden `<iframe>` for `html2canvas` snapshots (see `detail.html`'s `downloadReceiptImage`). It's never the target of a clickable link, so `hx-boost` never touches it.
- **Progress bar "done" event:** spec said `htmx:afterSettle`; this plan uses `htmx:afterRequest` instead so the bar always clears even if a request errors (afterSettle only fires after a successful swap). Visually identical for the happy path.
- **Explicitly excluded from this pilot** (left as normal full-page reloads, can be revisited in Phase 2):
  - Navbar brand/logo link to Dashboard (only the sidebar Dashboard link is boosted)
  - Language-switch links in `nav_links.html` (boosting them would leave `<body class="lang-{{ lang }}">` stale, since `<body>` is outside the swap region)
  - "View Previous Receipt" link in `generate.html` (has `target="_blank"`, which htmx's `hx-boost` already skips automatically)
  - Receipt Detail's "Edit" link and the "Delete Payment" modal form — Edit goes to an unaudited page, and the delete form lives inside a Bootstrap modal whose open/backdrop state could get out of sync with a swapped `#main-content`. Both stay as full-page reloads for now.

---

## Task 1: App-shell plumbing in `base.html`

**Files:**
- Modify: `app/templates/base.html`

This task adds the htmx script, marks `<main>` as the swap target, sets body-level `hx-target`/`hx-select` defaults, adds the progress-bar markup, and relocates `{% block scripts %}` inside `#main-content`. Nothing in this task is visible yet — no element has `hx-boost` until Task 3.

- [ ] **Step 1: Add `hx-target`/`hx-select` defaults to `<body>`**

In `app/templates/base.html`, change:

```html
<body class="lang-{{ lang }}">
```

to:

```html
<body class="lang-{{ lang }}" hx-target="#main-content" hx-select="#main-content">
```

These attributes are inherited by any descendant that issues an htmx request (including boosted links/forms), so they only need to be declared once.

- [ ] **Step 2: Add the progress bar markup after the navbar**

Change:

```html
</nav>

<!-- Desktop Sidebar -->
<div class="sidebar d-none d-lg-flex flex-column">
```

to:

```html
</nav>

<!-- htmx navigation progress bar -->
<div id="htmx-progress-bar"><div class="bar"></div></div>

<!-- Desktop Sidebar -->
<div class="sidebar d-none d-lg-flex flex-column">
```

- [ ] **Step 3: Mark `<main>` as the swap target**

Change:

```html
<main class="main-content">
```

to:

```html
<main class="main-content" id="main-content">
```

- [ ] **Step 4: Move `{% block scripts %}` inside `#main-content`**

Change:

```html
    {% block content %}{% endblock %}

  </div>
</main>
```

to:

```html
    {% block content %}{% endblock %}
    {% block scripts %}{% endblock %}

  </div>
</main>
```

- [ ] **Step 5: Remove the old `{% block scripts %}` location and add the htmx script tag**

Change:

```html
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="{{ url_for('static', filename='js/main.js') }}"></script>
{% block scripts %}{% endblock %}
```

to:

```html
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="{{ url_for('static', filename='js/main.js') }}"></script>
```

(`{% block scripts %}` now appears exactly once in the file — at Step 4's location. Defining it twice would raise a Jinja `TemplateAssertionError`.)

- [ ] **Step 6: Verify no regressions (manual, dev server already running)**

With the dev server running, open these three pages directly (normal full page loads — nothing is boosted yet) and confirm each looks and behaves exactly as before, with no browser console errors:
- Dashboard (`/`) — click the Overdue / Upcoming / Paid tabs, confirm `switchTab`/`applyFilters` still work.
- Generate Receipt (`/receipts/generate`) — pick a room, confirm electricity/water totals calculate live.
- An existing receipt's Detail page (`/receipts/<id>`) — confirm sections expand/collapse (`toggleMSection`) and the page renders normally.

This confirms relocating `{% block scripts %}` didn't break any page's existing inline scripts.

- [ ] **Step 7: Commit**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system add app/templates/base.html
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system commit -m "Add htmx app-shell plumbing to base.html"
```

---

## Task 2: Loading-feedback JS/CSS in `main.js` and `style.css`

**Files:**
- Modify: `app/static/css/style.css`
- Modify: `app/static/js/main.js`

Adds the progress-bar CSS, plus three event-driven JS snippets (progress bar, button spinner via `data-loading-text`, active-sidebar-highlight via URL path). All three listen for `htmx:*` events but stay inert until Task 3+ add `hx-boost`/`data-loading-text` to actual elements.

- [ ] **Step 1: Add progress bar CSS**

In `app/static/css/style.css`, change:

```css
@media (min-width: 992px) {
  .main-content { margin-left: var(--app-sidebar-w); }
}
```

to:

```css
@media (min-width: 992px) {
  .main-content { margin-left: var(--app-sidebar-w); }
}

/* ─── htmx navigation progress bar ──────────────────────── */
#htmx-progress-bar {
  position: fixed;
  top: var(--navbar-h, 60px);
  left: 0;
  right: 0;
  height: 3px;
  z-index: 1041;
  pointer-events: none;
}

#htmx-progress-bar .bar {
  height: 100%;
  width: 0;
  opacity: 0;
  background: linear-gradient(90deg, #22d3ee, var(--app-primary));
}

#htmx-progress-bar.htmx-loading .bar {
  width: 70%;
  opacity: 1;
  transition: width 8s cubic-bezier(0.1, 0.6, 0.2, 1), opacity 0.2s ease;
}

#htmx-progress-bar.htmx-done .bar {
  width: 100%;
  opacity: 0;
  transition: width 0.2s ease, opacity 0.4s ease 0.2s;
}
```

- [ ] **Step 2: Add the three JS snippets to `main.js`**

In `app/static/js/main.js`, change the end of the file from:

```javascript
// Auto-dismiss flash alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (el) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    });
  }, 5000);
});
```

to:

```javascript
// Auto-dismiss flash alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (el) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    });
  }, 5000);
});

// ── htmx navigation progress bar ────────────────────────────────
(function () {
  var bar = document.getElementById('htmx-progress-bar');
  if (!bar) return;

  document.body.addEventListener('htmx:beforeRequest', function () {
    bar.classList.remove('htmx-done');
    bar.classList.add('htmx-loading');
  });

  document.body.addEventListener('htmx:afterRequest', function () {
    bar.classList.remove('htmx-loading');
    bar.classList.add('htmx-done');
    setTimeout(function () {
      bar.classList.remove('htmx-done');
    }, 400);
  });
})();

// ── htmx button spinner (data-loading-text) ─────────────────────
(function () {
  function loadingTarget(el) {
    if (!el) return null;
    if (el.matches && el.matches('[data-loading-text]')) return el;
    if (el.querySelector) return el.querySelector('[data-loading-text]');
    return null;
  }

  document.body.addEventListener('htmx:beforeRequest', function (evt) {
    var btn = loadingTarget(evt.target);
    if (!btn) return;
    btn.dataset.originalHtml = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>' + btn.dataset.loadingText;
    btn.disabled = true;
  });

  document.body.addEventListener('htmx:afterRequest', function (evt) {
    var btn = loadingTarget(evt.target);
    if (!btn || btn.dataset.originalHtml === undefined) return;
    btn.innerHTML = btn.dataset.originalHtml;
    btn.disabled = false;
    delete btn.dataset.originalHtml;
  });
})();

// ── htmx active sidebar highlight ────────────────────────────────
(function () {
  var rules = [
    { prefix: '/',                  exact: true,  href: '/' },
    { prefix: '/reports/summary',   exact: true,  href: '/reports/summary' },
    { prefix: '/reports/breakdown', exact: true,  href: '/reports/breakdown' },
    { prefix: '/reports',           exact: false, href: '/reports',
      skip: ['/reports/summary', '/reports/breakdown'] },
    { prefix: '/buildings',       exact: false, href: '/buildings' },
    { prefix: '/rooms',           exact: false, href: '/rooms' },
    { prefix: '/receipts/verify', exact: true,  href: '/receipts/verify' },
    { prefix: '/receipts',        exact: false, href: '/receipts' },
    { prefix: '/utility-usage',   exact: false, href: '/utility-usage' },
    { prefix: '/utilities',       exact: false, href: '/utilities' },
    { prefix: '/settings',        exact: false, href: '/settings' }
  ];

  function updateActiveNav() {
    var path = window.location.pathname;
    var activeHrefs = rules.filter(function (r) {
      if (r.skip && r.skip.indexOf(path) !== -1) return false;
      return r.exact ? path === r.prefix : path.indexOf(r.prefix) === 0;
    }).map(function (r) { return r.href; });

    document.querySelectorAll('.sidebar-nav .nav-link').forEach(function (link) {
      var linkPath = new URL(link.href, window.location.origin).pathname;
      link.classList.toggle('active', activeHrefs.indexOf(linkPath) !== -1);
    });
  }

  document.body.addEventListener('htmx:afterSettle', updateActiveNav);
})();
```

The `rules` table mirrors every `{% if request.endpoint ... %}active{% endif %}` condition currently in `app/templates/partials/nav_links.html`, translated from Flask endpoint names to URL path prefixes (`dashboard.index` → `/`, `buildings.list` → `/buildings`, `rooms.list` → `/rooms`, `utilities.index` → `/utilities`, `utility_usage.setup` → `/utility-usage`, `receipts.list`/`receipts.verify` → `/receipts`/`/receipts/verify`, `reports.index`/`.summary`/`.breakdown` → `/reports`/`/reports/summary`/`/reports/breakdown`, `settings.index` → `/settings`).

- [ ] **Step 3: Verify still inert (manual, dev server already running)**

Open the Dashboard (`/`) and check the browser console — no errors (htmx loaded, all three new listeners attached, but nothing has `hx-boost` yet so they never fire). The progress bar div should be present in the DOM (inspect element) but invisible (0 height/opacity effect — `width:0; opacity:0`).

- [ ] **Step 4: Commit**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system add app/static/css/style.css app/static/js/main.js
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system commit -m "Add progress bar, button-spinner, and active-nav-highlight JS/CSS for htmx"
```

---

## Task 3: Pilot wiring — Dashboard entry points

**Files:**
- Modify: `app/templates/partials/nav_links.html`
- Modify: `app/templates/dashboard.html`

This is the first task where `hx-boost="true"` actually appears, so it's the first task with a visible effect.

- [ ] **Step 1: Boost the sidebar Dashboard link**

In `app/templates/partials/nav_links.html`, change:

```html
  <li class="nav-item">
    <a class="nav-link {% if request.endpoint == 'dashboard.index' %}active{% endif %}"
       href="{{ url_for('dashboard.index') }}">
      <i class="bi bi-speedometer2"></i>
      <span><span class="km">ផ្ទាំងគ្រប់គ្រង</span><span class="en">Dashboard</span></span>
    </a>
  </li>
```

to:

```html
  <li class="nav-item">
    <a class="nav-link {% if request.endpoint == 'dashboard.index' %}active{% endif %}"
       href="{{ url_for('dashboard.index') }}" hx-boost="true">
      <i class="bi bi-speedometer2"></i>
      <span><span class="km">ផ្ទាំងគ្រប់គ្រង</span><span class="en">Dashboard</span></span>
    </a>
  </li>
```

- [ ] **Step 2: Boost the "Generate Receipt" button on the Dashboard**

In `app/templates/dashboard.html`, change:

```html
<a href="{{ url_for('receipts.generate') }}" class="btn-dash-generate">
```

to:

```html
<a href="{{ url_for('receipts.generate') }}" class="btn-dash-generate" hx-boost="true">
```

- [ ] **Step 3: Boost the Overdue and Upcoming room cards**

In `app/templates/dashboard.html`, these two `<a>` tags (one in the Overdue tab, one in the Upcoming tab) are textually identical — use `replace_all` to update both in one edit. Change:

```html
  <a href="{{ url_for('receipts.detail', id=e.receipt.id) if e.receipt else url_for('receipts.generate') + '?room_id=' + e.room.id|string }}"
     class="dash-room-card" data-day="{{ e.start_day }}" data-building="{{ e.room.building_id }}">
```

to:

```html
  <a href="{{ url_for('receipts.detail', id=e.receipt.id) if e.receipt else url_for('receipts.generate') + '?room_id=' + e.room.id|string }}"
     class="dash-room-card" data-day="{{ e.start_day }}" data-building="{{ e.room.building_id }}" hx-boost="true">
```

(Use `replace_all: true` — this exact two-line block appears in both the Overdue tab and the Upcoming tab.)

- [ ] **Step 4: Boost the Paid tab room card**

In `app/templates/dashboard.html`, change:

```html
  <a href="{{ url_for('receipts.detail', id=e.receipt.id) }}" class="dash-room-card" data-building="{{ e.room.building_id }}">
```

to:

```html
  <a href="{{ url_for('receipts.detail', id=e.receipt.id) }}" class="dash-room-card" data-building="{{ e.room.building_id }}" hx-boost="true">
```

- [ ] **Step 5: Verify (manual, dev server already running)**

On the Dashboard:
1. Click **"Generate Receipt"** — confirm the navbar/sidebar do *not* flicker/reload, a thin gradient progress bar briefly sweeps under the navbar, the URL updates to `/receipts/generate`, and the Generate Receipt form appears in the content area.
2. Click browser **Back** — confirm it returns to the Dashboard instantly (no full reload), and the Overdue/Upcoming/Paid tab you had selected still works (click each tab, confirm `switchTab` still filters correctly).
3. Click a room card in any tab — confirm it instantly swaps to either Generate Receipt (`?room_id=...`) or an existing receipt's Detail page, with the progress bar animating.
4. While on Generate Receipt or a Receipt Detail page, click **"Dashboard"** in the sidebar — confirm instant swap back to the Dashboard.
5. Check the sidebar: **"Dashboard"** should be highlighted (`.active`) only while on `/`; after navigating to `/receipts/generate` or `/receipts/<id>`, the highlight should move to **"Receipts"**.

- [ ] **Step 6: Commit**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system add app/templates/partials/nav_links.html app/templates/dashboard.html
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system commit -m "Enable hx-boost on Dashboard sidebar link and dashboard entry points"
```

---

## Task 4: Pilot wiring — Generate Receipt page

**Files:**
- Modify: `app/templates/receipts/generate.html`

- [ ] **Step 1: Boost the receipt-generation form**

Change:

```html
<form method="POST" id="receiptForm" onsubmit="return confirmGenerate()">
```

to:

```html
<form method="POST" id="receiptForm" onsubmit="return confirmGenerate()" hx-boost="true">
```

(htmx respects `event.preventDefault()` from `onsubmit` handlers — if `confirmGenerate()` returns `false`, the boosted request is never sent, same as today.)

- [ ] **Step 2: Add a loading label to the Generate button**

Change:

```html
  <button type="submit" class="btn btn-primary btn-generate">
    <i class="bi bi-receipt me-1"></i>
    <span class="km">បង្កើត</span><span class="en">Generate</span>
  </button>
```

to:

```html
  <button type="submit" class="btn btn-primary btn-generate"
          data-loading-text="{% if lang=='km' %}កំពុងបង្កើត...{% else %}Generating...{% endif %}">
    <i class="bi bi-receipt me-1"></i>
    <span class="km">បង្កើត</span><span class="en">Generate</span>
  </button>
```

- [ ] **Step 3: Boost the "View Receipt" link (existing-receipt banner)**

Change:

```html
    <a href="{{ url_for('receipts.detail', id=existing_receipt.id) }}"
       class="btn btn-sm btn-outline-danger mt-2 py-0">
      <i class="bi bi-receipt me-1"></i>
      <span class="km">មើលវិក័យប័ត្រ</span><span class="en">View Receipt</span>
    </a>
```

to:

```html
    <a href="{{ url_for('receipts.detail', id=existing_receipt.id) }}"
       class="btn btn-sm btn-outline-danger mt-2 py-0" hx-boost="true">
      <i class="bi bi-receipt me-1"></i>
      <span class="km">មើលវិក័យប័ត្រ</span><span class="en">View Receipt</span>
    </a>
```

- [ ] **Step 4: Verify (manual, dev server already running)**

1. From the Dashboard, navigate to Generate Receipt (boosted, from Task 3). Select a room and confirm the room price, electricity/water calculations, and "Recall from Utility Usage" (`fetch`-based) still all work after this boosted navigation — this confirms the relocated `{% block scripts %}` re-executes correctly.
2. Fill in valid values and click **"Generate"** — confirm the button immediately shows a spinner with "Generating..." / "កំពុងបង្កើត..." and becomes disabled, the progress bar animates, and the page swaps instantly to the new Receipt Detail page (`/receipts/<id>`) with a success flash message.
3. If you land on Generate Receipt for a room/month that already has a receipt (existing-receipt banner shown), click **"View Receipt"** — confirm instant swap to that receipt's Detail page.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system add app/templates/receipts/generate.html
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system commit -m "Enable hx-boost and button spinner on Generate Receipt form"
```

---

## Task 5: Pilot wiring — Receipt Detail payment forms

**Files:**
- Modify: `app/templates/receipts/detail.html`

Wires up the three self-looping POST forms on Receipt Detail (Record Payment, Defer, Restore/Undefer) — each redirects back to the same `receipts.detail` page, so this exercises the "same-page boosted POST" pattern (complementing Task 4's "cross-page boosted POST").

- [ ] **Step 1: Boost the "Restore to Active" (undefer) form**

Change:

```html
    <form method="POST" action="{{ url_for('receipts.undefer_receipt', id=receipt.id) }}" class="mt-3">
      <button type="submit" class="btn btn-outline-secondary w-100">
        <i class="bi bi-arrow-counterclockwise me-1"></i>
        <span class="km">ស្ដារជាស្ថានភាពធម្មតា</span><span class="en">Restore to Active</span>
      </button>
    </form>
```

to:

```html
    <form method="POST" action="{{ url_for('receipts.undefer_receipt', id=receipt.id) }}" class="mt-3" hx-boost="true">
      <button type="submit" class="btn btn-outline-secondary w-100"
              data-loading-text="{% if lang=='km' %}កំពុងស្ដារ...{% else %}Restoring...{% endif %}">
        <i class="bi bi-arrow-counterclockwise me-1"></i>
        <span class="km">ស្ដារជាស្ថានភាពធម្មតា</span><span class="en">Restore to Active</span>
      </button>
    </form>
```

- [ ] **Step 2: Boost the "Record Payment" form**

Change:

```html
    <form method="POST" action="{{ url_for('receipts.pay', id=receipt.id) }}">
```

to:

```html
    <form method="POST" action="{{ url_for('receipts.pay', id=receipt.id) }}" hx-boost="true">
```

- [ ] **Step 3: Add a loading label to the "Record Payment" button**

Change:

```html
      <button type="submit" class="btn btn-success w-100 fw-bold py-3 fs-5">
        <i class="bi bi-check-lg me-2"></i>
        <span class="km">កត់ត្រាការទូទាត់</span><span class="en">Record Payment</span>
      </button>
```

to:

```html
      <button type="submit" class="btn btn-success w-100 fw-bold py-3 fs-5"
              data-loading-text="{% if lang=='km' %}កំពុងរក្សាទុក...{% else %}Saving...{% endif %}">
        <i class="bi bi-check-lg me-2"></i>
        <span class="km">កត់ត្រាការទូទាត់</span><span class="en">Record Payment</span>
      </button>
```

- [ ] **Step 4: Boost the "Defer to Next Month" form**

Change:

```html
    <form method="POST" action="{{ url_for('receipts.defer_receipt', id=receipt.id) }}" class="mt-3"
          onsubmit="return confirm('តើអ្នកចង់ពន្យារសមតុល្យនេះទៅខែក្រោយទេ?\nវានឹងត្រូវបានដោះស្រាយដោយស្វ័យប្រវត្តិ ហើយនឹងមិនបង្ហាញក្នុងរបាយការណ៍ហួសកំណត់ឡើយ។')">
      <button type="submit" class="btn btn-outline-secondary w-100">
        <i class="bi bi-calendar-arrow-down me-1"></i>
        <span class="km">ពន្យារខែក្រោយ</span><span class="en">Defer to Next Month</span>
      </button>
    </form>
```

to:

```html
    <form method="POST" action="{{ url_for('receipts.defer_receipt', id=receipt.id) }}" class="mt-3" hx-boost="true"
          onsubmit="return confirm('តើអ្នកចង់ពន្យារសមតុល្យនេះទៅខែក្រោយទេ?\nវានឹងត្រូវបានដោះស្រាយដោយស្វ័យប្រវត្តិ ហើយនឹងមិនបង្ហាញក្នុងរបាយការណ៍ហួសកំណត់ឡើយ។')">
      <button type="submit" class="btn btn-outline-secondary w-100"
              data-loading-text="{% if lang=='km' %}កំពុងពន្យារ...{% else %}Deferring...{% endif %}">
        <i class="bi bi-calendar-arrow-down me-1"></i>
        <span class="km">ពន្យារខែក្រោយ</span><span class="en">Defer to Next Month</span>
      </button>
    </form>
```

- [ ] **Step 5: Verify (manual, dev server already running)**

1. Open an unpaid or partially-paid receipt's Detail page. Fill in the payment form and click **"Record Payment"** — confirm the button shows a spinner with "Saving..." / "កំពុងរក្សាទុក...", the progress bar animates, and the page swaps in-place (still on `/receipts/<id>`) showing the updated payment status, paid amount, and a new payment-log entry, plus the success flash message.
2. On a receipt with a remaining balance, click **"Defer to Next Month"** — confirm the `confirm()` dialog still appears; on confirming, the button shows "Deferring..." / "កំពុងពន្យារ...", and the page updates to show the DEFERRED state.
3. On that now-deferred receipt, click **"Restore to Active"** — confirm "Restoring..." / "កំពុងស្ដារ..." shows, and the page returns to its previous active state.
4. Confirm `toggleMSection` (expand/collapse sections), the print button (`printTableViaBridge`), `downloadReceiptImage`, and the back-button origin-tracking script still work after these in-place swaps — this confirms the relocated `{% block scripts %}` re-executes correctly on same-page boosted POSTs too.

- [ ] **Step 6: Commit**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system add app/templates/receipts/detail.html
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system commit -m "Enable hx-boost and button spinners on Receipt Detail payment forms"
```

---

## Task 6: Full pilot verification, regression check, and push

**Files:** none (verification only)

- [ ] **Step 1: Run the existing test suite**

```bash
cd /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system && pytest
```

Expected: all existing tests pass (no Python/route code was touched in Tasks 1-5, this is a sanity check).

- [ ] **Step 2: Full pilot loop (manual, dev server already running)**

Walk the complete loop from the spec's Verification section:
1. Dashboard → click "Generate Receipt" → fill form → submit → land on Receipt Detail.
2. On Receipt Detail, record a payment (or defer/restore).
3. Click "Dashboard" in the sidebar to return.

At each step, confirm: instant content swap (no navbar/sidebar flicker), progress bar animates and clears, button spinners show/clear correctly, and the active sidebar link updates to match the current page ("Dashboard" on `/`, "Receipts" on `/receipts*`).

- [ ] **Step 3: Browser back/forward**

From Receipt Detail, press Back twice (to Generate Receipt, then Dashboard) and Forward twice — confirm each transition is instant (no full reload) and the content/active-nav-highlight match the URL at each step.

- [ ] **Step 4: Non-piloted page falls back to a normal load**

From Receipt Detail or Generate Receipt, click **"Buildings"** (or any other non-piloted sidebar link) — confirm this is a normal full page reload (brief flash/reload), since that link has no `hx-boost`. This confirms the pilot's scope boundary works as designed.

- [ ] **Step 5: Mobile viewport check**

Using browser devtools responsive mode (or a phone), open the Dashboard, use the mobile menu (offcanvas) to navigate to Generate Receipt — confirm the offcanvas closes and the swap still works, the progress bar doesn't visually collide with the navbar or content, and layout looks correct.

- [ ] **Step 6: Push**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system push
```

---
