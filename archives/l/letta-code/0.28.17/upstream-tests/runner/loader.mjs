// loader.mjs — entry: register the bun-like loader hooks (string form,
// because this node build's register() does not accept the data-object form).
import { register } from "node:module";
import { pathToFileURL } from "node:url";
if (process.env.BUNNODE_LOADER_MARK) console.error("[loader-marker] LOADER EXECUTING");
register(pathToFileURL(new URL("./bun-test-hooks.mjs", import.meta.url).pathname).href, import.meta.url);
if (process.env.BUNNODE_LOADER_MARK) console.error("[loader-marker] REGISTER DONE");

// Every node child (spawned by tests, or as the CLI/subagent children) should
// carry the spawn patch: PATH normalization + `node run <ts>` rewriting.
if (process.env.BUNNODE_LOADER_MARK) console.error("[loader-marker] BEFORE spawn-patch import");
const { installSpawnPatch } = await import("./spawn-patch.mjs");
if (process.env.BUNNODE_LOADER_MARK) console.error("[loader-marker] AFTER spawn-patch import");
installSpawnPatch();
if (process.env.BUNNODE_LOADER_MARK) console.error("[loader-marker] AFTER installSpawnPatch");

// CJS `require()` of .ts files (tests do `require("./catalog")` like bun
// allows). Register a require.extensions handler so createRequire-based
// requires transpile .ts on the fly via the same typescript instance.
{
  const Module = await import("node:module");
  const mod = Module.default ?? Module;
  if (!mod._extensions[".ts"]) {
    const { readFileSync } = await import("node:fs");
    const { createRequire: cr } = await import("node:module");
    // SRC root: env LETTA_SRC, else cwd (README: run from the letta-src checkout)
    const srcRoot = process.env.LETTA_SRC || process.cwd();
    const req = cr(srcRoot + "/package.json");
    const ts = req("typescript");
    mod._extensions[".ts"] = function (module, filename) {
      const source = readFileSync(filename, "utf8");
      const out = ts.transpileModule(source, {
        fileName: filename,
        compilerOptions: {
          module: ts.ModuleKind.CommonJS,
          target: ts.ScriptTarget.ESNext,
          esModuleInterop: true,
          isolatedModules: true,
          sourceMap: false,
        },
      });
      module._compile(out.outputText, filename);
    };
  }
}

// Spawned child node processes (e.g. the image-resize worker in
// image-resize.ts, and `spawnSync(process.execPath, ...)` in tests) must
// inherit the same flags, or they crash with V8 ENOMEM / fail to load .ts.
// Inject them via NODE_OPTIONS so every node child gets them automatically.
const extra = [
  "--jitless",
  "--no-experimental-strip-types",
  `--import=${new URL("./loader.mjs", import.meta.url).pathname}`,
];
const existing = process.env.NODE_OPTIONS ? process.env.NODE_OPTIONS.split(/\s+/) : [];
const toAdd = extra.filter((e) => !existing.includes(e));
if (toAdd.length) {
  process.env.NODE_OPTIONS = [...existing, ...toAdd].join(" ");
}
