import { calculateCheckout, CheckoutInputError } from "../lib/checkout.js";
import { deploymentMetadata, emitOpenObserveLog } from "../lib/openobserve.js";
import {
  normalizeCouponCode,
  normalizeOrderId,
  RequestInputError,
} from "../lib/validation.js";

export async function POST(request) {
  const requestId = crypto.randomUUID();
  const startedAt = performance.now();
  let body;

  try {
    try {
      body = await request.json();
    } catch {
      throw new RequestInputError("request body must be valid JSON");
    }

    const orderId = normalizeOrderId(body.orderId);
    const subtotal = Number(body.subtotal);
    const couponCode = normalizeCouponCode(body.couponCode);
    const totals = calculateCheckout({ subtotal, couponCode });

    const telemetry = await emitOpenObserveLog("cart.checkout.completed", {
      level: "INFO",
      message: "checkout completed successfully",
      request_id: requestId,
      order_id: orderId,
      route: "/api/checkout",
      http_method: "POST",
      http_status_code: 200,
      duration_ms: duration(startedAt),
      coupon_code: couponCode,
      incident_candidate: false,
    });

    return Response.json({
      ok: true,
      requestId,
      orderId,
      totals,
      deployment: deploymentMetadata(),
      telemetry,
    });
  } catch (error) {
    const isInputError =
      error instanceof CheckoutInputError || error instanceof RequestInputError;
    const status = isInputError ? 400 : 500;

    const telemetry = await emitOpenObserveLog(
      isInputError ? "cart.checkout.rejected" : "cart.checkout.failed",
      {
        level: isInputError ? "WARN" : "ERROR",
        message: isInputError
          ? "checkout request rejected"
          : "checkout failed during coupon calculation",
        request_id: requestId,
        order_id: safeOrderId(body),
        route: "/api/checkout",
        http_method: "POST",
        http_status_code: status,
        duration_ms: duration(startedAt),
        coupon_code: safeCouponCode(body),
        error_type: error instanceof Error ? error.name : "UnknownError",
        error_message: safeMessage(error),
        stack_trace: sanitizeStack(error),
        failure_fingerprint: isInputError
          ? "checkout.request.invalid"
          : "checkout.coupon_lookup.undefined_rate",
        incident_candidate: !isInputError,
      },
    );

    return Response.json(
      {
        ok: false,
        requestId,
        error: isInputError ? safeMessage(error) : "Checkout unavailable",
        deployment: deploymentMetadata(),
        telemetry,
      },
      { status },
    );
  }
}

function safeOrderId(body) {
  const value = String(body?.orderId ?? "unknown");
  return /^[A-Za-z0-9_-]{1,80}$/.test(value) ? value : "invalid";
}
function safeCouponCode(body) {
  const value = String(body?.couponCode ?? "").trim().toUpperCase();
  return /^[A-Z0-9_-]{0,40}$/.test(value) ? value : "invalid";
}
function safeMessage(error) {
  return error instanceof Error ? error.message.slice(0, 300) : "unknown error";
}
function sanitizeStack(error) {
  if (!(error instanceof Error) || !error.stack) return null;
  const workingDirectory = process.cwd().replaceAll("\\", "/");
  return error.stack
    .replaceAll("\\", "/")
    .replaceAll(workingDirectory, "<app>")
    .replaceAll("/var/task", "<app>")
    .split("\n")
    .slice(0, 12)
    .join("\n");
}
function duration(startedAt) {
  return Math.round((performance.now() - startedAt) * 1000) / 1000;
}
