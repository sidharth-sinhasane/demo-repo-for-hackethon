import assert from "node:assert/strict";
import test from "node:test";
import { calculateCheckout } from "../lib/checkout.js";

test("checkout without a coupon keeps the original subtotal", () => {
  const result = calculateCheckout({ subtotal: 125, couponCode: "" });
  assert.equal(result.discount, 0);
  assert.equal(result.total, 135);
  assert.equal(result.couponApplied, false);
});
test("known coupons are applied", () => {
  const result = calculateCheckout({ subtotal: 125, couponCode: "SAVE20" });
  assert.equal(result.discount, 25);
  assert.equal(result.total, 108);
  assert.equal(result.couponApplied, true);
});
