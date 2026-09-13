import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { POST as checkout } from "./api/checkout.js";
import { GET as health } from "./api/health.js";

const port = Number(process.env.PORT || 3000);
createServer(async (incoming, outgoing) => {
  try {
    const url = new URL(incoming.url || "/", `http://127.0.0.1:${port}`);
    if (url.pathname === "/api/health" && incoming.method === "GET") {
      return sendResponse(outgoing, await health());
    }
    if (url.pathname === "/api/checkout" && incoming.method === "POST") {
      const body = await readBody(incoming);
      const request = new Request(url, {
        method: "POST",
        headers: incoming.headers,
        body,
      });
      return sendResponse(outgoing, await checkout(request));
    }
    const staticFiles = {
      "/": ["./index.html", "text/html; charset=utf-8"],
      "/index.html": ["./index.html", "text/html; charset=utf-8"],
      "/ui.js": ["./ui.js", "text/javascript; charset=utf-8"],
      "/lib/ui-feedback.js": [
        "./lib/ui-feedback.js",
        "text/javascript; charset=utf-8",
      ],
    };
    if (staticFiles[url.pathname]) {
      const [file, contentType] = staticFiles[url.pathname];
      const content = await readFile(new URL(file, import.meta.url));
      outgoing.writeHead(200, { "Content-Type": contentType });
      outgoing.end(content);
      return;
    }
    outgoing.writeHead(404, { "Content-Type": "application/json" });
    outgoing.end(JSON.stringify({ error: "not_found" }));
  } catch (error) {
    console.error(error instanceof Error ? error.message : "server error");
    outgoing.writeHead(500, { "Content-Type": "application/json" });
    outgoing.end(JSON.stringify({ error: "internal_server_error" }));
  }
}).listen(port, "127.0.0.1", () => {
  console.log(`CartCrash is running at http://127.0.0.1:${port}`);
});

function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => resolve(Buffer.concat(chunks)));
    request.on("error", reject);
  });
}
async function sendResponse(outgoing, response) {
  outgoing.statusCode = response.status;
  response.headers.forEach((value, key) => outgoing.setHeader(key, value));
  outgoing.end(Buffer.from(await response.arrayBuffer()));
}
