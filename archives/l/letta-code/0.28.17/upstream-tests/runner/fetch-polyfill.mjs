// fetch-polyfill.mjs — undici-free fetch for --jitless OpenHarmony node
// (WebAssembly is unavailable under --jitless, so undici's llhttp wasm cannot
// load). This polyfill speaks plain node:http/https and exposes just enough of
// the fetch/Response API that letta-src relies on: status/ok/headers,
// text/json/arrayBuffer, a readable .body web stream (SSE iteration), signal
// abort, and custom method/headers/body.
import http from "node:http";
import https from "node:https";
import { Buffer } from "node:buffer";

function toHeadersList(headers) {
  const out = [];
  if (!headers) return out;
  if (headers instanceof Headers) {
    for (const [k, v] of headers) out.push([k, v]);
    return out;
  }
  if (Array.isArray(headers)) return headers.map(([k, v]) => [k, String(v)]);
  if (typeof headers === "object") {
    for (const [k, v] of Object.entries(headers)) out.push([k, String(v)]);
  }
  return out;
}

class PolyResponse {
  constructor(status, headers, bodySource, url) {
    this.status = status;
    this.statusText = status >= 200 && status < 300 ? "OK" : "Error";
    this.ok = status >= 200 && status < 300;
    this.url = url;
    this.headers = new Headers();
    for (const [k, v] of Object.entries(headers)) this.headers.set(k, String(v));
    this._chunks = [];
    this._bodyPromise = null;
    this._bodyStream = null;
    if (bodySource && typeof bodySource.on === "function") {
      // node IncomingMessage: stream chunks into a ReadableStream.
      let controllerRef;
      this._bodyStream = new ReadableStream({
        start(controller) {
          controllerRef = controller;
        },
      });
      const stream = this._bodyStream;
      bodySource.on("data", (c) => {
        this._chunks.push(c);
        if (controllerRef) {
          try {
            controllerRef.enqueue(new Uint8Array(c));
          } catch {
            // stream already closed; ignore
          }
        }
      });
      bodySource.on("end", () => {
        this._bodyPromise = Promise.resolve();
        if (controllerRef) controllerRef.close();
      });
      bodySource.on("error", (err) => {
        this._bodyPromise = Promise.reject(err);
        if (controllerRef) controllerRef.error(err);
      });
      this._bodyPromise = new Promise((resolve) => {
        bodySource.once("end", resolve);
      });
    } else if (bodySource) {
      this._chunks.push(bodySource);
      this._bodyPromise = Promise.resolve();
      let controllerRef;
      this._bodyStream = new ReadableStream({
        start(controller) {
          controllerRef = controller;
        },
      });
      queueMicrotask(() => {
        if (controllerRef) {
          controllerRef.enqueue(new Uint8Array(bodySource));
          controllerRef.close();
        }
      });
    } else {
      this._bodyPromise = Promise.resolve();
    }
  }
  get body() {
    return this._bodyStream;
  }
  async _buffer() {
    await this._bodyPromise;
    return Buffer.concat(this._chunks);
  }
  async text() {
    return (await this._buffer()).toString("utf8");
  }
  async json() {
    return JSON.parse(await this.text());
  }
  async arrayBuffer() {
    const buf = await this._buffer();
    return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  }
  async blob() {
    return new Blob([await this._buffer()]);
  }
}

export function installFetchPolyfill() {
  if (typeof globalThis.fetch === "function" && typeof WebAssembly !== "undefined") {
    return; // real fetch available (non-jitless)
  }
  if (globalThis.__bunnodeFetchInstalled) return;
  globalThis.__bunnodeFetchInstalled = true;

  globalThis.fetch = function polyfillFetch(input, init = {}) {
    const url =
      typeof input === "string" ? new URL(input) : new URL(input.url);
    const method = (init.method || "GET").toUpperCase();
    const headers = toHeadersList(init.headers);
    const body = init.body;
    const signal = init.signal;
    const transport = url.protocol === "https:" ? https : http;

    return new Promise((resolve, reject) => {
      const headersObj = {};
      for (const [k, v] of headers) headersObj[k] = v;
      const req = transport.request(
        url,
        {
          method,
          headers: headersObj,
        },
        (res) => {
          resolve(
            new PolyResponse(
              res.statusCode ?? 0,
              res.headers,
              res,
              url.toString(),
            ),
          );
        },
      );
      req.on("error", (err) => reject(new TypeError(`fetch failed: ${err.message}`, { cause: err })));
      if (signal) {
        if (signal.aborted) {
          req.destroy();
          reject(new DOMException("This operation was aborted", "AbortError"));
          return;
        }
        signal.addEventListener("abort", () => {
          req.destroy();
        });
      }
      if (body != null) req.write(body);
      req.end();
    });
  };
}
