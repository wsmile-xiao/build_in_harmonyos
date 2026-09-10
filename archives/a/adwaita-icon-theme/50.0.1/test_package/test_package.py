#!/usr/bin/env python3
"""Consumer validation for the adwaita-icon-theme 50.0.1 data-only package.

Usage: python3 test_package.py <package_folder>

Checks (real consumption, mirrors what a desktop/icon-theme consumer does):
  1. index.theme is installed under share/icons/Adwaita/
  2. Adwaita icon directories exist: 16x16, scalable, symbolic, cursors
  3. Representative SVG/PNG files and the folder-open SVG alias exist
  4. Cursor theme is installed: cursors dir + source/alias names exist
     as symlinks or byte-identical regular fallback files
  5. Dataonly pkg-config file adwaita-icon-theme.pc is installed and
     pkg-config resolves it with PKG_CONFIG_PATH set
  6. Licenses are installed under share/licenses/adwaita-icon-theme/
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def find_pkg_config() -> str:
    """Locate a usable pkg-config binary (not always on default PATH)."""
    found = shutil.which("pkg-config")
    if found:
        return found
    found = shutil.which("pkgconf")
    if found:
        return found
    for candidate in (
        "/data/service/hnp/bin/pkg-config",
        "/usr/bin/pkg-config",
        "/usr/local/bin/pkg-config",
        os.path.expanduser("~/usr/local/bin/pkg-config"),
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    win_get_root = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if win_get_root.is_dir():
        for pattern in ("pkg-config.exe", "pkgconf.exe"):
            for candidate in win_get_root.rglob(pattern):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)
    return "pkg-config"


def same_bytes(first: str, second: str) -> bool:
    with open(first, "rb") as lhs, open(second, "rb") as rhs:
        return lhs.read() == rhs.read()


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: test_package.py <package_folder>")
        return 1

    pkg = os.path.abspath(sys.argv[1])
    checks = 0

    # 1. index.theme
    idx = os.path.join(pkg, "share", "icons", "Adwaita", "index.theme")
    if not os.path.isfile(idx):
        fail(f"index.theme missing: {idx}")
    with open(idx, encoding="utf-8") as f:
        head = f.read(512)
    if "[Icon Theme]" not in head or "Name=Adwaita" not in head:
        fail(f"index.theme content unexpected: {head[:120]!r}")
    checks += 1
    print(f"  [ok] index.theme present and valid ({idx})")

    # 2. Icon directories
    adwaita = os.path.join(pkg, "share", "icons", "Adwaita")
    for d in ("16x16", "scalable", "symbolic", "cursors"):
        dd = os.path.join(adwaita, d)
        if not os.path.isdir(dd):
            fail(f"Adwaita/{d} directory missing: {dd}")
        checks += 1
        print(f"  [ok] Adwaita/{d}/ directory present")

    # 3. SVG + PNG representatives
    svg = os.path.join(adwaita, "scalable", "places", "folder.svg")
    if not os.path.isfile(svg):
        fail(f"SVG missing: {svg}")
    checks += 1
    print(f"  [ok] SVG present ({os.path.relpath(svg, pkg)})")

    svg_alias = os.path.join(adwaita, "scalable", "status", "folder-open.svg")
    if not os.path.lexists(svg_alias):
        fail(f"SVG alias missing: {svg_alias}")
    if os.path.islink(svg_alias):
        target = os.readlink(svg_alias)
        if os.path.basename(target) != "folder.svg":
            fail(f"SVG alias target unexpected: {target}")
        alias_desc = f"symlink -> {target}"
    else:
        if not os.path.isfile(svg_alias):
            fail(f"SVG alias is not a file: {svg_alias}")
        if not same_bytes(svg, svg_alias):
            fail("SVG alias fallback differs from scalable/places/folder.svg")
        alias_desc = "regular file fallback"
    checks += 1
    print(f"  [ok] SVG alias folder-open.svg present ({alias_desc})")

    png_16 = os.path.join(adwaita, "16x16")
    pngs = [f for f in os.listdir(png_16)] if os.path.isdir(png_16) else []
    png_files = []
    for sub in pngs:
        subdir = os.path.join(png_16, sub)
        if os.path.isdir(subdir):
            png_files += [os.path.join(subdir, f) for f in os.listdir(subdir) if f.endswith(".png")]
    if not png_files:
        fail("no PNG files under Adwaita/16x16/")
    checks += 1
    print(f"  [ok] PNG files present ({len(png_files)} found, e.g. {os.path.relpath(png_files[0], pkg)})")

    # 4. Cursors + aliases
    cursors = os.path.join(adwaita, "cursors")
    if not os.path.isdir(cursors):
        fail("cursors directory missing")
    cursor_aliases = {
        "default": ("left_ptr",),
        "pointer": ("hand2",),
        "text": ("xterm",),
        "wait": ("watch",),
    }
    for source_name, aliases in cursor_aliases.items():
        source_path = os.path.join(cursors, source_name)
        if not os.path.isfile(source_path):
            fail(f"cursor source missing: {source_path}")
        checks += 1
        print(f"  [ok] cursor source {source_name} present")
        for alias in aliases:
            alias_path = os.path.join(cursors, alias)
            if not os.path.lexists(alias_path):
                fail(f"cursor alias missing: {alias_path}")
            if os.path.islink(alias_path):
                target = os.readlink(alias_path)
                if os.path.basename(target) != source_name:
                    fail(f"cursor alias {alias} target unexpected: {target}")
                alias_desc = f"symlink -> {target}"
            else:
                if not os.path.isfile(alias_path):
                    fail(f"cursor alias is not a file: {alias_path}")
                if not same_bytes(source_path, alias_path):
                    fail(f"cursor alias fallback differs from source: {alias}")
                alias_desc = "regular file fallback"
            checks += 1
            print(f"  [ok] cursor alias {alias} present ({alias_desc})")

    # 5. Dataonly pkg-config file
    pc = os.path.join(pkg, "lib", "pkgconfig", "adwaita-icon-theme.pc")
    if not os.path.isfile(pc):
        fail(f"pkg-config file missing: {pc}")
    with open(pc, encoding="utf-8") as f:
        pc_content = f.read()
    if "Name:" not in pc_content or "Version: 50.0" not in pc_content:
        fail(f"pkg-config file content unexpected: {pc_content[:120]!r}")
    env = dict(os.environ)
    env["PKG_CONFIG_PATH"] = os.path.join(pkg, "lib", "pkgconfig")
    pkg_config = find_pkg_config()
    r = subprocess.run(
        [pkg_config, "--exists", "adwaita-icon-theme"],
        env=env, capture_output=True, text=True,
    )
    if r.returncode != 0:
        fail(f"pkg-config cannot resolve adwaita-icon-theme: {r.stderr.strip()}")
    rv = subprocess.run(
        [pkg_config, "--modversion", "adwaita-icon-theme"],
        env=env, capture_output=True, text=True,
    )
    ver = rv.stdout.strip() if rv.returncode == 0 else ""
    checks += 1
    print(f"  [ok] pkg-config resolves adwaita-icon-theme (version={ver or '50.0'})")

    # 6. Licenses
    lic_dir = os.path.join(pkg, "share", "licenses", "adwaita-icon-theme")
    for lic in ("COPYING", "COPYING_LGPL", "COPYING_CCBYSA3"):
        lp = os.path.join(lic_dir, lic)
        if not os.path.isfile(lp):
            fail(f"license file missing: {lp}")
        checks += 1
        print(f"  [ok] license {lic} present")

    print(f"\nAll {checks} consumer checks passed for adwaita-icon-theme 50.0.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
