import assert from "node:assert/strict";
import test from "node:test";
import {
  checkoutFeedback,
  networkFailureFeedback,
} from "../lib/ui-feedback.js";

test("shows a clear successful checkout result", () => {
  const feedback = checkoutFeedback(200, {
    ok: true,
    totals: { total: 135 },
  });
  assert.deepEqual(feedback, {
    state: "success",
    label: "Success",
    title: "Order placed",
    message: "Checkout completed successfully. Total: $135.00.",
  });
});

test("separates rejected input from production incidents", () => {
  assert.equal(
    checkoutFeedback(400, { error: "orderId is invalid" }).state,
    "warning",
  );
  assert.equal(checkoutFeedback(500, { ok: false }).state, "error");
  assert.equal(checkoutFeedback(500, { ok: false }).label, "Incident");
});

test("shows an unavailable state for network failures", () => {
  assert.equal(networkFailureFeedback().label, "Unavailable");
});
