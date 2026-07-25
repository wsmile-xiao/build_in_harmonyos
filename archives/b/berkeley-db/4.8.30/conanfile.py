#!/usr/bin/env python3
"""Conan recipe for Berkeley DB 4.8.30."""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BerkeleyDbConan(ConanFile):
    name = "berkeley-db"
    version = "4.8.30"
    description = "Berkeley DB embedded database"
    license = "Sleepycat"
    url = "https://github.com/berkeleydb/berkeley-db"
    package_type = "library"
    exports_sources = "conandata.yml", "patches/*"  # export_sources for G1
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        get(self, **src, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        if self.settings.os == "OHOS":
            # HarmonyOS has no `cc` symlink; Autotools needs explicit CC/CXX.
            tc.make_args.append("CC=clang")
            tc.make_args.append("CXX=clang++")
            # Berkeley DB 4.8 ships a 2009 config.guess/sub without an OHOS triple.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.extend(["--disable-static", "--enable-shared"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure(build_script_folder="dist")
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["db"]
