#!/usr/bin/env python3
"""Exploratory Conan build probe for Xorg Server 21.1.16 on OpenHarmony.

This is intentionally not publication-ready: it verifies whether the smallest
headless X server configuration can configure and compile on the device.
"""

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class XorgServerConan(ConanFile):
    name = "xorg-server"
    version = "21.1.16"
    description = "X.Org X server"
    license = "MIT"
    homepage = "https://www.x.org/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("pixman/0.46.4.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["xorg"] = "disabled"
        tc.project_options["xwayland"] = "disabled"
        tc.project_options["xvfb"] = "enabled"
        tc.project_options["xephyr"] = "disabled"
        tc.project_options["xnest"] = "disabled"
        tc.project_options["xwin"] = "disabled"
        tc.project_options["xquartz"] = "disabled"
        tc.project_options["glamor"] = "disabled"
        tc.project_options["dri3"] = "disabled"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
