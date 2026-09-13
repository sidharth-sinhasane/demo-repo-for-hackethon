const SERVICE_NAME = "cartcrash-checkout";

export function deploymentMetadata() {
  const revision =
    process.env.VERCEL_GIT_COMMIT_SHA ||
    process.env.DEMO_GIT_COMMIT_SHA ||
    "local-development";
  return {
    service_name: SERVICE_NAME,
    service_version:
      revision === "local-development"
        ? "cartcrash-local"
        : `cartcrash-${revision.slice(0, 7)}`,
    git_commit_sha: revision,
    deployment_environment: process.env.VERCEL_ENV || "local-development",
  };
}

export async function emitOpenObserveLog(eventName, fields = {}) {
  const event = {
    _timestamp: Date.now() * 1000,
    timestamp: new Date().toISOString(),
    level: fields.level || "INFO",
    event_name: eventName,
    ...deploymentMetadata(),
    ...fields,
  };
  console.log(JSON.stringify(event));

  const ingestionUrl = process.env.O2_INGESTION_URL;
  const authorization = process.env.O2_AUTH_HEADER;
  if (!ingestionUrl || !authorization) {
    return { exported: false, reason: "not_configured" };
  }

  try {
    const response = await fetch(ingestionUrl, {
      method: "POST",
      headers: {
        Authorization: authorization,
        "Content-Type": "application/json",
        "User-Agent": "cartcrash-demo/1.0",
      },
      body: JSON.stringify([event]),
      signal: AbortSignal.timeout(5_000),
    });
    return response.ok
      ? { exported: true }
      : { exported: false, reason: `http_${response.status}` };
  } catch (error) {
    return {
      exported: false,
      reason: error instanceof Error ? error.name : "export_failed",
    };
  }
}
