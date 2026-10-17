#!/usr/bin/env python3
"""Conan recipe for Little CMS 1.19 (Autotools).

Little CMS is an open-source color management engine,
with support for ICC profile creation and conversion.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Lcms1Conan(ConanFile):
    name = "lcms1"
    version = "1.19"
    description = "Little CMS 1.x - ICC color management engine"
    license = "MIT"
    homepage = "https://www.littlecms.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Out-of-tree build: testcms reads 'sRGB Color Space Profile.icm' from CWD,
        # so copy the upstream test data into the build tree before `make check`.
        copy(
            self,
            "*.icm",
            src=os.path.join(self.source_folder, "testbed"),
            dst=os.path.join(self.build_folder, "testbed"),
            keep_path=False,
        )
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lcms"]
        self.cpp_info.set_property("cmake_file_name", "lcms1")
        self.cpp_info.set_property("cmake_target_name", "lcms1::lcms1")
        self.cpp_info.set_property("pkg_config_name", "lcms")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
