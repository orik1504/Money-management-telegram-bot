"""Monthly budget with rollover. Pure functions, no DB access."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

ZERO = Decimal(0)


@dataclass
class BudgetStatus:
    budget: Decimal
    carried_over: Decimal
    spent: Decimal
    remaining: Decimal


def next_month(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def budget_for(month: date, budgets: dict[date, Decimal]) -> Decimal:
    """Budget of the most recent row at or before `month` (0 if none)."""
    earlier = [m for m in budgets if m <= month]
    return budgets[max(earlier)] if earlier else ZERO


def compute_status(
    current: date,
    budgets: dict[date, Decimal],
    spent: dict[date, Decimal],
) -> BudgetStatus | None:
    """Walk month by month from the first budget to `current`.

    Each month gets its budget plus whatever was left last month. Overspending
    is not carried as debt - a negative month carries 0.
    Returns None if no budget was set yet.
    """
    if not budgets or min(budgets) > current:
        return None

    month = min(budgets)
    carry = ZERO
    while True:
        month_budget = budget_for(month, budgets)
        month_spent = spent.get(month, ZERO)
        remaining = month_budget + carry - month_spent
        if month == current:
            return BudgetStatus(month_budget, carry, month_spent, remaining)
        carry = max(ZERO, remaining)
        month = next_month(month)
