#!/usr/bin/env python3
"""Conan recipe for libhdhomerun — SiliconDust HDHomeRun protocol library."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibhdhomerunConan(ConanFile):
    name = "libhdhomerun"
    version = "20260313"
    description = "SiliconDust HDHomeRun protocol library for controlling HDHomeRun TV tuners"
    license = "LGPL-2.1"
    homepage = "https://www.silicondust.com"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, filename="src.tar.gz")

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c", "clang")

        # OS=Linux: HarmonyOS returns "HarmonyOS" from uname -s, but the Makefile
        # needs "Linux" to select netlink interface detection and add -lrt
        # Use -C to run in source folder where the Makefile is
        if self.options.shared:
            self.run(f"make -C {self.source_folder} OS=Linux CC={cc} -j1")
        else:
            # Build static: compile sources to .o then archive
            import glob
            src_dir = self.source_folder
            srcs = " ".join(sorted(glob.glob(os.path.join(src_dir, "hdhomerun_*.c"))))
            self.run(f"{cc} -c -fPIC -O2 -I{src_dir} {srcs}")
            ar = comp_execs.get("ar", "llvm-ar")
            self.run(f"{ar} rcs libhdhomerun.a *.o")

    def package(self):
        # Copy all headers
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # Copy library
        if self.options.shared:
            copy(self, "libhdhomerun.so", self.source_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libhdhomerun.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Copy hdhomerun_config binary (CLI tool for controlling HDHomeRun devices)
        copy(self, "hdhomerun_config", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["hdhomerun"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "rt"]
