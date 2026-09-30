"""Conan recipe for the wcalc 2.5 command-line calculator."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WcalcConan(ConanFile):
    name = "wcalc"
    version = "2.5"
    description = "Command-line scientific calculator with arbitrary precision"
    license = "GPL-2.0-or-later"
    homepage = "https://wcalc.sourceforge.net/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-readline",
            f"--with-gmp={self.dependencies['gmp'].package_folder}",
            f"--with-mpfr={self.dependencies['mpfr'].package_folder}",
        ])
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        autotools.make(target="check")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
