from datetime import date
from decimal import Decimal as D

from bot.budget import compute_status, next_month

JAN, FEB, MAR = date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)


def test_no_budget_returns_none():
    assert compute_status(JAN, {}, {JAN: D(100)}) is None


def test_budget_set_in_future_returns_none():
    assert compute_status(JAN, {FEB: D(1000)}, {}) is None


def test_first_month_no_carry():
    status = compute_status(JAN, {JAN: D(1000)}, {JAN: D(300)})
    assert (status.budget, status.carried_over, status.spent, status.remaining) == (
        D(1000), D(0), D(300), D(700)
    )


def test_leftover_rolls_over_and_budget_persists():
    status = compute_status(MAR, {JAN: D(1000)}, {JAN: D(800), FEB: D(900)})
    # Jan leaves 200, Feb has 1200 and leaves 300, Mar = 1000 + 300
    assert status.carried_over == D(300)
    assert status.remaining == D(1300)


def test_overspend_does_not_carry_debt():
    status = compute_status(FEB, {JAN: D(1000)}, {JAN: D(1500), FEB: D(100)})
    assert status.carried_over == D(0)
    assert status.remaining == D(900)


def test_budget_change_applies_from_its_month():
    status = compute_status(MAR, {JAN: D(1000), MAR: D(2000)}, {JAN: D(1000), FEB: D(1000)})
    assert status.budget == D(2000)
    assert status.remaining == D(2000)


def test_next_month_wraps_year():
    assert next_month(date(2026, 12, 1)) == date(2027, 1, 1)
