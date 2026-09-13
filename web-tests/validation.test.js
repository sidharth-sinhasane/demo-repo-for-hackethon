import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeCouponCode,
  normalizeOrderId,
  RequestInputError,
} from "../lib/validation.js";

test("normalizes valid checkout identifiers", () => {
  assert.equal(normalizeOrderId("  order-demo_002  "), "order-demo_002");
  assert.equal(normalizeCouponCode("  flash25  "), "FLASH25");
});

test("rejects malformed order identifiers", () => {
  assert.throws(() => normalizeOrderId("order/spoofed"), RequestInputError);
});

test("rejects malformed coupon codes", () => {
  assert.throws(() => normalizeCouponCode("SAVE20<script>"), RequestInputError);
});
