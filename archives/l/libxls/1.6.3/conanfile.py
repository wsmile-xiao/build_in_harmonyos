#!/usr/bin/env python3
"""Conan recipe for libxls 1.6.3 on HarmonyOS PC."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibxlsConan(ConanFile):
    name = "libxls"
    version = "1.6.3"
    description = "C library for reading legacy Excel .xls files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/libxls/libxls"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("excel", "xls", "spreadsheet", "parser")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libxls is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
            "--disable-dependency-tracking",
        ])
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

        fixture = os.path.join(self.source_folder, "test", "files", "test2.xls")
        self.run(
            f'"{os.path.join(self.build_folder, "test2_libxls")}" "{fixture}"',
            env="conanrun",
        )
        self.run(
            f'"{os.path.join(self.build_folder, "test_cpp")}" "{fixture}"',
            env="conanrun",
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = ["xlsreader"]
        self.cpp_info.set_property("cmake_file_name", "libxls")
        self.cpp_info.set_property("cmake_target_name", "libxls::libxls")
        self.cpp_info.set_property("pkg_config_name", "libxls")
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
