// mock-bridge.mjs — shared helpers for the bun:test mock.module bridge.
// The loader hooks run in a separate worker thread, so the main thread's
// globalThis is not visible there. We bridge mock registrations through a
// tiny JSON state file; the actual factories stay in the main-thread
// globalThis (they may close over test-file variables).
import { readFileSync, writeFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import os from "node:os";
import path from "node:path";

// /tmp is read-only on this box; use the user home for the mock state file.
// The state file is per-process (pid-suffixed) so a previous run's
// registrations never leak into a new process and cause the loader to point
// at a mock whose cache was not populated in this process.
const stateDir = process.env.HOME ? path.join(process.env.HOME, ".bunnode") : os.tmpdir();
try { mkdirSync(stateDir, { recursive: true }); } catch {}
export const MOCK_STATE = path.join(stateDir, `bunnode-mocks-${process.pid}.json`);

let cachedState = null;
let cachedMtime = -1;
export function readMockState() {
  try {
    if (cachedState === null) {
      if (!existsSync(MOCK_STATE)) { cachedState = {}; cachedMtime = -1; return cachedState; }
      cachedState = JSON.parse(readFileSync(MOCK_STATE, "utf8"));
      cachedMtime = Date.now();
      return cachedState;
    }
    if (Date.now() - cachedMtime < 50) return cachedState;
    const st = statSync(MOCK_STATE);
    if (st.mtimeMs === cachedMtime) { cachedMtime = Date.now(); return cachedState; }
    cachedState = JSON.parse(readFileSync(MOCK_STATE, "utf8"));
    cachedMtime = Date.now();
    return cachedState;
  } catch {
    return cachedState || {};
  }
}
export function writeMockState(state) {
  try {
    writeFileSync(MOCK_STATE, JSON.stringify(state));
  } catch (e) {
    console.error("[bunnode] mock state write failed:", e.message);
  }
}
