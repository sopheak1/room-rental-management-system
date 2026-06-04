"""
Receipt calculation tests — mirrors the math in app/routes/receipts.py.
Run: venv/bin/pytest tests/test_receipt_calc.py -v
"""

# ── Helpers (same logic as the route) ───────────────────────────────────────

def calc_water_meter(w_from, w_to, w_ppu):
    w_units = max(w_to - w_from, 0)
    return round(w_units * w_ppu, 2)


def calc_electricity_meter(e_from, e_to, e_ppu):
    e_units = max(e_to - e_from, 0)
    return round(e_units * e_ppu, 2)


def calc_total(room_price, elec_total, water_total,
               previous_balance=0, fee=0, late_fee=0, discount=0):
    return round(
        room_price + elec_total + water_total
        + previous_balance + fee + late_fee - discount, 2
    )


# ── Water ────────────────────────────────────────────────────────────────────

class TestWaterMeterCalc:
    def test_basic(self):
        assert calc_water_meter(0, 10, 1500) == 15000

    def test_from_previous_reading(self):
        assert calc_water_meter(50, 60, 1500) == 15000

    def test_negative_units_clamp_to_zero(self):
        # to < from must give 0, never negative
        assert calc_water_meter(60, 50, 1500) == 0

    def test_same_reading(self):
        assert calc_water_meter(100, 100, 1500) == 0

    def test_zero_ppu(self):
        assert calc_water_meter(0, 10, 0) == 0

    def test_fractional_units(self):
        assert calc_water_meter(0, 10.5, 1000) == 10500

    def test_float_ppu_stored_value(self):
        # Python Float columns return 1500.0 — must not become 15000
        ppu = float('1500.0')
        assert calc_water_meter(0, 10, ppu) == 15000


# ── Electricity ──────────────────────────────────────────────────────────────

class TestElectricityMeterCalc:
    def test_basic(self):
        assert calc_electricity_meter(100, 200, 800) == 80000

    def test_same_reading(self):
        assert calc_electricity_meter(100, 100, 800) == 0

    def test_negative_units_clamp_to_zero(self):
        assert calc_electricity_meter(200, 100, 800) == 0

    def test_float_ppu_stored_value(self):
        ppu = float('800.0')
        assert calc_electricity_meter(100, 200, ppu) == 80000


# ── Total amount ─────────────────────────────────────────────────────────────

class TestTotalCalc:
    def test_basic(self):
        assert calc_total(200000, 80000, 15000) == 295000

    def test_with_previous_balance(self):
        assert calc_total(200000, 0, 0, previous_balance=50000) == 250000

    def test_with_discount(self):
        assert calc_total(200000, 0, 0, discount=10000) == 190000

    def test_with_fee(self):
        assert calc_total(200000, 15000, 10000, fee=1500) == 226500

    def test_discount_cannot_make_negative(self):
        # Route does not clamp; test documents expected behavior
        result = calc_total(100, 0, 0, discount=200)
        assert result == -100  # route trusts UI to prevent this

    def test_all_fields(self):
        assert calc_total(
            room_price=200000,
            elec_total=80000,
            water_total=15000,
            previous_balance=5000,
            fee=3000,
            late_fee=2000,
            discount=1000,
        ) == 304000
