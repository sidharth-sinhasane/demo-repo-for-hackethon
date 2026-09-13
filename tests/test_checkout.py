from decimal import Decimal
from unittest import TestCase

from app.checkout import calculate_checkout


class CheckoutReleaseTests(TestCase):
    def test_stable_release_safely_ignores_unknown_coupon(self) -> None:
        result = calculate_checkout(
            subtotal=Decimal("125.00"),
            coupon_code="FLASH25",
            release="stable",
        )

        self.assertEqual(result.discount, Decimal("0.00"))
        self.assertEqual(result.total, Decimal("135.00"))

    def test_regression_release_fails_for_same_unknown_coupon(self) -> None:
        with self.assertRaises(TypeError):
            calculate_checkout(
                subtotal=Decimal("125.00"),
                coupon_code="FLASH25",
                release="regression",
            )

    def test_known_coupon_still_works_in_regression_release(self) -> None:
        result = calculate_checkout(
            subtotal=Decimal("125.00"),
            coupon_code="SAVE20",
            release="regression",
        )

        self.assertEqual(result.discount, Decimal("25.00"))
        self.assertEqual(result.total, Decimal("108.00"))
