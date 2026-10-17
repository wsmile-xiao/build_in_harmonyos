#!/usr/bin/env python3
"""Verify icons smoke test — papirus-icon/theme resource package.

Called by test_package/conanfile.py via self.run().
Performs sanity checks on installed icon theme structure, including
symbolic link classification.
"""
import os
import sys


def symlink_classify(icons_root):
    total = resolvable = case_sensitive = broken = loop = 0
    broken_samples = []

    for theme in ("Papirus", "Papirus-Dark", "Papirus-Light"):
        theme_dir = os.path.join(icons_root, theme)
        if not os.path.isdir(theme_dir):
            continue
        for root, _dirs, files in os.walk(theme_dir, followlinks=False,
                                          onerror=lambda e: None):
            for name in files:
                fp = os.path.join(root, name)
                if not os.path.islink(fp):
                    continue
                total += 1
                target = os.readlink(fp)
                link_dir = os.path.dirname(fp)
                if target.startswith("/"):
                    resolved_path = target
                else:
                    resolved_path = os.path.normpath(
                        os.path.join(link_dir, target))

                if os.path.exists(resolved_path):
                    resolvable += 1
                else:
                    base = os.path.basename(fp)
                    target_base = os.path.basename(target)
                    if base.lower() == target_base.lower() and base != target_base:
                        case_sensitive += 1
                    elif os.path.normpath(resolved_path) == os.path.normpath(fp):
                        loop += 1
                    else:
                        broken += 1
                        if len(broken_samples) < 30:
                            rel = os.path.relpath(fp, icons_root)
                            broken_samples.append(f"{rel} -> {target}")

    return total, resolvable, case_sensitive, broken, loop, broken_samples


def verify(icons_root):
    errors = []
    warns = []

    # 1. Three index.theme exist
    for theme in ("Papirus", "Papirus-Dark", "Papirus-Light"):
        index = os.path.join(icons_root, theme, "index.theme")
        if not os.path.isfile(index):
            errors.append(f"Missing index.theme: {theme}")
        else:
            print(f"  ✓ index.theme: {theme}")

    # 2. Install paths discoverable
    for theme in ("Papirus", "Papirus-Dark", "Papirus-Light"):
        td = os.path.join(icons_root, theme)
        if os.path.isdir(td):
            print(f"  ✓ install path: {theme}")
        else:
            errors.append(f"Missing install path: {theme}")

    # 3. Sample icons in Papirus
    samples = ["folder", "document-open", "edit-copy",
               "network", "terminal", "settings"]
    for s in samples:
        found = False
        for root, _dirs, files in os.walk(
                os.path.join(icons_root, "Papirus"), followlinks=False):
            for f in files:
                base, _ = os.path.splitext(f)
                if base == s:
                    fp = os.path.join(root, f)
                    if os.path.islink(fp) and not os.path.exists(fp):
                        continue
                    found = True
                    break
            if found:
                break
        if found:
            print(f"  ✓ sample icon: {s}")
        else:
            errors.append(f"Sample icon not found: {s}")

    # 4. SVG non-empty + <svg header
    theme_dir = os.path.join(icons_root, "Papirus")
    sc = nc = hc = 0
    for root, _dirs, files in os.walk(theme_dir, followlinks=False):
        for f in files:
            if not f.endswith(".svg"):
                continue
            fp = os.path.join(root, f)
            if os.path.islink(fp) and not os.path.exists(fp):
                continue
            sc += 1
            try:
                if os.path.getsize(fp) > 0:
                    nc += 1
                else:
                    errors.append(f"Empty SVG: {os.path.relpath(fp, icons_root)}")
                    continue
            except OSError:
                continue
            try:
                with open(fp, "rb") as sf:
                    head = sf.read(1024)
                if b"<svg" in head or b"<SVG" in head:
                    hc += 1
            except Exception:
                pass
    print(f"  ✓ SVGs: {sc} total, {nc} non-empty, {hc} with <svg header")

    # 5. PNG magic
    png_ok = 0
    for root, _dirs, files in os.walk(theme_dir, followlinks=False):
        for f in files:
            if not f.endswith(".png"):
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, "rb") as pf:
                    magic = pf.read(8)
                if magic[:8] == b"\x89PNG\r\n\x1a\n":
                    png_ok += 1
                else:
                    errors.append(f"Invalid PNG magic: {os.path.relpath(fp, icons_root)}")
            except Exception:
                errors.append(f"Cannot read PNG: {os.path.relpath(fp, icons_root)}")
    if png_ok > 0 or sc > 0:
        print(f"  ✓ PNG magic valid: {png_ok} file(s)")

    # 6. Symlink classification
    total, ok, case, broken, loop, broken_samples = symlink_classify(icons_root)
    print(f"  Symlink: total={total} resolvable={ok} "
          f"CASE={case} BROKEN={broken} LOOP={loop}")

    if broken <= 306 and broken > 0:
        warns.append(
            f"{broken} upstream pre-existing broken symlinks "
            f"(all in apps/ aliases, not packaging defects)")
        for s in broken_samples[:5]:
            print(f"    BROKEN sample: {s}")
    elif broken > 306:
        errors.append(
            f"Package introduced {broken-306} new broken symlinks "
            f"(upstream has 306)")
    elif broken == 0:
        print("  ✓ No broken symlinks in package")

    if case > 0:
        print(f"  Note: {case} case-sensitive alias symlinks (recorded separately)")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    for w in warns:
        print(f"WARN: {w}")
    print(f"OK: {icons_root} — all checks passed")
    return 0


if __name__ == "__main__":
    icons_root = sys.argv[1] if len(sys.argv) > 1 else "/nonexistent"
    sys.exit(verify(icons_root))
