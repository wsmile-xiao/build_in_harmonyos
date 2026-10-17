// bun-test-shim.mjs — implements the bun:test API surface on top of plain node.
// Loaded via the module loader when a test file does `import ... from "bun:test"`.
import { expect } from "./bun-expect.mjs";
export { expect };
import { installBunGlobals } from "./bun-globals.mjs";
import { installBunServe } from "./bun-serve.mjs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";
import { existsSync, statSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import path from "node:path";
import { readMockState, writeMockState } from "./mock-bridge.mjs";

installBunGlobals();
installBunServe();

const SHIM_DIR = path.dirname(fileURLToPath(import.meta.url));
const BASE = SHIM_DIR;
const SRC = path.resolve(SHIM_DIR, "../letta-src");

// ---------------- registries ----------------
const rootSuites = [];
const suiteStack = [];
const pendingDescribes = []; // promises from async describe bodies
globalThis.__bunNodeMocks = new Map(); // resolved-abs-path -> factory

// bun attributes an unhandled rejection to the test that was running at the
// time (marking it failed) instead of crashing the whole process. node's
// default is to terminate on unhandledRejection, so mirror bun here: record
// the rejection against the active test and keep the runner alive.
const unhandledRejections = []; // { testName, error }
let activeTestName = null;
process.on("unhandledRejection", (reason) => {
  unhandledRejections.push({
    testName: activeTestName,
    error: String(reason?.stack || reason),
  });
});

let implicitRoot = null;
function ensureRoot() {
  if (!implicitRoot) {
    implicitRoot = {
      type: "describe", name: "", parent: null, tests: [], suites: [],
      beforeAll: [], afterAll: [], beforeEach: [], afterEach: [], defineError: null, isRoot: true,
    };
    rootSuites.push(implicitRoot);
  }
  return implicitRoot;
}
function currentSuite() {
  return suiteStack.length ? suiteStack[suiteStack.length - 1] : ensureRoot();
}

// ---------------- describe / test / hooks ----------------
export function describe(name, fn, opts) {
  const suite = {
    type: "describe", name, fullName: name, parent: suiteStack.length ? suiteStack[suiteStack.length - 1] : null,
    tests: [], suites: [], beforeAll: [], afterAll: [], beforeEach: [], afterEach: [],
    defineError: null, skip: !!(opts && opts.skip),
  };
  const root = suite.parent === null;
  (root ? rootSuites : suite.parent.suites).push(suite);
  suiteStack.push(suite);
  let ret;
  try {
    ret = fn();
  } catch (e) {
    suite.defineError = e;
  }
  if (ret && typeof ret.then === "function") {
    pendingDescribes.push(
      ret.then(
        () => suiteStack.splice(suiteStack.indexOf(suite), 1),
        (e) => { suite.defineError = e; suiteStack.splice(suiteStack.indexOf(suite), 1); },
      ),
    );
  } else {
    suiteStack.pop();
  }
  return suite;
}
describe.skip = (name, fn, opts) => describe(name, fn, { ...(opts || {}), skip: true });
describe.skipIf = (cond) => (name, fn, opts) => describe(name, fn, { ...(opts || {}), skip: !!cond });
describe.todoIf = (cond) => (name, fn, opts) => describe(name, fn, { ...(opts || {}), todo: true, skip: !!cond });
describe.if = (cond) => (name, fn, opts) => describe(name, fn, { ...(opts || {}), skip: !cond });

// bun's test(name, fn, options) third arg is an options object ({ timeout,
// retry, todo, skip, only }); the shim must extract the numeric timeout from
// it rather than storing the object (setTimeout(object) -> NaN -> immediate
// spurious timeout, and the abandoned body keeps running and corrupts the
// next test's temp dirs). Also accept a plain number for old-style callers.
function normalizeTestTimeout(arg) {
  if (arg && typeof arg === "object") {
    const t = Number(arg.timeout);
    return Number.isFinite(t) && t > 0 ? t : defaultTimeout();
  }
  const t = Number(arg);
  return Number.isFinite(t) && t > 0 ? t : defaultTimeout();
}

export function test(name, fn, timeout) {
  const suite = currentSuite();
  suite.tests.push({ name, fn, timeout: normalizeTestTimeout(timeout), todo: false, skip: false, suite });
  return undefined;
}
test.skip = (name, fn, timeout) => { const suite = currentSuite(); suite.tests.push({ name, fn, timeout: normalizeTestTimeout(timeout), todo: false, skip: true, suite }); };
test.skipIf = (cond) => (name, fn, timeout) => { const suite = currentSuite(); suite.tests.push({ name, fn, timeout: normalizeTestTimeout(timeout), todo: false, skip: !!cond, suite }); };
test.todoIf = (cond) => (name, fn, timeout) => { const suite = currentSuite(); suite.tests.push({ name, fn: cond ? null : fn, timeout: normalizeTestTimeout(timeout), todo: !!cond, skip: false, suite }); };
test.if = (cond) => (name, fn, timeout) => { const suite = currentSuite(); suite.tests.push({ name, fn, timeout: normalizeTestTimeout(timeout), todo: false, skip: !cond, suite }); };
test.todo = (name) => { const suite = currentSuite(); suite.tests.push({ name, fn: null, timeout: 0, todo: true, skip: false, suite }); };
test.only = test;
test.each = (rows) => (name, fn) => {
  const suite = currentSuite();
  for (const row of rows) {
    const args = Array.isArray(row) ? row : [row];
    suite.tests.push({
      name: typeof name === "string" ? name : name(...args),
      fn: () => fn(...args), timeout: defaultTimeout(), todo: false, skip: false, suite,
    });
  }
};
test.todo.each = test.todo;

export const it = test;
it.skip = test.skip;
it.todo = test.todo;
it.each = test.each;

function hookFor(which) {
  return (fn) => { currentSuite()[which].push(fn); };
}
export const beforeAll = hookFor("beforeAll");
export const afterAll = hookFor("afterAll");
export const beforeEach = hookFor("beforeEach");
export const afterEach = hookFor("afterEach");

function defaultTimeout() {
  const t = Number(process.env.BUNNODE_TIMEOUT_MS);
  return Number.isFinite(t) && t > 0 ? t : 30000;
}

// ---------------- mock / spyOn ----------------
export function mock(fn) {
  const data = { calls: [], results: [], instances: [], impl: typeof fn === "function" ? fn : undefined, onceQueue: [] };
  const m = function (...args) {
    data.calls.push(args);
    data.instances.push(this);
    let impl = data.impl;
    if (data.onceQueue.length) impl = data.onceQueue.shift();
    try {
      const r = impl ? impl.apply(this, args) : undefined;
      data.results.push({ type: "return", value: r });
      return r;
    } catch (e) {
      data.results.push({ type: "throw", value: e });
      throw e;
    }
  };
  Object.defineProperty(m, "mock", { value: data, enumerable: false, configurable: true });
  Object.defineProperty(m, "getMockName", { value: () => "mock", enumerable: false });
  m.mockReset = () => { data.calls.length = 0; data.results.length = 0; data.instances.length = 0; data.onceQueue.length = 0; data.impl = typeof fn === "function" ? fn : undefined; return m; };
  m.mockClear = () => { data.calls.length = 0; data.results.length = 0; data.instances.length = 0; return m; };
  m.mockRestore = () => { data.calls.length = 0; data.results.length = 0; data.instances.length = 0; data.onceQueue.length = 0; data.impl = typeof fn === "function" ? fn : undefined; return m; };
  m.mockImplementation = (f) => { data.impl = f; return m; };
  m.mockImplementationOnce = (f) => { data.onceQueue.push(f); return m; };
  m.mockReturnValue = (v) => { data.impl = () => v; return m; };
  m.mockReturnValueOnce = (v) => { data.onceQueue.push(() => v); return m; };
  m.mockResolvedValue = (v) => { data.impl = async () => v; return m; };
  m.mockResolvedValueOnce = (v) => { data.onceQueue.push(async () => v); return m; };
  m.mockRejectedValue = (e) => { data.impl = async () => { throw e; }; return m; };
  m.mockRejectedValueOnce = (e) => { data.onceQueue.push(async () => { throw e; }); return m; };
  m.mockName = (n) => { m.getMockName = () => n; return m; };
  Object.defineProperty(m, "lastCall", {
    get() { return data.calls.length ? data.calls[data.calls.length - 1] : undefined; },
    configurable: true,
  });
  return m;
}
mock.module = (spec, factory) => { registerMockModule(spec, factory); };
mock.restore = () => {};

export function spyOn(obj, key) {
  const descriptor = Object.getOwnPropertyDescriptor(obj, key);
  const original = descriptor && typeof descriptor.value === "function" ? descriptor.value : (typeof obj[key] === "function" ? obj[key] : undefined);
  const m = mock(original ? original.bind(obj) : undefined);
  const realRestore = m.mockRestore;
  m.mockRestore = () => {
    realRestore();
    if (descriptor) Object.defineProperty(obj, key, descriptor);
    else if (original) obj[key] = original;
    return m;
  };
  Object.defineProperty(obj, key, { value: m, configurable: true, writable: true, enumerable: descriptor ? descriptor.enumerable : true });
  return m;
}

// ---------------- setSystemTime ----------------
const RealDate = Date;
let fakeTime = null;
let originalPerfNow = null;
export function setSystemTime(t) {
  if (t === undefined || t === null) {
    fakeTime = null;
    if (originalPerfNow) { performance.now = originalPerfNow; originalPerfNow = null; }
    Object.defineProperty(globalThis, "Date", { value: RealDate, configurable: true, writable: true });
    return;
  }
  const ms = typeof t === "number" ? t : (t instanceof RealDate ? t.getTime() : new RealDate(t).getTime());
  fakeTime = ms;
  class FakeDate extends RealDate {
    constructor(...args) {
      if (args.length === 0) super(fakeTime);
      else super(...args);
    }
    static now() { return fakeTime; }
  }
  Object.defineProperty(globalThis, "Date", { value: FakeDate, configurable: true, writable: true });
  if (!originalPerfNow) originalPerfNow = performance.now.bind(performance);
  performance.now = () => fakeTime;
}
export const setTimeOrigin = () => {};

// ---------------- mock.module ----------------
function resolveMockTarget(spec, baseDir) {
  let p = null;
  if (spec.startsWith("@/")) {
    p = path.join(SRC, "src", spec.slice(2));
  } else if (spec.startsWith("./") || spec.startsWith("../")) {
    p = path.resolve(baseDir, spec);
  } else if (path.isAbsolute(spec)) {
    p = spec;
  } else {
    return null; // external package — not mocked by the harness
  }
  if (existsSync(p) && statSync(p).isFile()) return p;
  for (const ext of [".ts", ".tsx", ".mts", ".cts", ".js", ".mjs", ".cjs", ".json", ".node", ""]) {
    const cand = p + ext;
    if (existsSync(cand) && statSync(cand).isFile()) return cand;
  }
  for (const ext of [".ts", ".tsx", ".js", ".mjs", ".json"]) {
    const idx = path.join(p, "index" + ext);
    if (existsSync(idx) && statSync(idx).isFile()) return idx;
  }
  return null;
}

function registerMockModule(spec, factory) {
  const caller = callerFileUrl();
  const base = caller ? path.dirname(fileURLToPath(caller)) : process.cwd();
  const abs = resolveMockTarget(spec, base);
  if (!abs) {
    // Cannot map to a source file — keep spec-based registration so the
    // loader can still attempt a late match, then fall back to no-op.
    return;
  }
  // Evaluate the factory NOW (main thread) and cache the resulting module
  // namespace; the loader hooks run in a worker thread and cannot see the
  // main-thread globalThis, so we materialize a real mock module file that
  // the resolve hook can point at.
  let ns = typeof factory === "function" ? factory() : factory;
  ns = ns || {};
  const cache = (globalThis.__bunNodeMockCache = globalThis.__bunNodeMockCache || new Map());
  cache.set(abs, ns);
  // bun's mock.module leaves factory-omitted keys as `undefined`; node ESM
  // instead throws "does not provide an export named X" at link time when a
  // consumer imports a name the mock file lacks. Include the real module's
  // top-level export names so those bindings exist (undefined when absent).
  const keys = new Set(Object.keys(ns));
  try {
    const realSrc = readFileSync(abs, "utf8");
    for (const m of realSrc.matchAll(
      /export\s+(?:async\s+)?(?:function|const|let|var|class|interface|type|enum|abstract\s+class)\s+([A-Za-z_$][\w$]*)/g,
    )) keys.add(m[1]);
    const named = realSrc.match(/export\s*\{([^}]*)\}/g) || [];
    for (const blk of named) {
      for (const m of blk.matchAll(/([A-Za-z_$][\w$]*)\s*(?::\s*type)?\s*(?:as\s+[A-Za-z_$][\w$]*)?/g)) {
        if (m[1]) keys.add(m[1]);
      }
    }
  } catch { /* keep factory keys only */ }
  const exportLines = [...keys].map((k) => `export const ${safeId(k)} = __ns[${JSON.stringify(k)}];`).join("\n");
  const hash = createHash("sha256").update(abs).digest("hex").slice(0, 16);
  // Registering the same module several times (e.g. a loop that mocks
  // ../agent/personality per personality) must produce a NEW module URL each
  // time, otherwise node's ESM cache serves the first registration's namespace
  // and the new factory is never used (mock called 0).
  const gen = (globalThis.__bunNodeMockGen = (globalThis.__bunNodeMockGen || 0) + 1);
  const mockFile = path.join(BASE, ".bunnode-mocks", `mock-${hash}-${gen}.mjs`);
  mkdirSync(path.dirname(mockFile), { recursive: true });
  const src = `// auto-generated mock for ${abs}\nconst __ns = globalThis.__bunNodeMockCache.get(${JSON.stringify(abs)});\n${exportLines}\nexport default __ns;\n`;
  writeFileSync(mockFile, src);
  // persist abs -> mock file so the worker-side resolve hook can find it
  const state = readMockState();
  state[abs] = mockFile;
  writeMockState(state);
}

// ---------------- lazy pre-registration ----------------
// node ESM resolves a module's ENTIRE static import graph before any of its
// top-level code runs. If a test file statically imports module A, and A
// statically imports module M, then M is resolved while the test file's
// mock.module("M", ...) call (in the test body) has NOT run yet — so M binds
// to the REAL module and the mock never applies there. send.ts/turn.ts dodge
// this because they are reached through dynamic import() (post-registration).
// Fix: scan the test file for its mock.module(..., ...) specifiers BEFORE
// importing the test file, and materialize a "lazy" mock entity for each: the
// entity re-exports the real module (so every binding a static consumer needs
// exists) and overrides function exports with forwarders that read the mock
// cache at call time, falling back to the real implementation while the cache
// is empty (mock.module not yet run). Static-graph imports then bind to the
// lazy entity instead of the real module, and the mock takes effect once
// mock.module registers the real value.
function extractMockSpecs(testFile) {
  let src;
  try { src = readFileSync(testFile, "utf8"); } catch { return []; }
  const specs = [];
  const re = /mock\.module\(\s*["'`]([^"'`]+)["'`]/g;
  let m;
  while ((m = re.exec(src))) specs.push(m[1]);
  return specs;
}

export function __bunNodePreRegisterLazyMocks(testFile) {
  const specs = extractMockSpecs(testFile);
  if (!specs.length) return;
  const baseDir = path.dirname(testFile);
  const state = readMockState();
  state.__testFile = testFile; // resolve hook: skip mock for test-file self imports
  let changed = false;
  for (const spec of specs) {
    const abs = resolveMockTarget(spec, baseDir);
    if (!abs) continue;
    const lazyFile = generateLazyMockFile(abs);
    if (lazyFile && state[abs] !== lazyFile) { state[abs] = lazyFile; changed = true; }
  }
  if (changed) writeMockState(state);
}

function generateLazyMockFile(abs) {
  const hash = createHash("sha256").update(abs).digest("hex").slice(0, 16);
  const lazyFile = path.join(BASE, ".bunnode-mocks", `mock-lazy-${hash}.mjs`);
  if (existsSync(lazyFile)) return lazyFile;
  // Real module's top-level runtime export names (functions + values; types are
  // stripped by the transpiler and only need to exist for type-only consumers).
  const keys = new Set();
  try {
    const realSrc = readFileSync(abs, "utf8");
    for (const mm of realSrc.matchAll(
      /export\s+(?:async\s+)?(?:function|const|let|var|class|interface|type|enum|abstract\s+class)\s+([A-Za-z_$][\w$]*)/g,
    )) keys.add(mm[1]);
    const named = realSrc.match(/export\s*\{([^}]*)\}/g) || [];
    for (const blk of named) {
      for (const mm of blk.matchAll(/([A-Za-z_$][\w$]*)\s*(?::\s*type)?\s*(?:as\s+[A-Za-z_$][\w$]*)?/g)) {
        if (mm[1]) keys.add(mm[1]);
      }
    }
  } catch { /* keys may be empty; forwarders for factory-only keys are missed */ }
  const realUrl = pathToFileURL(abs).href;
  const absJson = JSON.stringify(abs);
  const lines = [
    `// auto-generated LAZY mock for ${abs} (pre-registered before static graph resolves)`,
    `import * as __real from ${JSON.stringify(realUrl)};`,
    `const __abs = ${absJson};`,
    `function __val(k) {`,
    `  const ns = globalThis.__bunNodeMockCache && globalThis.__bunNodeMockCache.get(__abs);`,
    `  if (ns && ns[k] !== undefined) return ns[k];`,
    `  return __real[k];`,
    `}`,
  ];
  for (const k of keys) {
    const id = safeId(k);
    const kJson = JSON.stringify(k);
    lines.push(
      `export const ${id} = (...a) => { const __v = __val(${kJson}); return typeof __v === "function" ? __v(...a) : __v; };`,
    );
  }
  // Guarantee every runtime name the real module provides exists here, even the
  // ones our regex missed; explicit forwarders above shadow these for the keys
  // we captured. `export *` never re-exports `default`, so if the real module
  // has one it is only reachable through the named/star path when type-only.
  lines.push(`export * from ${JSON.stringify(realUrl)};`);
  mkdirSync(path.dirname(lazyFile), { recursive: true });
  writeFileSync(lazyFile, lines.join("\n") + "\n");
  return lazyFile;
}
function safeId(k) {
  // `export` is a legal identifier per the char-class test below but a
  // reserved word, so `export const export = ...` would not parse.
  return /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(k) && !/^(?:export|import|default|class|function|const|let|var|new|delete|typeof|instanceof|in|of|return|throw|if|else|for|while|do|switch|case|break|continue|try|catch|finally|this|super|extends|static|get|set|async|await|yield|void|null|true|false|enum|interface|type|implements|package|private|protected|public|abstract|readonly|declare|namespace|module|require|with|debugger)$/.test(k)
    ? k
    : `__k_${Buffer.from(k).toString("hex")}`;
}

function callerFileUrl() {
  const stack = new Error().stack.split("\n").slice(1);
  const internal = ["bun-test-shim.mjs", "bun-expect.mjs", "bun-globals.mjs", "bun-stub.mjs", "loader.mjs", "bun-test-hooks.mjs"];
  for (const line of stack) {
    const m = line.match(/\(?(file:\/\/[^)]+?)(?::\d+){1,2}\)?$/);
    if (!m) continue;
    const url = m[1];
    if (internal.some((f) => url.includes("/" + f) || url.includes(f))) continue;
    return url;
  }
  return globalThis.__bunNodeTestFile ? "file://" + globalThis.__bunNodeTestFile : null;
}

// ---------------- running ----------------
function hookErrorLabel(suite, hook) {
  return `[suite:${suite.fullName || suite.name}] ${hook}`;
}

async function runSuite(s, ancestors, results, defaultMs) {
  const chain = {
    beforeAll: [...ancestors.beforeAll, ...s.beforeAll],
    afterAll: [...ancestors.afterAll, ...s.afterAll],
    beforeEach: [...ancestors.beforeEach, ...s.beforeEach],
    afterEach: [...ancestors.afterEach, ...s.afterEach],
  };
  const prefix = s.fullName ? `${s.fullName} > ` : "";
  if (s.defineError) {
    results.push({ status: "fail", name: `[suite:${s.fullName}] define-error`, error: String(s.defineError?.stack || s.defineError) });
    return;
  }
  // A skipped suite reports all of its tests as skipped, matching bun.
  if (s.skip) {
    const markSkipped = (suite) => {
      for (const t of suite.tests) results.push({ status: "skip", name: (suite.fullName ? `${suite.fullName} > ` : "") + t.name });
      for (const child of suite.suites) markSkipped(child);
    };
    markSkipped(s);
    return;
  }
  // beforeAll (outer -> inner)
  try {
    for (const h of chain.beforeAll) await withTimeout(() => h(), defaultMs, hookErrorLabel(s, "beforeAll"));
  } catch (e) {
    results.push({ status: "fail", name: hookErrorLabel(s, "beforeAll"), error: String(e?.stack || e) });
    for (const t of s.tests) results.push({ status: "fail", name: prefix + t.name, error: "beforeAll failed" });
    return;
  }
  // tests
  for (const t of s.tests) {
    const fullName = prefix + t.name;
    if (t.todo) { results.push({ status: "todo", name: fullName }); continue; }
    if (t.skip) { results.push({ status: "skip", name: fullName }); continue; }
    try {
      for (const h of chain.beforeEach) await withTimeout(() => h(), defaultMs, hookErrorLabel(s, "beforeEach"));
      activeTestName = fullName;
      let rejectionError = null;
      try {
        await withTimeout(() => t.fn(), t.timeout || defaultMs, fullName);
      } finally {
        activeTestName = null;
        // Any unhandled rejection raised while this test ran is attributed to
        // it (bun semantics). Consume only the ones logged under this name.
        const idx = unhandledRejections.findIndex((r) => r.testName === fullName);
        if (idx !== -1) rejectionError = unhandledRejections.splice(idx, 1)[0].error;
      }
      for (const h of chain.afterEach) await withTimeout(() => h(), defaultMs, hookErrorLabel(s, "afterEach"));
      results.push(
        rejectionError
          ? { status: "fail", name: fullName, error: `[unhandled rejection] ${rejectionError}` }
          : { status: "pass", name: fullName },
      );
    } catch (e) {
      try { for (const h of chain.afterEach) await withTimeout(() => h(), defaultMs, hookErrorLabel(s, "afterEach")); } catch { /* ignore */ }
      results.push({ status: "fail", name: fullName, error: String(e?.stack || e) });
    }
  }
  // nested suites
  for (const child of s.suites) await runSuite(child, chain, results, defaultMs);
  // afterAll (inner -> outer)
  try {
    for (let i = chain.afterAll.length - 1; i >= 0; i--) {
      await withTimeout(() => chain.afterAll[i](), defaultMs, hookErrorLabel(s, "afterAll"));
    }
  } catch (e) {
    results.push({ status: "fail", name: hookErrorLabel(s, "afterAll"), error: String(e?.stack || e) });
  }
}

async function withTimeout(promiseFn, ms, label) {
  let timer;
  const timeout = new Promise((_, rej) => {
    timer = setTimeout(() => rej(new Error(`[timeout] ${label} exceeded ${ms}ms`)), ms);
  });
  try {
    return await Promise.race([Promise.resolve().then(promiseFn), timeout]);
  } finally {
    clearTimeout(timer);
  }
}

export async function __bunNodeDrain() {
  while (pendingDescribes.length) {
    const batch = pendingDescribes.splice(0);
    await Promise.all(batch);
  }
}

export async function __bunNodeRunAll() {
  await __bunNodeDrain();
  const results = [];
  const defaultMs = defaultTimeout();
  // Optional single-test filter (runner tooling only, not an upstream test
  // change): BUNNODE_TEST_PATTERN=<substring> runs only matching tests.
  const pattern = process.env.BUNNODE_TEST_PATTERN;
  // Top-level (root) hooks registered outside any describe must run for every
  // declared suite, as they do under bun. implicitRoot collects them.
  const rootChain = {
    beforeAll: implicitRoot ? implicitRoot.beforeAll : [],
    afterAll: implicitRoot ? implicitRoot.afterAll : [],
    beforeEach: implicitRoot ? implicitRoot.beforeEach : [],
    afterEach: implicitRoot ? implicitRoot.afterEach : [],
  };
  for (const suite of rootSuites) {
    if (suite === implicitRoot) continue;
    if (pattern) {
      const t = suite.tests.filter(
        (x) => x.name && x.name.includes(pattern),
      );
      if (!t.length) continue;
      suite.tests = t;
    }
    await runSuite(suite, rootChain, results, defaultMs);
  }

  // Rejections that surfaced after their test completed (e.g. a floating
  // promise settled late) are still failures — do not drop them silently.
  for (const r of unhandledRejections.splice(0)) {
    results.push({
      status: "fail",
      name: r.testName || "(unattributed unhandled rejection)",
      error: `[unhandled rejection] ${r.error}`,
    });
  }

  const passed = results.filter((r) => r.status === "pass").length;
  const failed = results.filter((r) => r.status === "fail").length;
  const todo = results.filter((r) => r.status === "todo").length;
  const skipped = results.filter((r) => r.status === "skip").length;

  process.stdout.write(
    "\nBUNNODE_RESULT " +
      JSON.stringify({ total: results.length, passed, failed, todo, skipped, results }) +
      "\n",
  );
  process.exit(failed === 0 ? 0 : 1);
}
