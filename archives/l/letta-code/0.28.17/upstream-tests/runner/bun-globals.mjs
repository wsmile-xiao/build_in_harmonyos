// bun-globals.mjs — installs a minimal globalThis.Bun for node, covering the
// Bun.* API surface actually used by the letta-code unit tests.
import { spawn as nodeSpawn, spawnSync as nodeSpawnSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { Readable } from "node:stream";
import { once } from "node:events";
import { globSync } from "node:fs";

let installed = false;

export function installBunGlobals() {
  if (installed || globalThis.Bun) return;
  installed = true;

  function bunFile(p) {
    return {
      name: String(p),
      exists() { return existsSync(p); },
      async text() { return readFile(p, "utf8"); },
      async json() { return JSON.parse(await readFile(p, "utf8")); },
      async arrayBuffer() { return (await readFile(p)).buffer.slice(0); },
      async bytes() { return new Uint8Array(await readFile(p)); },
      async size() { return (await readFile(p)).byteLength; },
    };
  }

  const Bun = {
    version: "1.3.0",
    main: false,
    env: process.env,
    secrets: undefined,
    sleep(ms) { return new Promise((r) => setTimeout(r, ms)); },
    write(p, data) {
      if (typeof p === "string") return writeFile(p, data);
      return writeFile(p.path, data);
    },
    file: bunFile,
    fileURLToPath,
    pathToFileURL,
    homedir: () => os.homedir(),
    cwd: () => process.cwd(),
    nanoseconds: () => Number(process.hrtime.bigint()),
    which(cmd) {
      const dirs = (process.env.PATH || "").split(path.delimiter);
      for (const d of dirs) {
        const p = path.join(d, cmd);
        if (existsSync(p)) return p;
      }
      return null;
    },
    stdin: {
      stream: () => Readable.toWeb(process.stdin),
    },
    stdout: process.stdout,
    stderr: process.stderr,
    spawnSync(cmd, opts = {}) {
      const res = nodeSpawnSync(cmd[0], cmd.slice(1), {
        cwd: opts.cwd,
        env: opts.env,
        stdio: opts.stdio || "pipe",
        encoding: undefined,
        timeout: opts.timeout,
      });
      res.exitCode = res.status;
      res.success = res.status === 0;
      if (res.error) throw res.error;
      return res;
    },
    spawn(cmd, opts = {}) {
      // Support both bun signatures:
      //   Bun.spawn(["node", "x.ts"], {cwd, env, stdout, stderr})
      //   Bun.spawn({ cmd: [...], cwd, env, stdout: "pipe", stderr: "pipe" })
      let cmdArray = Array.isArray(cmd) ? cmd : null;
      if (cmdArray === null && cmd && Array.isArray(cmd.cmd)) {
        cmdArray = cmd.cmd;
        opts = cmd;
      }
      if (cmdArray === null) {
        throw new TypeError("Bun.spawn: expected a command array or {cmd: [...]}");
      }
      const stdio = opts.stdio || [
        opts.stdin || "ignore",
        opts.stdout || "pipe",
        opts.stderr || "inherit",
      ];
      const child = nodeSpawn(cmdArray[0], cmdArray.slice(1), { cwd: opts.cwd, env: opts.env, stdio });
      const exited = new Promise((resolve, reject) => {
        child.once("exit", (code, signal) => resolve(code ?? -1));
        child.once("error", reject);
      });
      child.exited = exited;
      child.exitCode = null;
      child.exited.then((r) => { child.exitCode = r; });
      // bun exposes child.stdout/stderr as web ReadableStreams (wrapping the
      // pipe), so `new Response(handle.stdout).text()` works like in tests.
      if (opts.stdout === "pipe" || opts.stdout === undefined) {
        child.stdout = child.stdout ? Readable.toWeb(child.stdout) : null;
      }
      if (opts.stderr === "pipe") {
        child.stderr = child.stderr ? Readable.toWeb(child.stderr) : null;
      }
      return child;
    },
    async serve(opts = {}) {
      const server = http.createServer(async (req, res) => {
        try {
          const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
          const headers = new Headers();
          for (const [k, v] of Object.entries(req.headers)) {
            if (v !== undefined) headers.set(k, Array.isArray(v) ? v.join(", ") : String(v));
          }
          let body = null;
          if (req.method !== "GET" && req.method !== "HEAD") {
            body = Readable.toWeb(req);
          }
          const request = new Request(url, { method: req.method, headers, body, duplex: "half" });
          const resp = await opts.fetch(request, server);
          const respHeaders = resp.headers instanceof Headers ? resp.headers : new Headers(resp.headers || {});
          res.writeHead(resp.status || 200, Object.fromEntries(respHeaders.entries()));
          if (resp.body) {
            for await (const chunk of resp.body) res.write(chunk);
          }
          res.end();
        } catch (e) {
          res.writeHead(500, { "content-type": "text/plain" });
          res.end(String((e && e.stack) || e));
        }
      });
      await new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(opts.port ?? 0, opts.hostname || "127.0.0.1", resolve);
      });
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : opts.port;
      const url = `http://${opts.hostname || "127.0.0.1"}:${port}`;
      return {
        url,
        port,
        hostname: opts.hostname || "127.0.0.1",
        stop: () => new Promise((resolve) => server.close(() => resolve())),
        server,
        requestIP: () => null,
      };
    },
    glob(pattern) {
      const out = globSync(String(pattern));
      return out[Symbol.iterator] ? out : [].values();
    },
    $() {
      throw new Error("Bun.$ shell template is not implemented by the bun→node shim");
    },
    deepEquals(a, b) {
      // reuse deep equality from bun-expect (imported lazily to avoid cycles)
      return requireDeepEqual()(a, b);
    },
    unsafe: { gc: () => {}, kill: () => {} },
  };

  Object.defineProperty(globalThis, "Bun", { value: Bun, configurable: true, writable: true });
}

let _deepEqualFn = null;
function requireDeepEqual() {
  if (!_deepEqualFn) {
    // lazy import to avoid a hard cycle at module init
    _deepEqualFn = null;
    try {
      // dynamic import of the sibling module
      void 0;
    } catch { /* ignore */ }
  }
  if (!_deepEqualFn) {
    const { isDeepStrictEqual } = process.getBuiltinModule("util");
    return isDeepStrictEqual;
  }
  return _deepEqualFn;
}
