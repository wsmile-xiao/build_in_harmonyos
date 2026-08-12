#!/usr/bin/env python3
"""Conan test_package — adw-gtk 6.5 (theme data consumer validation).

Theme data package: no libraries or binaries to link/run. The test()
method runs a Python consumer check (test_theme.py) that verifies the
installed theme data is complete and usable by a GTK3/GTK4 desktop:
  - share/themes/adw-gtk3/index.theme exists (light variant)
  - share/themes/adw-gtk3-dark/index.theme exists (dark variant)
  - gtk-3.0/gtk.css and gtk-3.0/gtk-dark.css exist and are non-empty
  - gtk-4.0/gtk.css, gtk-4.0/gtk-dark.css, gtk-4.0/libadwaita.css and
    gtk-4.0/libadwaita-tweaks.css exist and are non-empty
  - assets/ directory has content (SVG/PNG assets referenced by CSS)
  - index.theme contains GtkTheme=adw-gtk3 / GtkTheme=adw-gtk3-dark
  - LGPL-2.1 LICENSE installed under share/licenses/adw-gtk/
"""
import os

from conan import ConanFile


class AdwGtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["adw-gtk"]
        pkg_folder = dep.package_folder
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_theme.py")
        self.run(f'python3 "{script}" "{pkg_folder}"', env="conanrun")
