# Instant Navigation & Loading Feedback via htmx — Design

**Date:** 2026-06-13
**Status:** Approved, pending implementation plan
**Project:** room-rental-management-system

---

## Context

Navigating between pages (sidebar links, form submits) currently triggers full
page reloads — every click feels slow with no loading feedback. The original
ask was to fix this with a "feels like a real mobile app" experience.

**Alternatives considered:**
- **Native Android app** (`rental-android-native/IDEA.md`) — even trimmed to a
  3-screen MVP (Dashboard, Generate Receipt, Print Receipt), this requires a
  new Kotlin/Compose project, a brand-new authenticated REST API on this Flask
  app (none exists today), and a ported Bluetooth/ESC-POS printing stack.
  Realistically weeks of work, and only covers 3 of the app's many screens.
  **Paused** — revisit only if a need emerges that htmx genuinely can't meet
  (e.g. built-in Bluetooth printing without the print-bridge companion app).
- **PWA** (installable home-screen icon) — useful follow-on, but **deferred**
  for now per explicit choice.

**Chosen approach:** add [htmx](https://htmx.org) to this Flask + Jinja +
Bootstrap app for AJAX-based partial-page navigation, in an app-shell pattern.

---

## Architecture

**App-shell pattern** — `base.html` already wraps every page with a fixed
navbar + sidebar + `<main class="main-content">{% block content %}{% endblock %}</main>`
([base.html:39-76](../../../app/templates/base.html#L39-L76)). The navbar and
sidebar stay static; only the `<main>` content swaps on navigation.

**Mechanism — htmx `hx-boost`:**
- Add the htmx `<script>` tag (CDN) to `base.html`
- `hx-boost="true"` on the shell wrapper, with the swap targeted at
  `#main-content`
- htmx intercepts clicks on internal `<a href>` links (sidebar nav,
  [nav_links.html](../../../app/templates/partials/nav_links.html)) and form
  submits, fetches the same Flask route via AJAX, extracts `#main-content`
  from the response, swaps it into the current page, and updates the URL via
  the History API (browser back/forward keep working)
- **No backend route changes required** — every route keeps returning its
  normal full page; htmx does the extraction client-side

---

## Loading Feedback Design (Option B — top bar + button spinner)

1. **Top progress bar** — a thin gradient bar fixed under the navbar.
   Animates on `htmx:beforeRequest`, completes and fades out on
   `htmx:afterSettle`. Implemented as one small addition to
   [main.js](../../../app/static/js/main.js) plus a `<div>` in `base.html`.
2. **Button spinner** — submit buttons opt in via a
   `data-loading-text="Saving..."` attribute. On `htmx:beforeRequest`, if the
   triggering element is such a button, disable it and swap its label for a
   spinner + that text. Applied per-button as each page is touched during
   rollout.

---

## Implementation Considerations

- **Active sidebar highlighting** — currently computed server-side via
  `request.endpoint` in
  [nav_links.html](../../../app/templates/partials/nav_links.html). Since the
  sidebar no longer re-renders on navigation, add a small `htmx:afterSettle`
  JS snippet that re-applies `.active` based on the new URL.
- **Page-specific scripts** — `generate.html`, `detail.html`,
  `print_table.html`, and `utility_usage/setup.html` have `fetch()`-based JS
  in `{% block scripts %}`. htmx executes `<script>` tags in
  swapped content by default, but `{% block scripts %}` currently sits
  *outside* `<main>` in `base.html` — it needs to move inside the swapped
  region (`#main-content`) so these scripts re-run after each htmx navigation.
- **Bootstrap components** (offcanvas, modals, tooltips) using the data-API
  generally re-init automatically on new markup; anything JS-initialized in
  page scripts is covered by the point above.
- **CSRF** — not used anywhere in this app
  (verified: no `csrf_token`/`WTF_CSRF` references), so boosted POST forms
  need no extra token handling.
- **Flash messages** — the redirect-after-POST pattern
  (`flash()` + session) continues to work: htmx follows redirects and swaps
  the resulting page's `#main-content`, which includes the flash banner.

---

## Rollout Plan

1. **Core change** (single pass): `base.html` (htmx script tag, `hx-boost`,
   progress bar markup, move `{% block scripts %}` inside `#main-content`) +
   `main.js` (progress bar + button-spinner JS)
2. **Page-by-page verification** — walk through each major page and confirm
   navigation, forms (with redirect + flash), and existing `fetch()`-based
   interactivity still work:
   - Dashboard (tabs: Overdue/Upcoming/Paid)
   - Buildings, Rooms (list, detail tabs, add/edit, check-out)
   - Tenants
   - Receipts (list, Generate, Detail, print table)
   - Utilities, Utility Usage (setup, batch input, escpos print)
   - Reports (summary, breakdown, index)
   - Settings
3. **Escape hatch** — `hx-boost="false"` on any specific link/form found to
   misbehave, fixed individually rather than blocking the rollout

---

## Out of Scope

- PWA / installable home-screen icon
- Native Android app (`rental-android-native`) — paused
- New REST API — not needed for this work

---

## Verification

- Manual click-through of every page above: confirm instant content swap,
  progress bar animates and clears, browser back/forward works
- Form submits: confirm redirect + flash message render correctly, button
  spinner shows during the request and clears on the new page
- Confirm existing `fetch()`-based interactions (meter lookups, receipt
  generation calculations, ESC/POS print) still work after htmx-driven
  navigation
- Mobile viewport check — confirm layout/responsiveness unaffected
