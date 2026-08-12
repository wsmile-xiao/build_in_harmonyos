#!/usr/bin/env python3
"""Consumer validation for the adw-gtk 6.5 theme data package.

Usage: python3 test_theme.py <package_folder>

Checks (real consumption, mirrors how a GTK desktop consumes a theme):
  1. index.theme present for both adw-gtk3 (light) and adw-gtk3-dark
  2. index.theme content: [X-GNOME-Metatheme] + GtkTheme=adw-gtk3(-dark)
  3. gtk-3.0 theme CSS present and non-empty (gtk.css, gtk-dark.css)
  4. gtk-4.0 theme CSS present and non-empty (gtk.css, gtk-dark.css,
     libadwaita.css, libadwaita-tweaks.css)
  5. assets/ directory present with SVG/PNG assets (referenced by CSS)
  6. thumbnail present (gtk-3.0/thumbnail.png)
  7. LGPL-2.1 LICENSE installed under share/licenses/adw-gtk/
"""
import os
import sys


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def check_file(path: str, must_be_nonempty: bool = True) -> int:
    """Assert a file exists; optionally assert non-empty content."""
    if not os.path.isfile(path):
        fail(f"file missing: {path}")
    if must_be_nonempty and os.path.getsize(path) == 0:
        fail(f"file is empty: {path}")
    return 1


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: test_theme.py <package_folder>")
        return 1

    pkg = os.path.abspath(sys.argv[1])
    checks = 0

    themes_dir = os.path.join(pkg, "share", "themes")
    for variant in ("adw-gtk3", "adw-gtk3-dark"):
        theme_dir = os.path.join(themes_dir, variant)

        # 1. index.theme
        idx = os.path.join(theme_dir, "index.theme")
        checks += check_file(idx)
        with open(idx, encoding="utf-8") as f:
            head = f.read(512)
        if "[X-GNOME-Metatheme]" not in head:
            fail(f"index.theme lacks [X-GNOME-Metatheme]: {idx}")
        expected_gtk_theme = f"GtkTheme={variant}"
        if expected_gtk_theme not in head:
            fail(f"index.theme lacks {expected_gtk_theme}: {idx}")
        checks += 1
        print(f"  [ok] {variant}/index.theme valid (GtkTheme={variant})")

        # 2. gtk-3.0 CSS
        gtk3 = os.path.join(theme_dir, "gtk-3.0")
        for css in ("gtk.css", "gtk-dark.css"):
            checks += check_file(os.path.join(gtk3, css))
        print(f"  [ok] {variant}/gtk-3.0 CSS present")

        # 3. gtk-4.0 CSS
        gtk4 = os.path.join(theme_dir, "gtk-4.0")
        for css in ("gtk.css", "gtk-dark.css", "libadwaita.css",
                    "libadwaita-tweaks.css"):
            checks += check_file(os.path.join(gtk4, css))
        print(f"  [ok] {variant}/gtk-4.0 CSS present")

        # 4. assets
        assets = os.path.join(gtk3, "assets")
        if not os.path.isdir(assets):
            fail(f"assets dir missing: {assets}")
        asset_files = [f for f in os.listdir(assets)
                       if f.endswith((".png", ".svg"))]
        if not asset_files:
            fail(f"assets dir has no PNG/SVG assets: {assets}")
        checks += 1
        print(f"  [ok] {variant}/gtk-3.0/assets has {len(asset_files)} assets")

        # 5. thumbnail
        checks += check_file(os.path.join(gtk3, "thumbnail.png"))
        print(f"  [ok] {variant}/gtk-3.0/thumbnail.png present")

    # 6. LICENSE
    lic = os.path.join(pkg, "share", "licenses", "adw-gtk", "LICENSE")
    checks += check_file(lic)
    with open(lic, encoding="utf-8", errors="replace") as f:
        head = f.read(512)
    if "GNU LESSER GENERAL PUBLIC LICENSE" not in head:
        fail(f"LICENSE is not LGPL: {lic}")
    checks += 1
    print("  [ok] share/licenses/adw-gtk/LICENSE is LGPL-2.1")

    print(f"ALL CHECKS PASSED ({checks} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
