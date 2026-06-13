# htmx Phase 2 — App-Wide Boost via Global `hx-boost` — Design

**Date:** 2026-06-13
**Status:** Approved, pending implementation plan
**Project:** room-rental-management-system

---

## Context

[Phase 1](2026-06-13-htmx-instant-navigation-design.md) piloted htmx `hx-boost`
on the Dashboard → Generate Receipt → Receipt Detail flow, plus a full-page
dim overlay + spinner for slow boosted-link navigations
([base.html:38-41](../../../app/templates/base.html#L38-L41),
[main.js:60-85](../../../app/static/js/main.js#L60-L85)) and button spinners
via `data-loading-text` for form submits
([main.js:87-111](../../../app/static/js/main.js#L87-L111)).

The pilot's plumbing also fixed a nesting bug: `<body>` carries
`hx-target="#main-content" hx-select="#main-content" hx-swap="outerHTML"`
([base.html:13](../../../app/templates/base.html#L13)), so any boosted element
swaps `#main-content` cleanly with no duplication.

This phase extends the same loading experience (instant swaps + dim overlay +
button spinners) to **every remaining page** — Buildings, Rooms, Tenants,
Receipts list/verify/edit, Utilities, Utility Usage, Reports, Settings.

---

## Approach: Global `hx-boost="true"` on `<body>`

Rather than adding `hx-boost="true"` to ~30 individual `<a>`/`<form>`
elements across 17 templates, add it **once** to the same `<body>` tag that
already carries `hx-target`/`hx-select`/`hx-swap`:

```html
<body class="lang-{{ lang }}" hx-target="#main-content" hx-select="#main-content" hx-swap="outerHTML" hx-boost="true">
```

`hx-boost` is inherited by all descendants, so every same-origin `<a href>`
and `<form>` in the app becomes boosted automatically — true "whole
application" coverage, including any link the page-by-page survey missed.

`target="_blank"` links are skipped automatically by htmx regardless of
inherited `hx-boost` — no action needed for those.

---

## Exclusions (`hx-boost="false"` escape hatches)

Five elements must opt out, each for a distinct reason:

| Element | Location | Reason |
|---|---|---|
| Logout link | [nav_links.html](../../../app/templates/partials/nav_links.html) `nav-link-logout` | Full reload cleanly resets session/UI state |
| Khmer language-switch | [nav_links.html](../../../app/templates/partials/nav_links.html) `sidebar-lang-switch` (🇰🇭) | Carried over from Phase 1: `<body class="lang-{{ lang }}">` is outside the swap region and would go stale |
| English language-switch | [nav_links.html](../../../app/templates/partials/nav_links.html) `sidebar-lang-switch` (🇬🇧) | Same as above |
| `settings.download_db` | [settings/index.html:25](../../../app/templates/settings/index.html#L25) | Route returns a file (`send_file`); boosting would fetch it as AJAX and try to `hx-select` HTML out of binary content, breaking the download |
| `settings.auth_google` | [settings/index.html:162](../../../app/templates/settings/index.html#L162) | Route 302-redirects to Google's OAuth page (cross-origin); a boosted fetch would follow the redirect via AJAX and likely fail/break the OAuth handoff |

---

## Modal-close-before-swap fix (`main.js`)

[rooms/detail.html:183-216](../../../app/templates/rooms/detail.html#L183-L216)
has a Bootstrap modal (`#checkoutModal`) containing a POST form
(`tenants.checkout`). With global boost, submitting it would swap
`#main-content` while the modal's backdrop (appended to `<body>` by Bootstrap
JS) and `modal-open` class remain — a stuck dim backdrop with no modal.

Add a new IIFE to `main.js`:

```js
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

This runs for *any* element inside an open modal — generic enough to cover
`#checkoutModal` and any modal added later, with no per-modal configuration.

---

## `data-loading-text` additions

Following the established pattern
([main.js:87-111](../../../app/static/js/main.js#L87-L111)), add
`data-loading-text="..."` (km/en conditional, matching each page's existing
button label) to the primary submit button of every remaining POST form:

| Page | Form(s) |
|---|---|
| Buildings | delete (list), add/edit (form) |
| Rooms | add/edit (form), checkout (modal on detail) |
| Tenants | add/edit (form), write-off, checkout (checkout.html) |
| Utilities | update |
| Utility Usage | batch save |
| Receipts | edit |
| Settings | upload db, upload client, backup now, test connection, disconnect, save folder |

**GET filter forms** (Rooms search, Receipts list filter, Verify Payment,
Reports/Revenue, Utility Usage setup) are left without `data-loading-text` —
near-instant, conceptually closer to Dashboard's client-side tab filters
(no loading indicator today). The dim overlay also skips forms
([main.js:70](../../../app/static/js/main.js#L70)), so these forms get no
loading indicator at all. Acceptable for now; easy follow-up (add
`data-loading-text`, or stop excluding GET forms from the overlay) if it
feels like a gap once tested.

Existing `onsubmit="return confirm(...)"` handlers (Buildings delete,
Settings restore/disconnect, Tenants write-off/checkout) are unaffected —
Phase 1 already confirmed `confirm()` + `hx-boost` works correctly
(`preventDefault` stops the boosted request when the user cancels).

---

## Files Changed (single commit)

- `app/templates/base.html` — add `hx-boost="true"` to `<body>` (1 line)
- `app/templates/partials/nav_links.html` — `hx-boost="false"` on Logout + 2 language-switch links
- `app/static/js/main.js` — modal-close-before-swap IIFE
- `app/templates/settings/index.html` — `hx-boost="false"` on download_db + auth_google links, plus `data-loading-text` on the 6 remaining forms
- `app/templates/buildings/list.html`, `buildings/form.html`
- `app/templates/rooms/list.html`, `rooms/detail.html`, `rooms/form.html`
- `app/templates/tenants/form.html`, `tenants/checkout.html`
- `app/templates/receipts/list.html`, `receipts/verify.html`, `receipts/edit.html`
- `app/templates/utilities/index.html`
- `app/templates/utility_usage/setup.html`, `utility_usage/batch_input.html`
- `app/templates/reports/*.html` (no boost changes needed — links are covered by global boost; verify only)

---

## Out of Scope

- PWA / native app (carried over from Phase 1, still paused/deferred)
- Adding `data-loading-text` to GET filter forms (noted as a possible follow-up)
- New backend routes/changes — none required, same as Phase 1

---

## Verification

Single manual click-through pass covering every page now reachable via
boosted navigation:

1. **Sidebar**: click every remaining sidebar link (Buildings, Rooms,
   Utilities, Utility Usage, Receipts, Verify Payment, Reports ×3, Settings)
   — confirm instant swap, active-nav highlight updates, no navbar/sidebar
   flicker.
2. **Buildings**: add, edit, delete (with confirm dialog) — confirm button
   spinners, redirects, and flash messages work in-place.
3. **Rooms**: list → detail → edit; add tenant; **checkout modal** — confirm
   the modal closes cleanly before the swap (no stuck backdrop), checkout
   completes and redirects correctly.
4. **Tenants**: add/edit, write-off, checkout flow (checkout.html) — confirm
   spinners + confirm dialogs.
5. **Receipts**: list filter (GET), Verify Payment (GET), Edit receipt (POST)
   — confirm filters update in place, edit saves correctly.
6. **Utilities** / **Utility Usage**: update settings, setup → batch input →
   save — confirm `{% block scripts %}` (already inside `#main-content` since
   Phase 1) re-executes correctly after boosted swaps (meter calculations,
   ESC/POS print bridge `fetch()` calls).
7. **Reports**: index, summary, breakdown (month nav links), overdue,
   revenue (filter form), occupancy — all read-only, confirm instant nav.
8. **Settings**: confirm `download_db` still triggers a real file download
   and `auth_google` still redirects to Google's OAuth page correctly
   (both bypass boosting); confirm upload (multipart) forms still work with
   `hx-boost`; confirm backup/test-connection/disconnect spinners + confirm
   dialogs.
9. **Browser back/forward** across at least 3 different page types — confirm
   instant, correct content at each step.
10. **Mobile viewport** — confirm offcanvas sidebar nav still closes and
    swaps correctly for at least 2 of the newly-boosted pages.

Run the existing test suite (`pytest`) as a sanity check — no Python/route
code is touched in this phase.
