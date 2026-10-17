// bun-expect.mjs — a jest/bun-compatible `expect` implementation for node.
// Used by bun-test-shim.mjs. Self-contained (no deps beyond node builtins).
import { isDeepStrictEqual } from "node:util";

// ---------- asymmetric matchers ----------
function isAsymmetric(v) {
  return v !== null && typeof v === "object" && typeof v.asymmetricMatch === "function";
}

export function makeAsymmetric(kind, payload) {
  return {
    asymmetricMatch(actual, eq) {
      switch (kind) {
        case "any":
          return typeof payload === "function"
            ? actual instanceof payload || actual?.constructor === payload
            : actual === payload;
        case "anything":
          return actual !== null && actual !== undefined;
        case "stringContaining":
          return typeof actual === "string" && actual.includes(payload);
        case "stringMatching":
          return typeof actual === "string" && new RegExp(payload).test(actual);
        case "objectContaining":
          return actual !== null && typeof actual === "object" && partialMatch(actual, payload, eq);
        case "arrayContaining":
          return (
            Array.isArray(actual) &&
            payload.every((item) => actual.some((a) => eq(a, item)))
          );
        case "closeTo":
          return (
            typeof actual === "number" &&
            Math.abs(actual - payload.value) < payload.precision
          );
        default:
          return false;
      }
    },
    // helper used by toEqual / toHaveBeenCalledWith deep comparisons
  };
}

// ---------- deep equality (jest toEqual-ish) ----------
function normalize(v) {
  // strip undefined-valued own props on plain objects (jest toEqual ignores them)
  if (v === null || typeof v !== "object") return v;
  if (Array.isArray(v)) return v.map(normalize);
  if (v instanceof Date || v instanceof RegExp || v instanceof Map || v instanceof Set) return v;
  const proto = Object.getPrototypeOf(v);
  if (proto !== Object.prototype && proto !== null) return v; // class instance / typed array / buffer
  const out = {};
  for (const k of Object.keys(v)) {
    if (v[k] === undefined) continue;
    out[k] = normalize(v[k]);
  }
  return out;
}

function deepEqual(a, b, seen = new Set()) {
  if (isAsymmetric(a)) return a.asymmetricMatch(b, deepEqual);
  if (isAsymmetric(b)) return b.asymmetricMatch(a, deepEqual);
  if (Object.is(a, b)) return true;
  if (a === null || b === null) return false;
  if (typeof a !== typeof b) return false;
  if (typeof a !== "object") return false;
  if (a instanceof Date || b instanceof Date) return a instanceof Date && b instanceof Date && a.getTime() === b.getTime();
  if (a instanceof RegExp || b instanceof RegExp) return a instanceof RegExp && b instanceof RegExp && a.source === b.source && a.flags === b.flags;
  if (a instanceof Error || b instanceof Error) return a instanceof Error && b instanceof Error && a.name === b.name && a.message === b.message;
  if (a instanceof Map && b instanceof Map) {
    if (a.size !== b.size) return false;
    for (const [k, v] of a) if (!deepEqual(b.get(k), v, seen)) return false;
    return true;
  }
  if (a instanceof Set && b instanceof Set) {
    if (a.size !== b.size) return false;
    for (const v of a) if (![...b].some((x) => deepEqual(x, v, seen))) return false;
    return true;
  }
  // typed arrays / buffers
  if (ArrayBuffer.isView(a) && ArrayBuffer.isView(b)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
    return true;
  }
  const aArr = Array.isArray(a);
  const bArr = Array.isArray(b);
  if (aArr !== bArr) return false;
  if (aArr) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (i in a !== i in b) {
        // hole vs undefined: jest toEqual treats undefined array items as equal
      }
      if (!deepEqual(a[i], b[i], seen)) return false;
    }
    return true;
  }
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length) return false;
  for (const k of aKeys) {
    if (!Object.prototype.hasOwnProperty.call(b, k)) return false;
    if (!deepEqual(a[k], b[k], seen)) return false;
  }
  return true;
}

// jest toEqual uses this normalized variant (ignores undefined props)
function toEqual(a, b) {
  return deepEqual(normalize(a), normalize(b));
}

// ---------- toMatchObject ----------
function partialMatch(received, expected, eq) {
  if (isAsymmetric(expected)) return expected.asymmetricMatch(received, eq);
  if (Array.isArray(expected)) {
    if (!Array.isArray(received)) return false;
    // expected must be an ordered subsequence-ish match
    let ri = 0;
    for (const e of expected) {
      let found = false;
      while (ri < received.length) {
        if (partialMatch(received[ri], e, eq)) {
          found = true;
          ri++;
          break;
        }
        ri++;
      }
      if (!found) return false;
    }
    return true;
  }
  if (expected && typeof expected === "object") {
    if (received === null || typeof received !== "object") return false;
    for (const k of Object.keys(expected)) {
      const e = expected[k];
      if (e === undefined) continue;
      if (!(k in received)) return false;
      if (!partialMatch(received[k], e, eq)) return false;
    }
    return true;
  }
  return eq(received, expected);
}

// ---------- mock detection ----------
function mockCalls(fn) {
  return fn && typeof fn === "function" && fn.mock && Array.isArray(fn.mock.calls) ? fn.mock.calls : null;
}

// ---------- printing ----------
function fmt(v) {
  try {
    return require_node_util_inspect(v);
  } catch {
    return String(v);
  }
}
let _inspect;
function require_node_util_inspect(v) {
  if (!_inspect) _inspect = process.getBuiltinModule ? process.getBuiltinModule("util").inspect : undefined;
  return _inspect ? _inspect(v, { depth: 5, maxArrayLength: 20 }) : JSON.stringify(v);
}

function describeExpectation(received, expected, matcher, negate) {
  return `expected${negate ? " NOT" : ""} ${matcher}\n  received: ${fmt(received)}\n  expected: ${fmt(expected)}`;
}

// ---------- the expect object ----------
export function expect(actual, message) {
  const base = { actual, negate: false };

  function fail(msg) {
    const err = new Error(message ? `${msg}\n---\n${message}` : msg);
    err.name = "AssertionError";
    throw err;
  }

  function check(pass, msg) {
    if (base.negate ? pass : !pass) fail(msg);
  }

  const m = {
    toBe(expected) {
      const pass = Object.is(actual, expected);
      check(pass, describeExpectation(actual, expected, "toBe", base.negate));
    },
    toEqual(expected) {
      const pass = toEqual(actual, expected);
      check(pass, describeExpectation(actual, expected, "toEqual", base.negate));
    },
    toMatchObject(expected) {
      const pass = partialMatch(actual, expected, deepEqual);
      check(pass, describeExpectation(actual, expected, "toMatchObject", base.negate));
    },
    toBeNull() { check(actual === null, `expected${base.negate ? " NOT" : ""} to be null, received ${fmt(actual)}`); },
    toBeUndefined() { check(actual === undefined, `expected${base.negate ? " NOT" : ""} to be undefined, received ${fmt(actual)}`); },
    toBeDefined() { check(actual !== undefined, `expected${base.negate ? " NOT" : ""} to be defined, received ${fmt(actual)}`); },
    toBeTruthy() { check(Boolean(actual), `expected${base.negate ? " NOT" : ""} to be truthy, received ${fmt(actual)}`); },
    toBeFalsy() { check(!actual, `expected${base.negate ? " NOT" : ""} to be falsy, received ${fmt(actual)}`); },
    toBeNaN() { check(Number.isNaN(actual), `expected${base.negate ? " NOT" : ""} to be NaN, received ${fmt(actual)}`); },
    toBeNumber() { check(typeof actual === "number" && !Number.isNaN(actual), `expected${base.negate ? " NOT" : ""} to be a number, received ${fmt(actual)}`); },
    toBeString() { check(typeof actual === "string", `expected${base.negate ? " NOT" : ""} to be a string, received ${fmt(actual)}`); },
    toBeArray() { check(Array.isArray(actual), `expected${base.negate ? " NOT" : ""} to be an array, received ${fmt(actual)}`); },
    toBeObject() { check(actual !== null && typeof actual === "object" && !Array.isArray(actual), `expected${base.negate ? " NOT" : ""} to be an object, received ${fmt(actual)}`); },
    toBeTrue() { check(actual === true, `expected${base.negate ? " NOT" : ""} to be true, received ${fmt(actual)}`); },
    toBeFalse() { check(actual === false, `expected${base.negate ? " NOT" : ""} to be false, received ${fmt(actual)}`); },
    toBeInteger() { check(Number.isInteger(actual), `expected${base.negate ? " NOT" : ""} to be an integer, received ${fmt(actual)}`); },
    toBeInstanceOf(ctor) { check(actual instanceof ctor, `expected${base.negate ? " NOT" : ""} to be instance of ${ctor.name}`); },
    toBeTypeOf(type) { check(typeof actual === type, `expected${base.negate ? " NOT" : ""} typeof ${type}, got ${typeof actual}`); },
    toBeGreaterThan(n) { check(typeof actual === "number" && actual > n, describeExpectation(actual, n, "toBeGreaterThan", base.negate)); },
    toBeGreaterThanOrEqual(n) { check(typeof actual === "number" && actual >= n, describeExpectation(actual, n, "toBeGreaterThanOrEqual", base.negate)); },
    toBeLessThan(n) { check(typeof actual === "number" && actual < n, describeExpectation(actual, n, "toBeLessThan", base.negate)); },
    toBeLessThanOrEqual(n) { check(typeof actual === "number" && actual <= n, describeExpectation(actual, n, "toBeLessThanOrEqual", base.negate)); },
    toBeCloseTo(n, digits = 2) {
      const precision = Math.pow(10, -digits) / 2;
      check(Math.abs(actual - n) < precision, `expected ${actual} to be close to ${n} (${digits} digits)`);
    },
    toBeOneOf(arr) { check(Array.isArray(arr) && arr.some((x) => Object.is(x, actual)), `expected ${fmt(actual)} to be one of ${fmt(arr)}`); },
    toContain(item) {
      let pass = false;
      if (typeof actual === "string") pass = actual.includes(String(item));
      else if (Array.isArray(actual)) pass = actual.some((x) => Object.is(x, item) || x === item);
      else if (actual && typeof actual[Symbol.iterator] === "function") pass = [...actual].some((x) => Object.is(x, item));
      else if (actual instanceof Set) pass = actual.has(item);
      check(pass, describeExpectation(actual, item, "toContain", base.negate));
    },
    toContainEqual(item) {
      let pass = false;
      if (Array.isArray(actual)) pass = actual.some((x) => toEqual(x, item));
      else if (actual instanceof Set) pass = [...actual].some((x) => toEqual(x, item));
      check(pass, describeExpectation(actual, item, "toContainEqual", base.negate));
    },
    toContainKey(key) {
      const pass = actual !== null && typeof actual === "object" && key in actual;
      check(pass, describeExpectation(actual, key, "toContainKey", base.negate));
    },
    toHaveLength(n) { check(actual != null && actual.length === n, `expected length ${n}, got ${actual?.length}`); },
    toHaveProperty(key, value) {
      let pass = key in Object(actual) || hasNested(actual, key);
      if (pass && arguments.length > 1) pass = deepEqual(resolveNested(actual, key), value);
      check(pass, describeExpectation(actual, key, "toHaveProperty", base.negate));
    },
    toMatch(pat) {
      const pass = typeof pat === "string" ? String(actual).includes(pat) : new RegExp(pat).test(String(actual));
      check(pass, describeExpectation(actual, pat, "toMatch", base.negate));
    },
    toStartWith(s) { check(typeof actual === "string" && actual.startsWith(s), `expected "${actual}"${base.negate ? " NOT" : ""} to start with "${s}"`); },
    toEndWith(s) { check(typeof actual === "string" && actual.endsWith(s), `expected "${actual}"${base.negate ? " NOT" : ""} to end with "${s}"`); },
    toInclude(s) { this.toContain(s); },
    toIncludeMultiple(strs) { check(Array.isArray(strs) && strs.every((s) => String(actual).includes(s)), `expected "${actual}"${base.negate ? " NOT" : ""} to include all of ${fmt(strs)}`); },
    toSatisfy(fn) { check(typeof fn === "function" && fn(actual), `expected${base.negate ? " NOT" : ""} to satisfy predicate`); },
    toHaveBeenCalled() {
      const c = mockCalls(actual);
      check(c !== null && c.length > 0, `expected${base.negate ? " NOT" : ""} mock to have been called (calls: ${c?.length ?? "not a mock"})`);
    },
    toHaveBeenCalledTimes(n) {
      const c = mockCalls(actual);
      check(c !== null && c.length === n, `expected mock called ${n} times, got ${c?.length}`);
    },
    toHaveBeenCalledWith(...args) {
      const c = mockCalls(actual);
      const pass = c !== null && c.some((call) => toEqual(call, args));
      check(pass, `expected${base.negate ? " NOT" : ""} mock to have been called with ${fmt(args)}; calls: ${fmt(c ?? null)}`);
    },
    toHaveBeenLastCalledWith(...args) {
      const c = mockCalls(actual);
      const pass = c !== null && c.length > 0 && toEqual(c[c.length - 1], args);
      check(pass, `expected${base.negate ? " NOT" : ""} last call ${fmt(c?.[c.length - 1])} to equal ${fmt(args)}`);
    },
    toHaveBeenNthCalledWith(n, ...args) {
      const c = mockCalls(actual);
      const pass = c !== null && c.length >= n && toEqual(c[n - 1], args);
      check(pass, `expected${base.negate ? " NOT" : ""} nth call ${n} to equal ${fmt(args)}; calls: ${fmt(c ?? null)}`);
    },
    toHaveReturned() {
      const c = mockCalls(actual);
      const pass = c !== null && c.length > 0;
      check(pass, `expected${base.negate ? " NOT" : ""} mock to have returned`);
    },
    toHaveReturnedTimes(n) {
      const c = mockCalls(actual);
      check(c !== null && c.length === n, `expected mock returned ${n} times, got ${c?.length}`);
    },
    toHaveReturnedWith(v) {
      const c = mockCalls(actual);
      const pass = c !== null && c.some((_, i) => actual.mock.results[i]?.value !== undefined && toEqual(actual.mock.results[i].value, v));
      check(pass, `expected${base.negate ? " NOT" : ""} mock to have returned ${fmt(v)}`);
    },
    toThrow(expected) {
      let threw = false;
      let err = null;
      try {
        const r = typeof actual === "function" ? actual() : actual;
        if (r && typeof r.then === "function") {
          // async function passed to toThrow — bun/jest require rejects for async; surface clearly
          err = new Error("toThrow called on a Promise; use expect(p).rejects instead");
        } else if (r instanceof Error) {
          // actual is an already-caught error (e.g. expect(p).rejects.toThrow(...))
          threw = true;
          err = r;
        }
      } catch (e) {
        threw = true;
        err = e;
      }
      let pass = false;
      if (threw) {
        if (expected === undefined) pass = true;
        else if (typeof expected === "string") pass = String(err.message).includes(expected);
        else if (expected instanceof RegExp) pass = expected.test(String(err.message));
        else if (typeof expected === "function" && !(expected instanceof RegExp)) pass = err instanceof expected;
        else if (expected && typeof expected === "object") pass = toEqual(err.message, expected.message) && (expected.name ? err.name === expected.name : true);
      }
      check(pass, threw
        ? `expected${base.negate ? " NOT" : ""} to throw ${fmt(expected)}; got ${err?.stack || err}`
        : `expected${base.negate ? " NOT" : ""} to throw, but nothing was thrown`);
    },
  };
  // bun/jest aliases: toThrowError === toThrow
  m.toThrowError = m.toThrow;

  // resolves / rejects (async)
  const asyncApi = {};
  for (const name of Object.keys(m)) {
    asyncApi[name] = async function (...args) {
      const which = this && this.which ? this.which : null;
      const negate = this && this.negate ? true : false;
      let value, rejected = false, reason = null;
      try {
        value = await actual;
      } catch (e) {
        rejected = true;
        reason = e;
      }
      if (negate) {
        throw new Error("expect().resolves/rejects does not support .not");
      }
      if (which === "resolves") {
        if (rejected) fail(`expected promise to resolve, but it rejected: ${fmt(reason)}`);
        return expect(value)[name](...args);
      }
      if (rejected) return expect(reason)[name](...args);
      fail(`expected promise to reject, but it resolved: ${fmt(value)}`);
    };
  }

  const api = { ...m };
  Object.defineProperty(api, "not", {
    get() {
      base.negate = true;
      const nm = {};
      for (const name of Object.keys(m)) {
        nm[name] = (...args) => {
          try {
            return m[name](...args);
          } finally {
            base.negate = false;
          }
        };
      }
      return nm;
    },
    configurable: true,
  });
  api.resolves = Object.freeze(Object.fromEntries(Object.keys(m).map((name) => [name, asyncApi[name].bind({ ...base, which: "resolves" })])));
  api.rejects = Object.freeze(Object.fromEntries(Object.keys(m).map((name) => [name, asyncApi[name].bind({ ...base, which: "rejects" })])));

  // catch-all: throw a clear "matcher not implemented" so we can add it
  return new Proxy(api, {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (typeof prop === "symbol") return undefined;
      return function () {
        fail(`matcher .${prop}() is not implemented by the bun→node shim yet`);
      };
    },
  });
}

function hasNested(obj, key) {
  const parts = String(key).split(".");
  let cur = obj;
  for (const p of parts) {
    if (cur == null || !(p in Object(cur))) return false;
    cur = cur[p];
  }
  return true;
}
function resolveNested(obj, key) {
  const parts = String(key).split(".");
  let cur = obj;
  for (const p of parts) cur = cur?.[p];
  return cur;
}

// static helpers on expect
expect.any = (ctor) => makeAsymmetric("any", ctor);
expect.anything = () => makeAsymmetric("anything");
expect.stringContaining = (s) => makeAsymmetric("stringContaining", s);
expect.stringMatching = (re) => makeAsymmetric("stringMatching", re);
expect.objectContaining = (o) => makeAsymmetric("objectContaining", o);
expect.arrayContaining = (arr) => makeAsymmetric("arrayContaining", arr);
expect.closeTo = (value, precision = 2) => makeAsymmetric("closeTo", { value, precision: Math.pow(10, -precision) / 2 });
// jest/bun also expose negated asymmetric matchers via expect.not.<helper>.
function negateAsymmetric(a) {
  return { asymmetricMatch: (actual, eq) => !a.asymmetricMatch(actual, eq) };
}
expect.not = {
  any: (ctor) => negateAsymmetric(expect.any(ctor)),
  anything: () => negateAsymmetric(expect.anything()),
  stringContaining: (s) => negateAsymmetric(expect.stringContaining(s)),
  stringMatching: (re) => negateAsymmetric(expect.stringMatching(re)),
  objectContaining: (o) => negateAsymmetric(expect.objectContaining(o)),
  arrayContaining: (arr) => negateAsymmetric(expect.arrayContaining(arr)),
  closeTo: (value, precision) => negateAsymmetric(expect.closeTo(value, precision)),
};
expect.extend = () => {};
expect.addEqualityTesters = () => {};

export { toEqual as __toEqual, partialMatch as __partialMatch, deepEqual as __deepEqual };
