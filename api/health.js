import { deploymentMetadata, emitOpenObserveLog } from "../lib/openobserve.js";

export async function GET() {
  const requestId = crypto.randomUUID();
  const telemetry = await emitOpenObserveLog("service.health", {
    level: "INFO",
    message: "checkout service is healthy",
    request_id: requestId,
    route: "/api/health",
    http_method: "GET",
    http_status_code: 200,
    incident_candidate: false,
  });
  return Response.json(
    {
      ok: true,
      requestId,
      deployment: deploymentMetadata(),
      telemetry,
      checkedAt: new Date().toISOString(),
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
