export class RequestInputError extends Error {
  constructor(message) {
    super(message);
    this.name = "RequestInputError";
  }
}

export function normalizeOrderId(value) {
  const orderId = String(value ?? "").trim();
  if (!/^[A-Za-z0-9_-]{1,80}$/.test(orderId)) {
    throw new RequestInputError("orderId is invalid");
  }
  return orderId;
}

export function normalizeCouponCode(value) {
  const couponCode = String(value ?? "").trim().toUpperCase();
  if (!/^[A-Z0-9_-]{0,40}$/.test(couponCode)) {
    throw new RequestInputError("couponCode is invalid");
  }
  return couponCode;
}
