#!/usr/bin/env python3
"""Conan test_package — adapta-gtk 3.95.0.11 (theme data consumer validation).

Theme data package: no libraries or binaries to link/run. The test()
method runs a Python consumer check (test_theme.py) that verifies the
installed theme data is complete and usable by a GTK desktop:
  - four theme variants installed under share/themes/
    (Adapta, Adapta-Nokto, Adapta-Eta, Adapta-Nokto-Eta)
  - index.theme present and valid for each variant
  - gtk-3.0 / gtk-3.22 / gtk-3.24 CSS and gtk.gresource present,
    non-empty (data compiled upstream with sassc + inkscape)
  - gtk-2.0 rc files and representative PNG/SVG assets present
  - GPL-2.0 (COPYING) and CC-BY-SA-4.0 (LICENSE_CC_BY_SA4) licenses
    installed under share/licenses/adapta-gtk/
"""
import os

from conan import ConanFile


class AdaptaGtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["adapta-gtk"]
        pkg_folder = dep.package_folder
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_theme.py")
        self.run(f'python3 "{script}" "{pkg_folder}"', env="conanrun")
