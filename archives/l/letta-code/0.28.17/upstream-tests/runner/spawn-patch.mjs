// spawn-patch.mjs — shared child_process patch, installed both in the test
// runner process (child-entry.mjs) and in every node child via loader.mjs.
// 1. PATH normalization: ensure system dirs are on the spawn PATH (toybox sh
//    has no ';' separator and missing printf/etc otherwise break spawns).
// 2. `node ... run <file.ts> ...` rewriting: tests spawn the CLI the way bun
//    does (`bun --loader=... run src/index.ts` / `LETTA_CODE_BIN=node` with
//    args ["run", child.ts]). Plain node has no `run` subcommand, so rewrite
//    those invocations into `node --import=<entry-globals> <file.ts> ...`
//    (dropping bun's --loader= flags) so .ts entrypoints actually start.
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const require_ = createRequire(import.meta.url);
const { existsSync } = require_("node:fs");

const SYSTEM_PATH_DIRS = ["/usr/bin", "/bin", "/system/bin", "/system/usr/bin"];
const ENTRY_GLOBALS_IMPORT = `--import=${pathToFileURL(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "entry-globals.mjs"),
).pathname}`;
const LOADER_IMPORT = `--import=${pathToFileURL(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "loader.mjs"),
).pathname}`;

let installed = false;

export function normalizeSpawnEnvPath(options) {
  if (!options || typeof options !== "object" || !options.env) return options;
  const pathKey = Object.keys(options.env).find(
    (k) => k.toUpperCase() === "PATH",
  );
  if (!pathKey) return options;
  let pathValue = options.env[pathKey];
  if (typeof pathValue !== "string") return options;
  pathValue = pathValue.split(";").join(":");
  const entries = pathValue.split(":").filter(Boolean);
  let changed = false;
  for (const sysDir of SYSTEM_PATH_DIRS) {
    if (!entries.includes(sysDir)) {
      entries.push(sysDir);
      changed = true;
    }
  }
  if (changed) options.env[pathKey] = entries.join(":");
  return options;
}

// Rewrite `node [...--loader=x...] run <file.ts> [...args]` into
// `node --import=entry-globals <file.ts> [...args]`. Returns null when the
// invocation is not a node+run+ts pattern.
export function rewriteNodeRunInvocation(file, args) {
  if (typeof file !== "string" || !Array.isArray(args)) return null;
  const base = path.basename(file).toLowerCase();
  if (!base.startsWith("node")) return null;
  const runIdx = args.indexOf("run");
  if (runIdx < 0) return null;
  const tsFile = args[runIdx + 1];
  if (typeof tsFile !== "string" || !tsFile.endsWith(".ts")) return null;
  const rest = args.filter((a) => a !== "run" && !a.startsWith("--loader="));
  if (rest.includes(ENTRY_GLOBALS_IMPORT)) return rest;
  return [ENTRY_GLOBALS_IMPORT, ...rest];
}

// Rewrite `bun ...` into an equivalent `node ...` invocation, so tests that
// spawn the bun CLI (spawn("bun", ...) / spawnSync) can run under node.
// Returns { file, args } or null when this invocation is not a rewritable bun
// pattern (external `bunx`, package-manager runs, etc. stay as-is).
export function rewriteBunInvocation(file, args) {
  if (typeof file !== "string" || !Array.isArray(args)) return null;
  if (path.basename(file).toLowerCase() !== "bun") return null;
  const filtered = args.filter((a) => !a.startsWith("--loader="));
  // bun --eval <script> [...]
  if (filtered.includes("--eval") || filtered.includes("-e")) {
    // The script imports .ts modules; without the loader preload the subprocess
    // cannot resolve them (bun has TS support natively, plain node does not).
    return { file: process.execPath, args: [LOADER_IMPORT, ...filtered] };
  }
  // bun run <script> [...]
  if (filtered[0] === "run") {
    const script = filtered[1];
    const rest = filtered.slice(2);
    if (typeof script === "string" && script.endsWith(".ts")) {
      return { file: process.execPath, args: [ENTRY_GLOBALS_IMPORT, script, ...rest] };
    }
    if (script === "dev") {
      return { file: process.execPath, args: [path.join(process.cwd(), "scripts/dev.cjs"), ...rest] };
    }
    if (script === "build") {
      // package.json: build = "node scripts/postinstall-patches.js && bun run build.js".
      // Skip the vendor-patch step (sandbox-safe) and run the bundler directly.
      return { file: process.execPath, args: [path.join(process.cwd(), "build.js"), ...rest] };
    }
    return null;
  }
  // bun <file.ts> [...args] (direct entrypoint, e.g. src/index.ts)
  const first = filtered[0];
  if (typeof first === "string" && (first.endsWith(".ts") || first.endsWith(".tsx"))) {
    return { file: process.execPath, args: [ENTRY_GLOBALS_IMPORT, ...filtered] };
  }
  return null;
}

export function installSpawnPatch() {
  if (installed) return;
  installed = true;
  const cp = require_("node:child_process");
  const patch = (fn) =>
    function (...args) {
      // spawn(file, args, options) | spawn(command, options) | spawn(command)
      const last = args[args.length - 1];
      const second = args[1];
      if (last && typeof last === "object" && !Array.isArray(last)) {
        normalizeSpawnEnvPath(last);
      } else if (second && typeof second === "object" && !Array.isArray(second)) {
        normalizeSpawnEnvPath(second);
      }
      // OpenHarmony sandbox has no bash (only /bin/sh / busybox); rewrite
      // spawn("bash", ...) / execFile("bash", ...) so tests that launch bash
      // scripts (hook commands, shell launchers) can still run under sh.
      if (Array.isArray(second) && !existsSync("/bin/bash")) {
        const bfile = args[0];
        if (typeof bfile === "string" && path.basename(bfile) === "bash") {
          // `bash -c <script-file>`: exec'ing the file hits the unresolvable
          // #!/bin/bash shebang (exit 127). Interpret the file directly with
          // sh instead — sh skips the shebang line and runs the body, which
          // covers the sandbox's missing bash for POSIX scripts.
          const ci = second.indexOf("-c");
          const scriptArg = ci !== -1 ? second[ci + 1] : undefined;
          if (
            typeof scriptArg === "string" &&
            !scriptArg.includes(" ") &&
            existsSync(scriptArg) &&
            ci !== -1
          ) {
            args[0] = "/bin/sh";
            args[1] = second.filter((_, i) => i !== ci);
          } else {
            args[0] = "/bin/sh";
          }
        }
      }
      // Rewrite node `run <ts>` style invocations (used to launch the CLI and
      // mock subagent children exactly as bun would). args[0] is the command
      // string for execFile; for spawn it is args[1]. Handle both shapes.
      const fileArg = args[0];
      const argsArg = Array.isArray(second) ? second : null;
      if (argsArg) {
        const rewritten = rewriteNodeRunInvocation(fileArg, argsArg);
        if (rewritten) {
          args[1] = rewritten;
          process.stderr.write(
            `[spawnpatch] rewrite node run -> ${fileArg} ${JSON.stringify(rewritten)}\n`,
          );
        } else {
          const bun = rewriteBunInvocation(fileArg, argsArg);
          if (bun) {
            args[0] = bun.file;
            args[1] = bun.args;
            process.stderr.write(
              `[spawnpatch] rewrite bun -> ${bun.file} ${JSON.stringify(bun.args)}\n`,
            );
            // Debug: surface the subprocess stderr for bun --eval children.
            if (process.env.BUNNODE_DBG_EVAL) {
              const cp2 = require_("node:child_process");
              const probe = cp2.spawn(bun.file, bun.args, {
                cwd: typeof args[2] === "object" && args[2] ? args[2].cwd : process.cwd(),
                env: (typeof args[2] === "object" && args[2] && args[2].env) || process.env,
              });
              probe.on("error", (e) => process.stderr.write("[dbg-eval] spawn error: " + e.message + "\n"));
              probe.stderr.on("data", (d) => process.stderr.write("[dbg-eval] child-stderr: " + d.toString().slice(0, 400)));
              probe.stdout.on("data", (d) => process.stderr.write("[dbg-eval] child-stdout: " + d.toString().slice(0, 200)));
            }
          }
        }
      }
      return fn.apply(this, args);
    };
  for (const name of ["spawn", "spawnSync", "execFile", "execFileSync"]) {
    if (typeof cp[name] === "function") {
      const orig = cp[name];
      cp[name] = patch(orig);
      // Preserve util.promisify's custom conversion (used by grep/glob tools).
      try {
        const { promisify } = require_("node:util");
        const custom = orig[promisify.custom];
        if (custom) {
          cp[name][promisify.custom] = (file, args2, options) =>
            new Promise((resolve, reject) => {
              normalizeSpawnEnvPath(options);
              if (Array.isArray(args2)) {
                const rewritten = rewriteNodeRunInvocation(file, args2);
                if (rewritten) {
                  args2 = rewritten;
                } else {
                  const bun = rewriteBunInvocation(file, args2);
                  if (bun) {
                    file = bun.file;
                    args2 = bun.args;
                  }
                }
              }
              orig(file, args2, options, (err, stdout, stderr) => {
                if (err) reject(err);
                else resolve({ stdout, stderr });
              });
            });
        }
      } catch {
        // non-fatal: promisify.custom unavailable
      }
    }
  }
}
