#!/usr/bin/env python3
"""Verify packaged debian-parl config/metadata (no upstream test suite)."""
import json
import os
import sys


def main():
    root = sys.argv[1]
    base = os.path.join(root, "share", "parl")
    cfg = os.path.join(base, "config")
    meta_path = os.path.join(base, "debian-metadata.json")

    if not os.path.isfile(meta_path):
        print("FAIL: missing debian-metadata.json")
        return 1

    meta = json.load(open(meta_path, encoding="utf-8"))
    if meta.get("debian_version") != "1.9.33+nmu1":
        print("FAIL: metadata debian_version != 1.9.33+nmu1")
        return 1
    profiles = meta.get("profiles", {})
    if sorted(profiles) != sorted(["desktop", "desktop-eu", "desktop-world"]):
        print("FAIL: profiles set mismatch")
        return 1

    # config dir: 3 nodes + 2 skel templates + Makefile/NEWS/TODO
    nodes = sorted(os.listdir(os.path.join(cfg, "nodes")))
    if nodes != ["desktop-eu.yml", "desktop-world.yml", "desktop.yml"]:
        print(f"FAIL: nodes {nodes}")
        return 1
    skel = sorted(os.listdir(os.path.join(cfg, "skel")))
    if skel != ["preseed.cfg.in", "script.sh.in"]:
        print(f"FAIL: skel {skel}")
        return 1
    for f in ("Makefile", "NEWS", "TODO"):
        if not os.path.isfile(os.path.join(cfg, f)):
            print(f"FAIL: missing {f}")
            return 1

    # nodes reference the expected boxer classes
    content = {}
    for n in nodes:
        content[n] = open(os.path.join(cfg, "nodes", n), encoding="utf-8",
                          errors="replace").read()
    if "Task.harden.desktop" not in content["desktop.yml"]:
        print("FAIL: desktop.yml missing Task.harden.desktop")
        return 1
    if "Desktop.locale.EU" not in content["desktop-eu.yml"]:
        print("FAIL: desktop-eu.yml missing Desktop.locale.EU")
        return 1
    if "Desktop.locale" not in content["desktop-world.yml"]:
        print("FAIL: desktop-world.yml missing Desktop.locale")
        return 1

    # recorded binary semantics sanity (counts must be present and coherent)
    bp = meta.get("binary_packages", {})
    if set(bp) != {"parl-data", "parl-desktop", "parl-desktop-world",
                   "parl-desktop-eu", "parl-desktop-strict"}:
        print("FAIL: binary_packages set mismatch")
        return 1
    for name, expect in [("parl-data", (0, 0, 0)),
                         ("parl-desktop", (54, 1, 0)),
                         ("parl-desktop-world", (350, 1, 0)),
                         ("parl-desktop-eu", (125, 1, 0)),
                         ("parl-desktop-strict", (1, 0, 21))]:
        got = (bp[name]["depends"], bp[name]["suggests"], bp[name]["conflicts"])
        if got != expect:
            print(f"FAIL: {name} depends/suggests/conflicts {got} != {expect}")
            return 1

    print("OK: debian-parl metadata verified "
          f"(profiles={len(profiles)}, nodes=3, binary_packages={len(bp)}, "
          "config/Makefile/NEWS/TODO present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
