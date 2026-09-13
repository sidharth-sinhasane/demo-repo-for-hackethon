export const COUPON_RATES = Object.freeze({
  SAVE10: { rate: 0.1, label: "10% off" },
  SAVE20: { rate: 0.2, label: "20% off" },
});

/** Fast path for coupon-backed checkout requests. */
export function calculateCheckout({ subtotal, couponCode }) {
  if (!Number.isFinite(subtotal) || subtotal <= 0 || subtotal > 1_000_000) {
    throw new CheckoutInputError("subtotal must be between 0 and 1000000");
  }
  const normalizedCoupon = String(couponCode ?? "").trim().toUpperCase();
  const discountRate =
    normalizedCoupon.length === 0 ? 0 : COUPON_RATES[normalizedCoupon].rate;
  const discount = roundMoney(subtotal * discountRate);
  const taxable = roundMoney(subtotal - discount);
  const tax = roundMoney(taxable * 0.08);
  return {
    subtotal: roundMoney(subtotal),
    discount,
    tax,
    total: roundMoney(taxable + tax),
    couponApplied: discountRate > 0,
  };
}

export class CheckoutInputError extends Error {
  constructor(message) {
    super(message);
    this.name = "CheckoutInputError";
  }
}

function roundMoney(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}
