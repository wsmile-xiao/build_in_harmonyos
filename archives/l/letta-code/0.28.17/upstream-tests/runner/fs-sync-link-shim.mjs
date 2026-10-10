// fs-sync-link-shim.mjs — OpenHarmony's filesystem returns EPERM for
// linkSync() (hard links unsupported). Preserve the atomic-create semantics
// (O_EXCL) with a write fallback so the lock's EEXIST behaviour is kept.
import { linkSync as origLinkSync, readFileSync, writeFileSync } from "node:fs";

export const linkSync = (existingPath, newPath) => {
  try {
    return origLinkSync(existingPath, newPath);
  } catch (e) {
    if (e && e.code === "EPERM") {
      const data = readFileSync(existingPath);
      writeFileSync(newPath, data, { flag: "wx" });
      return;
    }
    throw e;
  }
};

export * from "node:fs";
export { default } from "node:fs";
