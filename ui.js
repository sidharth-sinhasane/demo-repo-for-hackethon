import {
  checkoutFeedback,
  networkFailureFeedback,
} from "/lib/ui-feedback.js";

const dot = document.getElementById("healthDot");
const health = document.getElementById("healthText");
const revision = document.getElementById("revision");
const resultCard = document.getElementById("resultCard");
const resultTitle = document.getElementById("resultTitle");
const resultMessage = document.getElementById("resultMessage");
const resultMeta = document.getElementById("resultMeta");
const resultPill = document.getElementById("resultPill");
const responseDetails = document.getElementById("responseDetails");
const resultJson = document.getElementById("resultJson");
const button = document.getElementById("checkoutButton");
const orderInput = document.getElementById("orderId");
const couponInput = document.getElementById("coupon");

async function checkHealth() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error("health check failed");

    dot.className = "dot ok";
    health.textContent = data.telemetry.exported
      ? "Production healthy - O2 connected"
      : "Production healthy - O2 " + data.telemetry.reason;
    const sha = data.deployment.git_commit_sha;
    revision.textContent =
      "Revision: " +
      (sha === "local-development" ? sha : sha.slice(0, 12));
  } catch {
    dot.className = "dot bad";
    health.textContent = "Production unavailable";
  }
}

button.addEventListener("click", async () => {
  setBusy(true);
  renderFeedback({
    state: "running",
    label: "Running",
    title: "Processing checkout",
    message: "Calling the production checkout service...",
  });

  try {
    const response = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        orderId: orderInput.value,
        subtotal: 125,
        couponCode: couponInput.value,
      }),
    });
    const data = await response.json();

    renderFeedback(checkoutFeedback(response.status, data), data);
    resultMeta.textContent = requestMetadata(data);
    orderInput.setAttribute("aria-invalid", String(response.status === 400));
    couponInput.setAttribute("aria-invalid", String(response.status === 400));
  } catch {
    renderFeedback(networkFailureFeedback());
  } finally {
    setBusy(false);
  }
});

function renderFeedback(feedback, rawResponse) {
  resultCard.dataset.state = feedback.state;
  resultPill.textContent = feedback.label;
  resultPill.className = "pill " + feedback.state;
  resultTitle.textContent = feedback.title;
  resultMessage.textContent = feedback.message;
  resultMeta.textContent = "";

  if (rawResponse) {
    resultJson.textContent = JSON.stringify(rawResponse, null, 2);
    responseDetails.hidden = false;
  } else {
    responseDetails.hidden = true;
    responseDetails.open = false;
  }
}

function requestMetadata(data) {
  const parts = [];
  if (data.requestId) parts.push("Request " + data.requestId.slice(0, 8));
  const sha = data.deployment?.git_commit_sha;
  if (sha) {
    parts.push(
      "revision " +
        (sha === "local-development" ? sha : sha.slice(0, 12)),
    );
  }
  return parts.join(" · ");
}

function setBusy(isBusy) {
  button.disabled = isBusy;
  button.setAttribute("aria-busy", String(isBusy));
  button.textContent = isBusy
    ? "Processing checkout..."
    : "Place order - $125.00";
}

checkHealth();
setInterval(checkHealth, 30000);
