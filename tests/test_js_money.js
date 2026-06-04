/**
 * JS money formatter & calculation tests.
 * Run: node tests/test_js_money.js
 *
 * Catches bugs like:
 *   - "1500.0" → 15000 (float string with trailing zero)
 *   - parseFloat("1,500") = 1  (comma-formatted string)
 */

let passed = 0, failed = 0;

function assert(condition, label) {
  if (condition) {
    console.log(`  ✅  ${label}`);
    passed++;
  } else {
    console.error(`  ❌  FAIL: ${label}`);
    failed++;
  }
}

// ── Replicate main.js formatters ─────────────────────────────────────────────

// OLD (buggy): strips decimal point, so "1500.0" → "15000"
function formatMoneyOld(str) {
  const raw = str.replace(/[^0-9]/g, '');
  return raw ? parseInt(raw, 10) : 0;
}

// FIXED: parseFloat first, then parseInt — "1500.0" → 1500
function formatMoneyFixed(str) {
  return parseInt(parseFloat(str) || 0);
}

// parseKhr from generate.html — strips commas but keeps decimal point
function parseKhr(s) {
  return parseFloat(String(s).replace(/[^0-9.]/g, '')) || 0;
}

// ── Money formatter ───────────────────────────────────────────────────────────

console.log('\n── formatMoney (on-load, pre-filled values) ───────────────');
assert(formatMoneyOld('1500.0')  === 15000, 'OLD BUG  : "1500.0" → 15000 (float string broken)');
assert(formatMoneyFixed('1500.0') === 1500, 'FIXED    : "1500.0" → 1500');
assert(formatMoneyFixed('800.0')  === 800,  'FIXED    : "800.0"  → 800');
assert(formatMoneyFixed('1500')   === 1500, '"1500"   → 1500');
assert(formatMoneyFixed('0')      === 0,    '"0"      → 0');
assert(formatMoneyFixed('')       === 0,    '""       → 0');

// ── parseKhr ──────────────────────────────────────────────────────────────────

console.log('\n── parseKhr (reads comma-formatted display values) ─────────');
assert(parseKhr('1,500')   === 1500,  '"1,500"   → 1500');
assert(parseKhr('15,000')  === 15000, '"15,000"  → 15000');
assert(parseKhr('1500')    === 1500,  '"1500"    → 1500');
assert(parseKhr('1500.0')  === 1500,  '"1500.0"  → 1500');
assert(parseKhr('0')       === 0,     '"0"       → 0');
assert(parseKhr('')        === 0,     '""        → 0');
// Bug case: parseFloat stops at comma
assert(parseFloat('1,500') === 1,     'RAW BUG  : parseFloat("1,500") = 1 — why parseKhr is needed');

// ── Water calculation ─────────────────────────────────────────────────────────

console.log('\n── Water meter calculation ──────────────────────────────────');
function calcWater(from, to, ppu) {
  return Math.max(to - from, 0) * ppu;
}
assert(calcWater(0, 10, 1500)  === 15000, 'From 0, To 10, PPU 1500 → 15,000');
assert(calcWater(50, 60, 1500) === 15000, 'From 50, To 60, PPU 1500 → 15,000');
assert(calcWater(60, 50, 1500) === 0,     'Negative units clamp to 0');
assert(calcWater(0, 10, parseKhr('1,500'))   === 15000, 'PPU "1,500" via parseKhr → 15,000');
assert(calcWater(0, 10, parseKhr('1500.0'))  === 15000, 'PPU "1500.0" via parseKhr → 15,000');

// ── Electricity calculation ────────────────────────────────────────────────────

console.log('\n── Electricity meter calculation ────────────────────────────');
function calcElec(from, to, ppu) {
  return Math.max(to - from, 0) * ppu;
}
assert(calcElec(100, 200, 800) === 80000, 'From 100, To 200, PPU 800 → 80,000');
assert(calcElec(100, 100, 800) === 0,     'Same reading → 0');
assert(calcElec(200, 100, 800) === 0,     'Negative units clamp to 0');
assert(calcElec(100, 200, parseKhr('800.0')) === 80000, 'PPU "800.0" via parseKhr → 80,000');

// ── Summary ───────────────────────────────────────────────────────────────────

console.log(`\n${'─'.repeat(55)}`);
console.log(`Results: ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
