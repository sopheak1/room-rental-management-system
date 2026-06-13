// Global mobile section toggle
function toggleMSection(header) {
  header.classList.toggle('collapsed');
  header.nextElementSibling.classList.toggle('collapsed');
}

// Sync --navbar-h CSS variable to actual navbar height
(function () {
  function syncNavbarHeight() {
    var nav = document.querySelector('.navbar');
    if (nav) {
      document.documentElement.style.setProperty('--navbar-h', nav.offsetHeight + 'px');
    }
  }
  syncNavbarHeight();
  window.addEventListener('resize', syncNavbarHeight);
  // Also sync after fonts/icons finish loading (can change height slightly)
  document.addEventListener('DOMContentLoaded', syncNavbarHeight);
})();

// ── Global money input formatter ──────────────────────────────
// Add class="money-input" to any input that should format as #,###
function formatMoneyInputs() {
  // Format existing values — use parseFloat first so "1500.0" → 1500, not 15000
  document.querySelectorAll('input.money-input').forEach(function (el) {
    const num = parseInt(parseFloat(el.value) || 0);
    if (num) {
      el.value = num.toLocaleString('en-US');
    }
  });
}
// Re-run after every boosted swap too — DOMContentLoaded only fires once,
// but htmx:afterSettle fires after each #main-content swap and would
// otherwise leave freshly-rendered values (e.g. Paid Amount) unformatted.
document.addEventListener('DOMContentLoaded', formatMoneyInputs);
document.body.addEventListener('htmx:afterSettle', formatMoneyInputs);

// Format as user types
document.addEventListener('input', function (e) {
  if (!e.target.classList.contains('money-input')) return;
  const raw = e.target.value.replace(/[^0-9]/g, '');
  e.target.value = raw ? parseInt(raw).toLocaleString('en-US') : '';
});

// Strip commas before any form submits.
// Capture phase is required: htmx's hx-boost submit handler also listens on
// document (bubble phase) and was firing first, serializing the form with
// commas still in the value before this listener could strip them.
document.addEventListener('submit', function (e) {
  e.target.querySelectorAll('input.money-input').forEach(function (el) {
    el.value = el.value.replace(/,/g, '');
  });
}, true);

// Auto-dismiss flash alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (el) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    });
  }, 5000);
});

// ── htmx full-page loading overlay (link navigation only) ────────
// Form submits keep their own button spinner (data-loading-text) and
// don't get this overlay, unless the form opts in with
// data-full-overlay="true" (used on high-traffic mobile screens).
(function () {
  var overlay = document.getElementById('htmx-page-loading');
  if (!overlay) return;

  var showTimeout = null;

  function skipOverlay(elt) {
    return elt.tagName === 'FORM' && !elt.hasAttribute('data-full-overlay');
  }

  document.body.addEventListener('htmx:beforeRequest', function (evt) {
    if (skipOverlay(evt.detail.elt)) return;
    showTimeout = setTimeout(function () {
      overlay.classList.add('htmx-page-loading-visible');
      showTimeout = null;
    }, 150);
  });

  document.body.addEventListener('htmx:afterRequest', function (evt) {
    if (skipOverlay(evt.detail.elt)) return;
    if (showTimeout) {
      clearTimeout(showTimeout);
      showTimeout = null;
    }
    overlay.classList.remove('htmx-page-loading-visible');
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

// ── Close open Bootstrap modal before a boosted swap ─────────────
(function () {
  document.body.addEventListener('htmx:beforeRequest', function (evt) {
    var modalEl = evt.detail.elt.closest('.modal.show');
    if (!modalEl) return;
    var modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
  });
})();
