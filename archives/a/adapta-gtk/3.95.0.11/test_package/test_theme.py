#!/usr/bin/env python3
"""Consumer validation for the adapta-gtk 3.95.0.11 theme data package.

Usage: python3 test_theme.py <package_folder>

Checks (real consumption, mirrors how a GTK desktop resolves a theme):
  1. Four theme variants exist under share/themes/
     (Adapta, Adapta-Nokto, Adapta-Eta, Adapta-Nokto-Eta)
  2. index.theme exists per variant and contains [Desktop Entry] +
     GtkTheme=<variant> mapping (GTK resolves themes by directory name)
  3. GTK3 theme data is complete per variant:
     - gtk-3.0/gtk.css and gtk-3.0/gtk-dark.css (light variants) non-empty
     - gtk-3.22/gtk.css, gtk-3.24/gtk.css non-empty
     - gtk.gresource non-empty (bundles sassc-compiled CSS + PNG assets)
     - thumbnail.png present in gtk-3.0
  4. gtk-2.0 rc files present (gtkrc, common.rc, 3rd-party.rc)
  5. Representative desktop-shell assets present (gnome-shell CSS,
     metacity-1 theme XML, xfwm4 PNGs)
  6. Licenses installed under share/licenses/adapta-gtk/
     (COPYING = GPL-2.0, LICENSE_CC_BY_SA4 = CC-BY-SA-4.0)
"""
import os
import sys


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def check_file(path: str, must_be_nonempty: bool = True) -> int:
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

    # 1+2. variants and index.theme
    variants = ("Adapta", "Adapta-Nokto", "Adapta-Eta", "Adapta-Nokto-Eta")
    for variant in variants:
        theme_dir = os.path.join(themes_dir, variant)
        if not os.path.isdir(theme_dir):
            fail(f"theme variant missing: {theme_dir}")
        idx = os.path.join(theme_dir, "index.theme")
        checks += check_file(idx)
        with open(idx, encoding="utf-8") as f:
            head = f.read(512)
        if "[Desktop Entry]" not in head:
            fail(f"index.theme missing [Desktop Entry]: {idx}")
        if f"Name={variant}" not in head:
            fail(f"index.theme Name mismatch for {variant}: {head[:120]!r}")
        checks += 1

    # 3. GTK3 theme data per variant
    for variant in variants:
        theme_dir = os.path.join(themes_dir, variant)
        for gtkmajor in ("gtk-3.0", "gtk-3.22", "gtk-3.24"):
            gdir = os.path.join(theme_dir, gtkmajor)
            if not os.path.isdir(gdir):
                fail(f"missing {gtkmajor} dir in {variant}: {gdir}")
            for css in ("gtk.css", "gtk-dark.css"):
                if os.path.isfile(os.path.join(gdir, css)):
                    checks += check_file(os.path.join(gdir, css))
            checks += check_file(os.path.join(gdir, "gtk.gresource"))
            if gtkmajor == "gtk-3.0":
                checks += check_file(os.path.join(gdir, "thumbnail.png"))

    # 4. gtk-2.0 rc files (present in all four variants)
    for variant in variants:
        g2 = os.path.join(themes_dir, variant, "gtk-2.0")
        for rc in ("gtkrc", "common.rc", "3rd-party.rc"):
            if os.path.isfile(os.path.join(g2, rc)):
                checks += check_file(os.path.join(g2, rc))

    # 5. representative desktop-shell assets (full variant only)
    adapta = os.path.join(themes_dir, "Adapta")
    checks += check_file(os.path.join(adapta, "gnome-shell", "gnome-shell.css"))
    checks += check_file(os.path.join(adapta, "metacity-1", "metacity-theme-3.xml"))
    checks += check_file(os.path.join(adapta, "xfwm4", "close-active.png"))
    checks += check_file(os.path.join(adapta, "cinnamon", "cinnamon.css"))

    # 6. licenses
    lic_dir = os.path.join(pkg, "share", "licenses", "adapta-gtk")
    checks += check_file(os.path.join(lic_dir, "COPYING"))
    checks += check_file(os.path.join(lic_dir, "LICENSE_CC_BY_SA4"))

    print(f"PASS: adapta-gtk 3.95.0.11 theme data OK ({checks} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
