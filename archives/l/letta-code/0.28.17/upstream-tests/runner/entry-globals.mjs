// entry-globals.mjs — global install for node processes launched as
// `node --import=entry-globals.mjs <file.ts>` (i.e. the CLI and mock-subagent
// children spawned via the rewritten `node run <ts>` invocation). Installs the
// fetch polyfill and Bun globals so plain .ts entrypoints (which assume a bun
// runtime) can start under --jitless OpenHarmony node.
import { installFetchPolyfill } from "./fetch-polyfill.mjs";
import { installBunGlobals } from "./bun-globals.mjs";
import { installBunServe } from "./bun-serve.mjs";
import { installSpawnPatch } from "./spawn-patch.mjs";

installFetchPolyfill();
installBunGlobals();
installBunServe();
installSpawnPatch();
