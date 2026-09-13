"""Checkout behavior with stable and intentionally regressed release paths."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


# The demonstration PR changes this value to "regression". Keeping the switch in
# this file makes the GitHub changed-file evidence overlap the exception stack.
DEFAULT_RELEASE = "stable"

COUPON_RATES: dict[str, Decimal] = {
    "SAVE10": Decimal("0.10"),
    "SAVE20": Decimal("0.20"),
}


@dataclass(frozen=True)
class CheckoutResult:
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal

    def as_dict(self) -> dict[str, str]:
        return {
            "subtotal": _money(self.subtotal),
            "discount": _money(self.discount),
            "tax": _money(self.tax),
            "total": _money(self.total),
        }


def calculate_checkout(
    *, subtotal: Decimal, coupon_code: str, release: str
) -> CheckoutResult:
    """Calculate checkout totals.

    The regression deliberately models a plausible refactor: removing a fallback
    from a dictionary lookup because callers were assumed to validate coupons.
    The demo request violates that assumption and produces a stable TypeError.
    """

    if subtotal <= 0:
        raise ValueError("subtotal must be greater than zero")

    normalized_coupon = coupon_code.strip().upper()

    if release == "regression":
        # Intentional demo defect: an unknown coupon returns None. The next line
        # then raises TypeError when Decimal is multiplied by None.
        discount_rate = COUPON_RATES.get(normalized_coupon)
    else:
        discount_rate = COUPON_RATES.get(normalized_coupon, Decimal("0"))

    discount = (subtotal * discount_rate).quantize(  # type: ignore[operator]
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    discounted_subtotal = subtotal - discount
    tax = (discounted_subtotal * Decimal("0.08")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = discounted_subtotal + tax

    return CheckoutResult(
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
    )


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"
