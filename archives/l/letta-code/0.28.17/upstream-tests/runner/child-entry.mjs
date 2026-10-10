// child-entry.mjs — per-test-file process bootstrap. Usage:
//   node --import bunnode/loader.mjs child-entry.mjs <abs test file path>
// Imports the test file, then runs the collected bun:test suites and prints
// a single BUNNODE_RESULT <json> line to stdout, then exits.
import { pathToFileURL } from "node:url";
import { installFetchPolyfill } from "./fetch-polyfill.mjs";
import { installSpawnPatch } from "./spawn-patch.mjs";

// --jitless disables WebAssembly, so undici's fetch cannot load its wasm
// llhttp parser. Install a node:http-based fetch polyfill in that case.
installFetchPolyfill();

// Spawn-path normalization (system dirs on PATH) + `node run <ts>` rewrite.
installSpawnPatch();

const testFile = process.argv[2];
if (!testFile) {
  process.stderr.write("ENTRY_ERROR: no test file argument\n");
  process.exit(2);
}
globalThis.__bunNodeTestFile = testFile;

try {
  // Load the shim FIRST so its pre-registration hook can materialize lazy
  // mocks for every mock.module(...) specifier the test file declares, BEFORE
  // node resolves the test file's static import graph (recovery.ts → stream).
  const shim = await import("bun:test");
  if (typeof shim.__bunNodePreRegisterLazyMocks === "function") {
    shim.__bunNodePreRegisterLazyMocks(testFile);
  }
  await import(pathToFileURL(testFile).href);
  await shim.__bunNodeDrain();
  await shim.__bunNodeRunAll();
  process.exit(0); // runAll already exits; safety net
} catch (e) {
  process.stderr.write("ENTRY_ERROR\n" + ((e && e.stack) || String(e)) + "\n");
  process.exit(3);
}
