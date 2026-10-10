// fs-link-shim.mjs — OpenHarmony's filesystem returns EPERM for link()
// (hard links unsupported). Preserve the atomic-create semantics tests rely
// on (e.g. the manual-instance lock publishes a hard link so a concurrent
// process fails with EEXIST): fall back to an O_EXCL write of the source
// bytes, which still fails with EEXIST if the target already exists.
import { link as origLink, readFile, writeFile } from "node:fs/promises";
import { linkSync as origLinkSync, readFileSync, writeFileSync } from "node:fs";

export const link = async (existingPath, newPath) => {
  try {
    return await origLink(existingPath, newPath);
  } catch (e) {
    if (e && e.code === "EPERM") {
      const data = await readFile(existingPath);
      await writeFile(newPath, data, { flag: "wx" });
      return;
    }
    throw e;
  }
};

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

export * from "node:fs/promises";
export { default } from "node:fs/promises";
