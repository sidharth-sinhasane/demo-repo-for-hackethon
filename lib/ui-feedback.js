export function checkoutFeedback(status, payload = {}) {
  if (status >= 200 && status < 300 && payload.ok) {
    const total = Number(payload.totals?.total);
    return {
      state: "success",
      label: "Success",
      title: "Order placed",
      message: Number.isFinite(total)
        ? "Checkout completed successfully. Total: $" + total.toFixed(2) + "."
        : "Checkout completed successfully.",
    };
  }

  if (status >= 400 && status < 500) {
    return {
      state: "warning",
      label: "Check input",
      title: "Checkout details need attention",
      message: payload.error || "Review the order details and try again.",
    };
  }

  return {
    state: "error",
    label: "Incident",
    title: "Production checkout failed",
    message:
      "The service returned " +
      (status || "an unexpected error") +
      ". An incident event was sent for investigation.",
  };
}

export function networkFailureFeedback() {
  return {
    state: "error",
    label: "Unavailable",
    title: "Cannot reach production",
    message:
      "The checkout service could not be reached. Check the deployment and try again.",
  };
}
