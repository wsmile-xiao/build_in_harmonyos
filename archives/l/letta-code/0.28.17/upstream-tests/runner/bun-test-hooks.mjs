// loader.mjs — node module loader hooks that give the letta-code tests a
// bun-like environment:
//   * "bun:test"   -> bun-test-shim.mjs
//   * "@/..."      -> src/...  (path alias)
//   * extensionless relative imports (bundler resolution) inside src
//   * .ts/.tsx     -> transpiled on the fly with the repo's typescript
//   * .json        -> ESM default-export wrapper
//   * mock.module(..., factory)  -> per-process module mocking by resolved path
import { register, isBuiltin } from "node:module";
import { pathToFileURL, fileURLToPath } from "node:url";
import { existsSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { createRequire } from "node:module";

const BASE = path.dirname(fileURLToPath(import.meta.url));
// SRC root: env LETTA_SRC, else <BASE>/../letta-src (repo checkout convention)
const SRC = process.env.LETTA_SRC || path.resolve(BASE, "../letta-src");
const SHIM_URL = pathToFileURL(path.join(BASE, "bun-test-shim.mjs")).href;
const STUB_URL = pathToFileURL(path.join(BASE, "bun-stub.mjs")).href;

let ts = null;
function getTs() {
  if (!ts) {
    const req = createRequire(path.join(SRC, "package.json"));
    ts = req("typescript");
  }
  return ts;
}

const CANDIDATES = [".ts", ".tsx", ".mts", ".cts", ".js", ".mjs", ".cjs", ".json", ".node", ""];

const __isFileCache = new Map();
function isFile(p) {
  if (__isFileCache.has(p)) return __isFileCache.get(p);
  let r;
  try { r = statSync(p).isFile(); } catch { r = false; }
  __isFileCache.set(p, r);
  return r;
}
function resolveCandidates(base, rel) {
  // base: absolute path of a file (strip ext) OR of a directory
  const p = path.join(base, rel);
  // NodeNext style: "./foo.js" may refer to foo.ts / foo.tsx (TS projects)
  const mjsRel = rel.match(/^(.*)\.(js|mjs|cjs)$/);
  if (mjsRel) {
    for (const ext of [".ts", ".tsx", ".mts", ".cts", ".ts", ".tsx"]) {
      const cand = path.join(base, mjsRel[1] + ext);
      if (isFile(cand)) return cand;
    }
  }
  for (const ext of CANDIDATES) {
    const cand = p + ext;
    if (isFile(cand)) return cand;
  }
  // treat base as dir and try index.*
  for (const ext of CANDIDATES) {
    const cand = path.join(p, "index" + ext);
    if (isFile(cand)) return cand;
  }
  return null;
}

function srcAbs(relNoAt) {
  const target = path.join(SRC, "src", relNoAt);
  // relNoAt may include an extension already or point to a dir
  if (isFile(target)) return target;
  const resolved = resolveCandidates(path.dirname(target), path.basename(target));
  return resolved;
}

function mocks() {
  return globalThis.__bunNodeMocks || (globalThis.__bunNodeMocks = new Map());
}
function mockSpecs() {
  return globalThis.__bunNodeMockSpecs || (globalThis.__bunNodeMockSpecs = new Map());
}

const __resolveCache = new Map();
function absoluteTargetForImport(specifier, parentURL) {
  // Returns the absolute file path this specifier resolves to *within src*,
  // or null if it is not a src-relative target (external package / builtin).
  const __cparent = parentURL && parentURL.startsWith("file://") ? path.dirname(fileURLToPath(parentURL)) : parentURL;
  const __ckey = __cparent + "|" + specifier;
  if (__resolveCache.has(__ckey)) return __resolveCache.get(__ckey);
  const __run = () => {
  if (specifier.startsWith("@/")) {
    const target = srcAbs(specifier.slice(2));
    if (target) return target;
  }
  if (specifier.startsWith("./") || specifier.startsWith("../") || specifier === "." || specifier === "..") {
    if (!parentURL || !parentURL.startsWith("file://")) return null;
    const parent = fileURLToPath(parentURL);
    if (!parent.startsWith(SRC + path.sep) && parent !== SRC) return null;
    const dir = path.dirname(parent);
    // "." / ".." reference the directory itself -> resolve to its index file
    if (specifier === "." || specifier === "..") {
      const dirTarget = specifier === "." ? dir : path.resolve(dir, "..");
      return resolveCandidates(dirTarget, "index");
    }
    const resolved = resolveCandidates(dir, specifier);
    return resolved;
  }
    return null;
  };
  const __res = __run();
  __resolveCache.set(__ckey, __res);
  return __res;
}

import { readMockState } from "./mock-bridge.mjs";
function mockState() {
  return readMockState();
}
function mockUrlFor(abs) {
  const st = mockState();
  const f = st && st[abs];
  if (f) return "file://" + f;
  return null;
}

// ---------- resolve ----------
export async function resolve(specifier, context, nextResolve) {

  if (process.env.BUNNODE_GLOBAL_RESOLVE_DEBUG) {
    const par = context.parentURL ? String(context.parentURL).split("/").slice(-2).join("/") : "?";
    console.error("[gresolve] ", specifier.slice(0, 60), " <- ", par);
  }

  if (specifier === "bun:test") return { url: SHIM_URL, shortCircuit: true };
  if (specifier.startsWith("bun:")) return { url: STUB_URL, shortCircuit: true };
  if (specifier === "sharp") {
    // OpenHarmony has no native libvips; use the pure-JS emulation.
    return { url: pathToFileURL(path.join(BASE, "sharp-stub.mjs")).href, shortCircuit: true };
  }
  if (specifier === "yoga-layout" || specifier === "yoga-layout-prebuilt") {
    // Upstream yoga-layout is wasm-only; --jitless disables WebAssembly, so
    // use the pure-JS flexbox emulation.
    return { url: pathToFileURL(path.join(BASE, "yoga-stub.mjs")).href, shortCircuit: true };
  }
  if (isBuiltin(specifier)) {
    // OpenHarmony's filesystem returns EPERM for link(); use the shim that
    // falls back to an O_EXCL write (same EEXIST semantics) for any consumer
    // importing node:fs/promises inside the test graph. The shim itself must
    // get the real builtin (skip when the parent is the shim file).
    const parentFile = context.parentURL && context.parentURL.startsWith("file://")
      ? fileURLToPath(context.parentURL)
      : "";
    if ((specifier === "node:fs/promises" || specifier === "fs/promises") &&
        path.basename(parentFile) !== "fs-link-shim.mjs") {
      return { url: pathToFileURL(path.join(BASE, "fs-link-shim.mjs")).href, shortCircuit: true };
    }
    if ((specifier === "node:fs" || specifier === "fs") &&
        path.basename(parentFile) !== "fs-sync-link-shim.mjs") {
      return { url: pathToFileURL(path.join(BASE, "fs-sync-link-shim.mjs")).href, shortCircuit: true };
    }
    return nextResolve(specifier, context);
  }

  const abs = absoluteTargetForImport(specifier, context.parentURL);
  if (abs) {
    // The test file itself must see the REAL module: it captures real* exports
    // (test.ts:223-244) BEFORE mock.module, and afterAll restores them. Lazy
    // pre-registration writes state.__testFile so we can skip the mock mapping
    // for imports whose parent is the test file. Other parents (static-chain
    // modules like recovery.ts, dynamic importers like send.ts) still get the
    // mock/lazy-mock.
    const st = mockState();
    const skipForTestFile = !!(
      st && st.__testFile &&
      context.parentURL === pathToFileURL(st.__testFile).href
    );
    const mockUrl = skipForTestFile ? null : mockUrlFor(abs);
    if (process.env.BUNNODE_RESOLVE_DEBUG && abs.includes("cli/helpers/stream")) {
      const par = context.parentURL ? String(context.parentURL).split("/").slice(-3).join("/") : "?";
      console.error("[resolve-debug] spec=", specifier, "parent=", par, "mockUrl=", mockUrl ? mockUrl.split("/").pop() : null, "skipTest=", skipForTestFile);
    }
    if (mockUrl) return { url: mockUrl, shortCircuit: true };
    return { url: pathToFileURL(abs).href, shortCircuit: true };
  }

  return nextResolve(specifier, context);
}

// ---------- load ----------
function realModuleExportNames(fp) {
  // Top-level named exports of the real module being mocked. bun's
  // mock.module leaves factory-omitted keys as `undefined`; node ESM instead
  // throws "does not provide an export named X" at link time. Declaring the
  // real module's export names (bound to the mock value, i.e. undefined when
  // absent) reproduces bun's permissive namespace.
  const t = getTs();
  const src = readFileSync(fp, "utf8");
  const sf = t.createSourceFile(fp, src, t.ScriptTarget.ESNext, true, t.ScriptKind.TS);
  const names = new Set();
  for (const st of sf.statements) {
    const hasExport = st.modifiers && st.modifiers.some((m) => m.kind === t.SyntaxKind.ExportKeyword);
    if (!hasExport) continue;
    if (t.isFunctionDeclaration(st) || t.isClassDeclaration(st) || t.isInterfaceDeclaration(st) || t.isTypeAliasDeclaration(st) || t.isEnumDeclaration(st)) {
      if (st.name) names.add(st.name.text);
    } else if (t.isVariableStatement(st)) {
      for (const d of st.declarationList.declarations) {
        if (t.isIdentifier(d.name)) names.add(d.name.text);
      }
    } else if (t.isExportDeclaration(st) && st.exportClause && t.isNamedExports(st.exportClause)) {
      for (const el of st.exportClause.elements) names.add(el.name.text);
    }
  }
  return names;
}

export async function load(url, context, nextLoad) {
  if (process.env.BUNNODE_LOAD_MARK && url.startsWith("file://")) {
    console.error("[load-marker] ", fileURLToPath(url));
  }
  if (url.startsWith("mock://")) {
    const abs = url.slice("mock://".length);
    const factory = mocks().get(abs);
    if (!factory) return { format: "module", source: "export default undefined;", shortCircuit: true };
    const ns = typeof factory === "function" ? factory() : factory;
    const keys = new Set(Object.keys(ns || {}));
    for (const n of realModuleExportNames(abs)) keys.add(n);
    const exportsSrc = [...keys].map((k) => `export const ${safeId(k)} = __ns[${JSON.stringify(k)}];`).join("\n");
    const src = `const __ns = globalThis.__bunNodeMockFactory(${JSON.stringify(abs)})();\n${exportsSrc}\nexport default __ns;\n`;
    return { format: "module", source: src, shortCircuit: true };
  }

  if (url.startsWith("file://")) {
    const fp = fileURLToPath(url);
    // Transpile ALL TypeScript ourselves: node's built-in TS strip (amaro)
    // requires WebAssembly, which --jitless disables.
    if (fp.endsWith(".ts") || fp.endsWith(".tsx") || fp.endsWith(".mts")) {
      const source = readFileSync(fp, "utf8");
      const __cacheDir = process.env.BUNNODE_TSCACHE_DIR;
      if (__cacheDir) {
        try {
          const __st = statSync(fp);
          const __key = createHash("sha1").update(fp + ":" + __st.mtimeMs + ":" + __st.size).digest("hex");
          const __cpath = __cacheDir + "/" + __key + ".mjs";
          if (isFile(__cpath)) {
            return { format: "module", source: readFileSync(__cpath, "utf8"), shortCircuit: true };
          }
        } catch {}
      }
      const t = getTs();
      const out = t.transpileModule(source, {
        fileName: fp,
        compilerOptions: {
          module: t.ModuleKind.ESNext,
          target: t.ScriptTarget.ESNext,
          jsx: fp.endsWith(".tsx") ? t.JsxEmit.ReactJSX : undefined,
          esModuleInterop: true,
          allowJs: true,
          resolveJsonModule: true,
          isolatedModules: true,
          verbatimModuleSyntax: false,
          sourceMap: false,
        },
      });
      let code = out.outputText;
      // bun allows `require(...)` from ESM; node does not. Inject a
      // per-module require so tests using CJS-require-style access work.
      if (/\brequire\s*\(/.test(source) && !code.includes("__bunCreateRequire")) {
        code =
          `import { createRequire as __bunCreateRequire } from "node:module";\n` +
          `const __bunReqBase = __bunCreateRequire(import.meta.url);\n` +
          `const require = (__bunReqId) => {\n` +
          `  try { return __bunReqBase(__bunReqId); }\n` +
          `  catch (__bunReqErr) {\n` +
          `    if (__bunReqErr && (__bunReqErr.code === "MODULE_NOT_FOUND" || __bunReqErr.code === "ERR_REQUIRE_ESM" || __bunReqErr.code === "ERR_UNKNOWN_FILE_EXTENSION")) {\n` +
          `      for (const __bunReqExt of [".ts", ".tsx"]) {\n` +
          `        try { return __bunReqBase(__bunReqId + __bunReqExt); } catch {}\n` +
          `      }\n` +
          `    }\n` +
          `    throw __bunReqErr;\n` +
          `  }\n` +
          `};\n` +
          code;
      }
      // Circular-dependency TDZ fix: modules that top-level read an import
      // binding which is itself mid-evaluation due to a cycle (e.g.
      // manager.ts -> tool-definitions.ts -> ... -> manager.ts) crash with
      // "Cannot access 'X' before initialization". bun bundles modules and
      // thus never hits node's strict ESM TDZ here. Replace the top-level
      // read with a lazily-filled proxy array: the first array access (after
      // the whole module graph finished evaluating) computes the keys. A
      // queueMicrotask is NOT enough — node ESM evaluation can suspend at
      // top-level awaits, draining the microtask queue before the dependency
      // finished initializing.
      if (code.includes("export const TOOL_NAMES = Object.keys(TOOL_DEFINITIONS)")) {
        code = code.replace(
          /export const TOOL_NAMES = Object\.keys\(TOOL_DEFINITIONS\)(?: as ToolName\[\])?;/,
          `const __bunToolNames = [];
            export const TOOL_NAMES = new Proxy(__bunToolNames, {
              get(target, prop, receiver) {
                try {
                  if (__bunToolNames.length === 0 && Object.keys(TOOL_DEFINITIONS).length > 0) {
                    __bunToolNames.push(...Object.keys(TOOL_DEFINITIONS));
                  }
                } catch { /* dependency still mid-evaluation; retry on next access */ }
                return Reflect.get(target, prop, receiver);
              },
            });`,
        );
      }
      // This OpenHarmony node build returns undefined/broken values for
      // import.meta.dir / import.meta.filename; polyfill them per-module.
      if (code.includes("import.meta.dir") || code.includes("import.meta.filename")) {
        code =
          `import { fileURLToPath as __bunMetaToPath } from "node:url";\n` +
          `import __bunMetaPath from "node:path";\n` +
          `const __bunMetaDir = __bunMetaPath.dirname(__bunMetaToPath(import.meta.url));\n` +
          `const __bunMetaFilename = __bunMetaToPath(import.meta.url);\n` +
          code
            .replaceAll("import.meta.dir", "__bunMetaDir")
            .replaceAll("import.meta.filename", "__bunMetaFilename");
      }
      if (__cacheDir) {
        try {
          const __st = statSync(fp);
          const __key = createHash("sha1").update(fp + ":" + __st.mtimeMs + ":" + __st.size).digest("hex");
          const __tmp = __cacheDir + "/." + __key + "." + process.pid + ".tmp";
          writeFileSync(__tmp, code);
          renameSync(__tmp, __cacheDir + "/" + __key + ".mjs");
        } catch {}
      }
      return { format: "module", source: code, shortCircuit: true };
    }
    if (!fp.startsWith(SRC + path.sep) && !fp.startsWith(BASE + path.sep)) {
      return nextLoad(url, context);
    }
    if (fp.endsWith(".cts")) {
      const source = readFileSync(fp, "utf8");
      const t = getTs();
      const out = t.transpileModule(source, {
        fileName: fp,
        compilerOptions: { module: t.ModuleKind.CommonJS, target: t.ScriptTarget.ESNext, esModuleInterop: true, sourceMap: false },
      });
      return { format: "commonjs", source: out.outputText, shortCircuit: true };
    }
    if (fp.endsWith(".json")) {
      const raw = readFileSync(fp, "utf8");
      return { format: "module", source: "export default " + raw + ";", shortCircuit: true };
    }
    // bun-style text asset imports: .md/.mdx/.txt/.html/.css/.svg/... default-export the raw string
    if (/\.(md|mdx|txt|html|htm|css|scss|sass|less|svg|yaml|yml|csv|xml|sql|wasm|ico|pdf)$/.test(fp)) {
      const raw = readFileSync(fp, "utf8");
      return { format: "module", source: "export default " + JSON.stringify(raw) + ";", shortCircuit: true };
    }
    if (/\.(png|jpg|jpeg|gif|webp|woff2?|ttf|eot|mp3|wav|ogg)$/.test(fp)) {
      return { format: "module", source: "export default {};", shortCircuit: true };
    }
  }

  return nextLoad(url, context);
}

function safeId(k) {
  return /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(k) ? k : `__k_${Buffer.from(k).toString("hex")}`;
}

