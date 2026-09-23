#!/usr/bin/env python3
"""debianbuttons 2.3 — packaged-artifact validation (test_package body).

Validates the authentic webextension artifact shipped by the recipe: the
source tree and the build() produced icedeb.xpi (byte-identical entries to
the packaged sources), the manifest.json metadata contract, popup resource
closure, and the absence of bin/ELF artifacts. Exit code != 0 on any failure
so the Conan/CI test step fails loudly.

Usage: python3 test_debianbuttons.py <package_folder>
"""
import json
import os
import re
import sys
import zipfile

FAILURES = []
CHECKS = 0


def check(cond, label, detail=""):
    global CHECKS
    CHECKS += 1
    if cond:
        print("  [PASS] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def main():
    if len(sys.argv) != 2:
        print("usage: %s <package_folder>" % sys.argv[0])
        return 2

    pkg = sys.argv[1]
    ext = os.path.join(pkg, "share", "debianbuttons")

    # ── 1. 打包布局（诚实性：源码树 + icedeb.xpi，无 bin/ 无 ELF）──
    print("\n--- [1] packaged layout ---")
    check(os.path.isdir(ext), "share/debianbuttons/ exists", ext)
    for f in ("manifest.json", "icedeb.js", "icedeb-content.js",
              "icedeb.html", "icedeb.css", "README", "Changes", "TODO"):
        check(os.path.isfile(os.path.join(ext, f)), "packaged: %s" % f)
    xpi = os.path.join(ext, "icedeb.xpi")
    check(os.path.isfile(xpi) and os.path.getsize(xpi) > 0,
          "packaged: icedeb.xpi (built artifact, non-empty)")
    check(not os.path.isdir(os.path.join(pkg, "bin")),
          "no bin/ directory (L0k/R38: not a CLI tool)")
    bin_dir = os.path.join(pkg, "bin")
    if os.path.isdir(bin_dir):
        bad = [n for n in os.listdir(bin_dir) if n not in (".", "..")]
        check(not bad, "no bin/ entries", str(bad[:5]))
    elf = [n for n in os.listdir(pkg) if n.endswith((".so", ".a", ".o"))]
    check(not elf, "no .so/.a/.o library artifacts (R26 isolation N/A)", str(elf[:5]))

    # ── 2. manifest.json 元数据契约 ──
    print("\n--- [2] manifest.json contract ---")
    mpath = os.path.join(ext, "manifest.json")
    try:
        with open(mpath, encoding="utf-8") as fh:
            manifest = json.load(fh)
        check(isinstance(manifest, dict), "manifest.json parses as JSON")
    except Exception as e:
        manifest = {}
        check(False, "manifest.json parses as JSON", str(e))
    check(manifest.get("manifest_version") == 2, "manifest_version == 2",
          repr(manifest.get("manifest_version")))
    check(manifest.get("version") == "2.3", "version == 2.3", repr(manifest.get("version")))
    check(manifest.get("name") == "Debian queries", "name == 'Debian queries'",
          repr(manifest.get("name")))
    gecko = manifest.get("applications", {}).get("gecko", {})
    check(gecko.get("id") == "{8fb11c5b-84eb-4da0-9128-292eacce2dcb}",
          "gecko extension id present", repr(gecko.get("id")))
    perms = set(manifest.get("permissions", []))
    check(perms == {"activeTab", "storage", "clipboardRead"},
          "permissions == {activeTab, storage, clipboardRead}", repr(sorted(perms)))

    # ── 3. manifest 引用资源闭包 ──
    print("\n--- [3] referenced resource closure ---")
    refs = []
    for v in (manifest.get("icons") or {}).values():
        refs.append(v)
    ba = manifest.get("browser_action") or {}
    if ba.get("default_icon"):
        refs.append(ba["default_icon"])
    if ba.get("default_popup"):
        refs.append(ba["default_popup"])
    for ti in ba.get("theme_icons") or []:
        refs += [ti.get("light"), ti.get("dark")]
    missing = sorted({r for r in refs if r and not os.path.isfile(os.path.join(ext, r))})
    check(not missing, "all manifest-referenced resources exist in package",
          str(missing[:5]))
    # 实际引用 4 个唯一资源：icons/openlogo-nd.svg、icedeb-addon-dark.svg、
    # icedeb-addon-light.svg + browser_action.default_popup(icedeb.html)
    #（theme_icons 16/32 两套复用同一对 light/dark）
    check(len(set(r for r in refs if r)) == 4,
          "manifest references exactly 4 unique resources",
          "refs=%d" % len(set(r for r in refs if r)))

    # ── 4. icedeb.xpi 归档完整性 + 与打包源码逐条目字节一致 ──
    print("\n--- [4] icedeb.xpi integrity ---")
    expected = [
        "README", "TODO", "Changes", "manifest.json",
        "icedeb.js", "icedeb.css", "icedeb.html", "icedeb-content.js",
        "res/icon.xcf",
        "icons/openlogo-nd.svg",
        "icons/icedeb-addon-light.svg", "icons/icedeb-addon-dark.svg",
    ]
    try:
        with zipfile.ZipFile(xpi) as zf:
            names = sorted(zf.namelist())
            check(names == sorted(expected), "xpi entries == upstream Makefile ALL_FILES",
                  "got %d want %d" % (len(names), len(expected)))
            bad = [n for n in names if n.startswith("/") or ".." in n]
            check(not bad, "no path traversal / absolute entries in xpi", str(bad[:5]))
            for rel in ("manifest.json", "icedeb.js", "icedeb-content.js",
                        "icedeb.html", "icedeb.css"):
                on_disk = open(os.path.join(ext, rel), "rb").read()
                in_xpi = zf.read(rel)
                check(in_xpi == on_disk,
                      "xpi %s byte-identical to packaged source" % rel,
                      "len %d vs %d" % (len(in_xpi), len(on_disk)))
    except Exception as e:
        check(False, "icedeb.xpi is a valid zip archive", str(e))

    # ── 5. popup HTML 引用闭包 + JS 源码可装载标记 ──
    print("\n--- [5] popup references & JS markers ---")
    try:
        with open(os.path.join(ext, "icedeb.html"), encoding="utf-8") as fh:
            html = fh.read()
        local_refs = [r for r in re.findall(r'(?:src|href)="([^"]+)"', html)
                      if not r.startswith(("#", "http", "data:", "about:"))]
        missing_html = [r for r in local_refs if not os.path.isfile(os.path.join(ext, r))]
        check(not missing_html, "icedeb.html local refs exist in package", str(missing_html[:5]))
    except Exception as e:
        check(False, "icedeb.html readable", str(e))
    try:
        with open(os.path.join(ext, "icedeb.js"), encoding="utf-8") as fh:
            js = fh.read()
        check("link_clicked" in js and "check_likely_inputs" in js,
              "icedeb.js contains core functions (link_clicked/check_likely_inputs)")
        with open(os.path.join(ext, "icedeb-content.js"), encoding="utf-8") as fh:
            content_js = fh.read()
        check("onMessage" in content_js, "icedeb-content.js registers onMessage listener")
    except Exception as e:
        check(False, "JS sources readable", str(e))

    # ── 汇总 ──
    rate = 100.0 * (CHECKS - len(FAILURES)) / CHECKS if CHECKS else 0.0
    print("\n================ 汇总 ================")
    print("用例数 N      : %d" % CHECKS)
    print("通过          : %d" % (CHECKS - len(FAILURES)))
    print("失败          : %d" % len(FAILURES))
    print("通过率        : %.2f%%" % rate)
    if FAILURES:
        print("\n失败明细：")
        for f in FAILURES:
            print(" - " + f)
        return 1
    print("==> ALL PASSED (%.1f%%)" % rate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
