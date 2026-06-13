# htmx Phase 2 — App-Wide Boost via Global `hx-boost` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Phase 1 htmx-boost + dim-overlay + button-spinner loading experience to every remaining page of room-rental-management-system via a single global `hx-boost="true"` on `<body>`, with targeted `hx-boost="false"` exclusions and `data-loading-text` button spinners, per the approved design doc (`docs/superpowers/specs/2026-06-13-htmx-phase2-global-boost-design.md`).

**Architecture:** One attribute change on `<body>` (base.html) makes every same-origin `<a href>`/`<form>` boosted by default — instant swaps into `#main-content`. Five elements opt out via `hx-boost="false"` (2 language-switch links, Logout, download_db, auth_google). A new `htmx:beforeRequest` listener in main.js closes any open Bootstrap modal before a boosted swap, fixing a stuck-backdrop issue on the Rooms checkout modal. The remainder of the work is additive `data-loading-text="..."` attributes on ~13 form-submit buttons across Buildings, Rooms, Tenants, Receipts, Utilities, Utility Usage, and Settings, following the existing km/en Jinja-conditional pattern already used in `receipts/generate.html` and `receipts/detail.html`.

**Tech Stack:** Flask + Jinja2 templates, htmx 2.0.4 (`hx-boost`, `data-loading-text` via custom JS in `app/static/js/main.js`), Bootstrap 5.3.2 (modals, spinners).

**No new files.** All edits are to existing templates + `main.js`. No automated tests exist for this UI-loading behavior — verification is the design doc's 10-point manual click-through (Task 11), plus a `pytest` sanity run since no Python/route code changes.

---

### Task 1: Global `hx-boost` on `<body>`

**Files:**
- Modify: `app/templates/base.html:13`

- [ ] **Step 1: Add `hx-boost="true"` to the `<body>` tag**

Current (`base.html:13`):
```html
<body class="lang-{{ lang }}" hx-target="#main-content" hx-select="#main-content" hx-swap="outerHTML">
```

New:
```html
<body class="lang-{{ lang }}" hx-target="#main-content" hx-select="#main-content" hx-swap="outerHTML" hx-boost="true">
```

Note: this line already carries `hx-swap="outerHTML"` from the previously-uncommitted Bug #4 fix (dashboard content-shift fix). This edit is purely additive — appending `hx-boost="true"`. Task 11's commit will include both fixes together.

- [ ] **Step 2: Confirm the edit landed**

```bash
grep -n 'hx-boost="true"' app/templates/base.html
```
Expected: `13:<body class="lang-{{ lang }}" hx-target="#main-content" hx-select="#main-content" hx-swap="outerHTML" hx-boost="true">`

---

### Task 2: Exclude Logout + language-switch links from boost

**Files:**
- Modify: `app/templates/partials/nav_links.html:4-11,100`

- [ ] **Step 1: Add `hx-boost="false"` to both language-switch links (lines 4-11)**

Current:
```html
    <a href="{{ url_for('set_lang', code='km') }}"
       class="lang-flag-btn {{ 'active' if lang == 'km' }}" title="ខ្មែរ">
      <span class="flag">🇰🇭</span><span class="flag-label">ខ្មែរ</span>
    </a>
    <a href="{{ url_for('set_lang', code='en') }}"
       class="lang-flag-btn {{ 'active' if lang == 'en' }}" title="English">
      <span class="flag">🇬🇧</span><span class="flag-label">EN</span>
    </a>
```

New:
```html
    <a href="{{ url_for('set_lang', code='km') }}" hx-boost="false"
       class="lang-flag-btn {{ 'active' if lang == 'km' }}" title="ខ្មែរ">
      <span class="flag">🇰🇭</span><span class="flag-label">ខ្មែរ</span>
    </a>
    <a href="{{ url_for('set_lang', code='en') }}" hx-boost="false"
       class="lang-flag-btn {{ 'active' if lang == 'en' }}" title="English">
      <span class="flag">🇬🇧</span><span class="flag-label">EN</span>
    </a>
```

- [ ] **Step 2: Add `hx-boost="false"` to the Logout link (line 100)**

Current:
```html
    <a class="nav-link nav-link-logout" href="{{ url_for('auth.logout') }}">
```

New:
```html
    <a class="nav-link nav-link-logout" href="{{ url_for('auth.logout') }}" hx-boost="false">
```

- [ ] **Step 3: Confirm**

```bash
grep -n 'hx-boost="false"' app/templates/partials/nav_links.html
```
Expected: 3 matches (2 language-switch `<a>` tags + the Logout `<a>` tag).

---

### Task 3: Modal-close-before-swap fix in `main.js`

**Files:**
- Modify: `app/static/js/main.js` (append after line 144)

- [ ] **Step 1: Append the new IIFE after the "active sidebar highlight" block**

Current end of file (lines 143-145):
```js
  document.body.addEventListener('htmx:afterSettle', updateActiveNav);
})();
```

New (append a new IIFE after this block):
```js
  document.body.addEventListener('htmx:afterSettle', updateActiveNav);
})();

// ── Close open Bootstrap modal before a boosted swap ─────────────
(function () {
  document.body.addEventListener('htmx:beforeRequest', function (evt) {
    var modalEl = evt.detail.elt.closest('.modal.show');
    if (!modalEl) return;
    var modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
  });
})();
```

- [ ] **Step 2: Confirm**

```bash
grep -n "Close open Bootstrap modal" app/static/js/main.js
```
Expected: one match near the end of the file.

---

### Task 4: `settings/index.html` — exclusions + 6 `data-loading-text` buttons

**Files:**
- Modify: `app/templates/settings/index.html:25,46-49,88-91,94-97,102-104,124-126,147-149,162`

- [ ] **Step 1: `hx-boost="false"` on the download_db link (line 25)**

Current:
```html
    <a href="{{ url_for('settings.download_db') }}" class="btn btn-outline-primary w-100 fw-bold mb-3">
```
New:
```html
    <a href="{{ url_for('settings.download_db') }}" class="btn btn-outline-primary w-100 fw-bold mb-3" hx-boost="false">
```

- [ ] **Step 2: `data-loading-text` on the Restore button (lines 46-49)**

Current:
```html
        <button class="btn btn-danger fw-bold" style="white-space:nowrap;">
          <i class="bi bi-upload me-1"></i>
          <span class="km">ស្ដារ</span><span class="en">Restore</span>
        </button>
```
New:
```html
        <button class="btn btn-danger fw-bold" style="white-space:nowrap;"
                data-loading-text="{% if lang=='km' %}កំពុងស្ដារ...{% else %}Restoring...{% endif %}">
          <i class="bi bi-upload me-1"></i>
          <span class="km">ស្ដារ</span><span class="en">Restore</span>
        </button>
```

- [ ] **Step 3: `data-loading-text` on the Backup Now button (lines 88-91)**

Current:
```html
        <button class="btn btn-primary w-100 fw-bold">
          <i class="bi bi-cloud-upload me-1"></i>
          <span class="km">បម្រុងទុកឥឡូវ</span><span class="en">Backup Now</span>
        </button>
```
New:
```html
        <button class="btn btn-primary w-100 fw-bold"
                data-loading-text="{% if lang=='km' %}កំពុងបម្រុងទុក...{% else %}Backing up...{% endif %}">
          <i class="bi bi-cloud-upload me-1"></i>
          <span class="km">បម្រុងទុកឥឡូវ</span><span class="en">Backup Now</span>
        </button>
```

- [ ] **Step 4: `data-loading-text` on the Test button (lines 94-97)**

Current:
```html
        <button class="btn btn-outline-info w-100 fw-bold">
          <i class="bi bi-wifi me-1"></i>
          <span class="km">សាកល្បង</span><span class="en">Test</span>
        </button>
```
New:
```html
        <button class="btn btn-outline-info w-100 fw-bold"
                data-loading-text="{% if lang=='km' %}កំពុងសាកល្បង...{% else %}Testing...{% endif %}">
          <i class="bi bi-wifi me-1"></i>
          <span class="km">សាកល្បង</span><span class="en">Test</span>
        </button>
```

- [ ] **Step 5: `data-loading-text` on the Disconnect button (icon-only, lines 102-104)**

Current:
```html
        <button class="btn btn-outline-danger">
          <i class="bi bi-x-circle"></i>
        </button>
```
New:
```html
        <button class="btn btn-outline-danger"
                data-loading-text="{% if lang=='km' %}កំពុងផ្តាច់...{% else %}Disconnecting...{% endif %}">
          <i class="bi bi-x-circle"></i>
        </button>
```

- [ ] **Step 6: `data-loading-text` on the Upload (client JSON) button (lines 124-126)**

Current:
```html
          <button class="btn btn-primary" style="white-space:nowrap;">
            <span class="km">បង្ហោះ</span><span class="en">Upload</span>
          </button>
```
New:
```html
          <button class="btn btn-primary" style="white-space:nowrap;"
                  data-loading-text="{% if lang=='km' %}កំពុងបង្ហោះ...{% else %}Uploading...{% endif %}">
            <span class="km">បង្ហោះ</span><span class="en">Upload</span>
          </button>
```

- [ ] **Step 7: `hx-boost="false"` on the auth_google link (line 162)**

Current:
```html
      <a href="{{ url_for('settings.auth_google') }}" class="btn btn-success w-100 fw-bold py-3">
```
New:
```html
      <a href="{{ url_for('settings.auth_google') }}" class="btn btn-success w-100 fw-bold py-3" hx-boost="false">
```

- [ ] **Step 8: `data-loading-text` on the Save (folder ID) button (lines 147-149)**

Current:
```html
          <button class="btn btn-primary" style="white-space:nowrap;">
            <span class="km">រក្សាទុក</span><span class="en">Save</span>
          </button>
```
New:
```html
          <button class="btn btn-primary" style="white-space:nowrap;"
                  data-loading-text="{% if lang=='km' %}កំពុងរក្សាទុក...{% else %}Saving...{% endif %}">
            <span class="km">រក្សាទុក</span><span class="en">Save</span>
          </button>
```

- [ ] **Step 9: Confirm**

```bash
grep -n 'data-loading-text\|hx-boost="false"' app/templates/settings/index.html
```
Expected: 8 matches (2 `hx-boost="false"` + 6 `data-loading-text`).

---

### Task 5: `buildings/list.html` + `buildings/form.html`

**Files:**
- Modify: `app/templates/buildings/list.html:29`
- Modify: `app/templates/buildings/form.html:30-34`

- [ ] **Step 1: `data-loading-text` on the delete button (icon-only, `list.html:29`)**

Current:
```html
        <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
```
New:
```html
        <button class="btn btn-sm btn-outline-danger"
                data-loading-text="{% if lang=='km' %}កំពុងលុប...{% else %}Deleting...{% endif %}"><i class="bi bi-trash"></i></button>
```

- [ ] **Step 2: `data-loading-text` on the Create/Update button (`form.html:30-34`), conditional on `building` + `lang`**

Current:
```html
  <button type="submit" class="btn btn-primary">
    <i class="bi bi-check-lg me-1"></i>
    <span class="km">{{ 'រក្សាទុក' if building else 'បង្កើត' }}</span>
    <span class="en">{{ 'Update' if building else 'Create' }}</span>
  </button>
```
New:
```html
  <button type="submit" class="btn btn-primary"
          data-loading-text="{% if building %}{% if lang=='km' %}កំពុងរក្សាទុក...{% else %}Updating...{% endif %}{% else %}{% if lang=='km' %}កំពុងបង្កើត...{% else %}Creating...{% endif %}{% endif %}">
    <i class="bi bi-check-lg me-1"></i>
    <span class="km">{{ 'រក្សាទុក' if building else 'បង្កើត' }}</span>
    <span class="en">{{ 'Update' if building else 'Create' }}</span>
  </button>
```

- [ ] **Step 3: Confirm**

```bash
grep -n 'data-loading-text' app/templates/buildings/list.html app/templates/buildings/form.html
```
Expected: 1 match per file.

---

### Task 6: `rooms/detail.html` (checkout modal) + `rooms/form.html`

`rooms/list.html` is a GET filter form — excluded per design, verify-only in Task 11 (no edit).

**Files:**
- Modify: `app/templates/rooms/detail.html:205-208`
- Modify: `app/templates/rooms/form.html:72-77`

- [ ] **Step 1: `data-loading-text` on the checkout-modal Confirm button (`detail.html:205-208`)**

Current:
```html
          <button type="submit" class="btn btn-danger fw-bold">
            <i class="bi bi-box-arrow-right me-1"></i>
            <span class="km">បញ្ជាក់ចេញ</span><span class="en">Confirm Check Out</span>
          </button>
```
New:
```html
          <button type="submit" class="btn btn-danger fw-bold"
                  data-loading-text="{% if lang=='km' %}កំពុងចេញ...{% else %}Checking out...{% endif %}">
            <i class="bi bi-box-arrow-right me-1"></i>
            <span class="km">បញ្ជាក់ចេញ</span><span class="en">Confirm Check Out</span>
          </button>
```

- [ ] **Step 2: `data-loading-text` on the Create/Update Room button (`form.html:72-77`), conditional on `room` + `lang`**

Current:
```html
  <button type="submit" class="btn btn-primary">
    <i class="bi bi-check-lg me-1"></i>
    <span class="km">{{ 'រក្សាទុក' if room else 'បង្កើតបន្ទប់' }}</span>
    <span class="en">{{ 'Update' if room else 'Create Room' }}</span>
  </button>
```
New:
```html
  <button type="submit" class="btn btn-primary"
          data-loading-text="{% if room %}{% if lang=='km' %}កំពុងរក្សាទុក...{% else %}Updating...{% endif %}{% else %}{% if lang=='km' %}កំពុងបង្កើត...{% else %}Creating...{% endif %}{% endif %}">
    <i class="bi bi-check-lg me-1"></i>
    <span class="km">{{ 'រក្សាទុក' if room else 'បង្កើតបន្ទប់' }}</span>
    <span class="en">{{ 'Update' if room else 'Create Room' }}</span>
  </button>
```

- [ ] **Step 3: Confirm**

```bash
grep -n 'data-loading-text' app/templates/rooms/detail.html app/templates/rooms/form.html
```
Expected: 1 match per file.

---

### Task 7: `tenants/form.html` + `tenants/checkout.html`

**Files:**
- Modify: `app/templates/tenants/form.html:108-113`
- Modify: `app/templates/tenants/checkout.html:61-65,163-167`

- [ ] **Step 1: `data-loading-text` on the Add/Update Tenant button (`form.html:108-113`), conditional on `tenant` + `lang`**

Current:
```html
  <button type="submit" class="btn btn-primary">
    <i class="bi bi-check-lg me-1"></i>
    <span class="km">{{ 'រក្សាទុក' if tenant else 'បន្ថែម' }}</span>
    <span class="en">{{ 'Update' if tenant else 'Add Tenant' }}</span>
  </button>
```
New:
```html
  <button type="submit" class="btn btn-primary"
          data-loading-text="{% if tenant %}{% if lang=='km' %}កំពុងរក្សាទុក...{% else %}Updating...{% endif %}{% else %}{% if lang=='km' %}កំពុងបន្ថែម...{% else %}Adding...{% endif %}{% endif %}">
    <i class="bi bi-check-lg me-1"></i>
    <span class="km">{{ 'រក្សាទុក' if tenant else 'បន្ថែម' }}</span>
    <span class="en">{{ 'Update' if tenant else 'Add Tenant' }}</span>
  </button>
```

- [ ] **Step 2: `data-loading-text` on the Write Off All button (`checkout.html:61-65`)**

The visible label includes a dynamic amount (`{{ total_outstanding|khr }}`); the loading text stays simple/static.

Current:
```html
      <button class="btn btn-outline-warning w-100 fw-bold">
        <i class="bi bi-eraser me-1"></i>
        <span class="km">លើកលែងទាំងអស់ ({{ total_outstanding|khr }})</span>
        <span class="en">Write Off All ({{ total_outstanding|khr }})</span>
      </button>
```
New:
```html
      <button class="btn btn-outline-warning w-100 fw-bold"
              data-loading-text="{% if lang=='km' %}កំពុងលើកលែង...{% else %}Writing off...{% endif %}">
        <i class="bi bi-eraser me-1"></i>
        <span class="km">លើកលែងទាំងអស់ ({{ total_outstanding|khr }})</span>
        <span class="en">Write Off All ({{ total_outstanding|khr }})</span>
      </button>
```

- [ ] **Step 3: `data-loading-text` on the final Confirm Check Out button (`checkout.html:163-167`)**

Note: this button uses `onclick="return confirm('{{ confirm_co }}')"` directly on the `<button>`, not `onsubmit` on the `<form>` (different from the Phase 1-established pattern). When the click handler returns `false`, the browser cancels the click's default action (form submission) before any `submit` event fires, so htmx's boosted-submit listener never runs — Cancel should still correctly abort the request. Verified during Task 11's manual click-through (item 4).

Current:
```html
      <button type="submit" class="btn btn-danger w-100 fw-bold py-3"
              onclick="return confirm('{{ confirm_co }}')">
        <i class="bi bi-box-arrow-right me-2"></i>
        <span class="km">បញ្ជាក់ចេញ</span><span class="en">Confirm Check Out</span>
      </button>
```
New:
```html
      <button type="submit" class="btn btn-danger w-100 fw-bold py-3"
              onclick="return confirm('{{ confirm_co }}')"
              data-loading-text="{% if lang=='km' %}កំពុងចេញ...{% else %}Checking out...{% endif %}">
        <i class="bi bi-box-arrow-right me-2"></i>
        <span class="km">បញ្ជាក់ចេញ</span><span class="en">Confirm Check Out</span>
      </button>
```

- [ ] **Step 4: Confirm**

```bash
grep -n 'data-loading-text' app/templates/tenants/form.html app/templates/tenants/checkout.html
```
Expected: 1 match in `form.html`, 2 matches in `checkout.html`.

---

### Task 8: `receipts/edit.html`

`receipts/list.html` (GET filter) and `receipts/verify.html` (GET search) are excluded per design, verify-only in Task 11 (no edits).

**Files:**
- Modify: `app/templates/receipts/edit.html:184-187`

- [ ] **Step 1: `data-loading-text` on the Save button**

Current:
```html
  <button type="submit" class="btn btn-warning btn-generate fw-bold">
    <i class="bi bi-pencil-square me-1"></i>
    <span class="km">រក្សាទុក</span><span class="en">Save</span>
  </button>
```
New:
```html
  <button type="submit" class="btn btn-warning btn-generate fw-bold"
          data-loading-text="{% if lang=='km' %}កំពុងរក្សាទុក...{% else %}Saving...{% endif %}">
    <i class="bi bi-pencil-square me-1"></i>
    <span class="km">រក្សាទុក</span><span class="en">Save</span>
  </button>
```

- [ ] **Step 2: Confirm**

```bash
grep -n 'data-loading-text' app/templates/receipts/edit.html
```
Expected: 1 match.

---

### Task 9: `utilities/index.html`

**Files:**
- Modify: `app/templates/utilities/index.html:77-80`

- [ ] **Step 1: `data-loading-text` on the Update Price button**

Current:
```html
      <button type="submit" class="btn btn-primary w-100 mt-3 py-3 fw-bold">
        <i class="bi bi-check-lg me-1"></i>
        <span class="km">ធ្វើបច្ចុប្បន្នភាព</span><span class="en">Update Price</span>
      </button>
```
New:
```html
      <button type="submit" class="btn btn-primary w-100 mt-3 py-3 fw-bold"
              data-loading-text="{% if lang=='km' %}កំពុងធ្វើបច្ចុប្បន្នភាព...{% else %}Updating...{% endif %}">
        <i class="bi bi-check-lg me-1"></i>
        <span class="km">ធ្វើបច្ចុប្បន្នភាព</span><span class="en">Update Price</span>
      </button>
```

- [ ] **Step 2: Confirm**

```bash
grep -n 'data-loading-text' app/templates/utilities/index.html
```
Expected: 1 match.

---

### Task 10: `utility_usage/batch_input.html` (`setup.html` — verify/note only)

**Files:**
- Modify: `app/templates/utility_usage/batch_input.html:119-122`

- [ ] **Step 1: `data-loading-text` on the Save All button**

Current:
```html
    <button type="submit" class="btn btn-success w-100 fw-bold py-3 fs-5">
      <i class="bi bi-check-circle me-2"></i>
      <span class="km">រក្សាទុកទាំងអស់</span><span class="en">Save All</span>
    </button>
```
New:
```html
    <button type="submit" class="btn btn-success w-100 fw-bold py-3 fs-5"
            data-loading-text="{% if lang=='km' %}កំពុងរក្សាទុក...{% else %}Saving...{% endif %}">
      <i class="bi bi-check-circle me-2"></i>
      <span class="km">រក្សាទុកទាំងអស់</span><span class="en">Save All</span>
    </button>
```

- [ ] **Step 2: Note for Task 11 — no edit needed in `utility_usage/setup.html`**

`setup.html`'s `#setupForm` submit handler calls `e.preventDefault()` then sets `window.location.href = ...` — a hard navigation that bypasses htmx/`hx-boost` entirely regardless of the new global boost. This is pre-existing behavior, not a regression. Task 11's manual click-through should confirm Setup → Batch Input still navigates correctly (full page reload, not a boosted swap).

- [ ] **Step 3: Confirm**

```bash
grep -n 'data-loading-text' app/templates/utility_usage/batch_input.html
```
Expected: 1 match.

---

### Task 11: Verification & Commit

**Files:** none (verification + single commit covering Tasks 1-10 plus the previously-uncommitted Bug #4 fix on `base.html:13`)

- [ ] **Step 1: Run the existing test suite as a sanity check**

```bash
cd /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system && python -m pytest -q
```
Expected: all tests pass (no Python/route code is touched in this phase).

- [ ] **Step 2: Manual click-through (design doc's 10-point checklist)**

Start the dev server and verify each item from `docs/superpowers/specs/2026-06-13-htmx-phase2-global-boost-design.md`:

1. **Sidebar** — click every remaining sidebar link (Buildings, Rooms, Utilities, Utility Usage, Receipts, Verify Payment, Reports ×3, Settings) — instant swap, active-nav highlight updates, no navbar/sidebar flicker.
2. **Buildings** — add, edit, delete (with confirm dialog) — button spinners, redirects, and flash messages work in-place.
3. **Rooms** — list → detail → edit; add tenant; **checkout modal** — the modal closes cleanly before the swap (no stuck backdrop), checkout completes and redirects correctly.
4. **Tenants** — add/edit, write-off, checkout flow (`checkout.html`) — spinners + confirm dialogs, including the `onclick="return confirm(...)"` Confirm Check Out button (Cancel must NOT trigger a boosted submit).
5. **Receipts** — list filter (GET), Verify Payment (GET), Edit receipt (POST) — filters update in place, edit saves correctly with spinner.
6. **Utilities** / **Utility Usage** — update settings, setup → batch input → save — `{% block scripts %}` (already inside `#main-content` since Phase 1) re-executes correctly after boosted swaps (meter calculations, ESC/POS print bridge `fetch()` calls). Confirm Setup's submit still hard-navigates to Batch Input (pre-existing `window.location.href` behavior, not a regression).
7. **Reports** — index, summary, breakdown (month `<select onchange="window.location.href=...">` + year nav `<a href>` links), overdue, revenue (filter form), occupancy — all read-only; `<a href>` links get instant boosted nav, the month `<select>` still does a hard navigation (pre-existing, not a regression).
8. **Settings** — `download_db` still triggers a real file download and `auth_google` still redirects to Google's OAuth page correctly (both bypass boosting); upload (multipart) forms still work with `hx-boost`; backup/test-connection/disconnect spinners + confirm dialogs work.
9. **Browser back/forward** across at least 3 different page types — instant, correct content at each step.
10. **Mobile viewport** — offcanvas sidebar nav still closes and swaps correctly for at least 2 of the newly-boosted pages.

- [ ] **Step 3: Stage and commit**

This single commit covers Tasks 1-10 plus the previously-uncommitted Bug #4 `hx-swap="outerHTML"` fix on `base.html:13` (same line edited in Task 1). **Ask Sopheak for explicit confirmation before running `git commit`, per the project's 2nd-confirmation rule.**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system add \
  app/templates/base.html \
  app/templates/partials/nav_links.html \
  app/static/js/main.js \
  app/templates/settings/index.html \
  app/templates/buildings/list.html app/templates/buildings/form.html \
  app/templates/rooms/detail.html app/templates/rooms/form.html \
  app/templates/tenants/form.html app/templates/tenants/checkout.html \
  app/templates/receipts/edit.html \
  app/templates/utilities/index.html \
  app/templates/utility_usage/batch_input.html

git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system commit -m "$(cat <<'EOF'
Apply global htmx boost + loading indicators app-wide

- Add hx-boost="true" to <body> (base.html), with hx-boost="false"
  on Logout, language-switch links, download_db, and auth_google
- Add modal-close-before-swap fix to main.js for the checkout modal
- Add data-loading-text button spinners across Buildings, Rooms,
  Tenants, Receipts, Utilities, Utility Usage, and Settings forms
- Includes the previously pending hx-swap="outerHTML" fix on
  base.html:13 (dashboard content-shift bug)
EOF
)"
```

- [ ] **Step 4: Confirm clean working tree**

```bash
git -C /Users/sopheak.l/ClaudeHome/Personal/room-rental-management-system status
```
Expected: `nothing to commit, working tree clean`.
