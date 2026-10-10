// bun-serve.mjs — Bun.serve shim built on node:http, for --jitless OpenHarmony
// node. Tests that start a mock OpenAI-compatible SSE provider via Bun.serve
// (headless-* tests) rely on this. Provides:
//   Bun.serve({ port, idleTimeout, fetch(req) }) -> { port, stop() }
// req: { url, method, headers, json(), text(), body }
import http from "node:http";
import { Buffer } from "node:buffer";

const installed = Symbol.for("bunnode.bun.serve.installed");

// node's listen() is async; tests read server.port synchronously right after
// Bun.serve() returns, so we bind a chosen fixed port (not 0) and hand back
// the same value. Ports are picked from a per-process range that starts at a
// pid-derived offset to avoid clashing with other concurrent child processes.
const PORT_BASE = 20000 + ((process.pid || 0) % 1000) * 40;
let nextPort = PORT_BASE;

function createRequest(req) {
  return {
    url: `http://${req.headers.host || "127.0.0.1"}${req.url}`,
    method: req.method,
    headers: new Headers(req.headers),
    async text() {
      return readBody(req);
    },
    async json() {
      const raw = await readBody(req);
      return JSON.parse(raw);
    },
    body: req,
  };
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function writeResponse(res, response, resChunks) {
  if (response === undefined || response === null) {
    res.writeHead(200, { "content-type": "text/plain" });
    res.end();
    return;
  }
  if (typeof response === "number") {
    res.writeHead(response);
    res.end();
    return;
  }
  if (response instanceof Response) {
    res.writeHead(response.status, response.headers);
    if (resChunks && resChunks.length) {
      res.end(Buffer.concat(resChunks));
    } else {
      res.end();
    }
    return;
  }
  if (response instanceof ReadableStream) {
    const reader = response.getReader();
    const pump = () =>
      reader.read().then(({ done, value }) => {
        if (done) {
          res.end();
          return;
        }
        res.write(Buffer.from(value));
        pump();
      });
    pump();
    return;
  }
  res.writeHead(200, { "content-type": "application/json" });
  res.end(JSON.stringify(response));
}

export function installBunServe() {
  if (globalThis[installed]) return;
  globalThis[installed] = true;
  if (!globalThis.Bun) globalThis.Bun = {};
  globalThis.Bun.serve = function bunServe(options) {
    const handler = options.fetch;
    const port = options.port && options.port !== 0 ? options.port : nextPort++;
    const server = http.createServer((req, res) => {
      Promise.resolve(handler(createRequest(req), server))
        .then((response) => {
          if (response instanceof Response && response.body) {
            // Drain the web stream first so SSE bytes are written in order.
            const reader = response.body.getReader();
            const chunks = [];
            const pump = () =>
              reader.read().then(({ done, value }) => {
                if (done) {
                  writeResponse(res, response, chunks);
                  return;
                }
                chunks.push(Buffer.from(value));
                pump();
              });
            pump();
          } else {
            writeResponse(res, response, []);
          }
        })
        .catch((err) => {
          res.writeHead(500, { "content-type": "text/plain" });
          res.end(String((err && err.message) || err));
        });
    });
    server.on("error", (err) => {
      if (err && err.code === "EADDRINUSE") {
        // port clash: retry once on the next port
        const retry = nextPort++;
        server.close();
        const server2 = http.createServer(server.listeners("request")[0]);
        server2.listen(retry, "127.0.0.1");
        server.port = retry;
        server.url = `http://127.0.0.1:${retry}`;
      } else {
        process.stderr.write(`[bun-serve] error: ${err.message}\n`);
      }
    });
    server.listen(port, "127.0.0.1");
    server.port = port;
    server.hostname = "127.0.0.1";
    server.url = `http://127.0.0.1:${port}`;
    server.stop = (closeActive) =>
      new Promise((resolveStop) => {
        server.close(() => resolveStop());
        if (closeActive) server.closeAllConnections?.();
      });
    return server;
  };
}
