// Global mobile section toggle
function toggleMSection(header) {
  header.classList.toggle('collapsed');
  header.nextElementSibling.classList.toggle('collapsed');
}

// ── Global money input formatter ──────────────────────────────
// Add class="money-input" to any input that should format as #,###
document.addEventListener('DOMContentLoaded', function () {
  // Format existing values on load
  document.querySelectorAll('input.money-input').forEach(function (el) {
    const raw = el.value.replace(/[^0-9]/g, '');
    if (raw && raw !== '0') {
      el.value = parseInt(raw).toLocaleString('en-US');
    }
  });

  // Format as user types
  document.addEventListener('input', function (e) {
    if (!e.target.classList.contains('money-input')) return;
    const raw = e.target.value.replace(/[^0-9]/g, '');
    e.target.value = raw ? parseInt(raw).toLocaleString('en-US') : '';
  });

  // Strip commas before any form submits
  document.addEventListener('submit', function (e) {
    e.target.querySelectorAll('input.money-input').forEach(function (el) {
      el.value = el.value.replace(/,/g, '');
    });
  });
});

// Auto-dismiss flash alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (el) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    });
  }, 5000);
});
