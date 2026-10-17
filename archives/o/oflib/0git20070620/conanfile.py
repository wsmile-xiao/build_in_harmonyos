#!/usr/bin/env python3
"""Conan recipe for oflib 0git20070620."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class OflibConan(ConanFile):
    name = "oflib"
    version = "0git20070620"
    description = "Userspace Open Firmware device-tree access library"
    license = "GPL-2.0-or-later"
    homepage = "http://git.sipsolutions.net/?p=of-lib.git"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "oflib is packaged for HarmonyOS PC AArch64"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        output = os.path.join(self.build_folder, "libofapi.so.0.0.0")
        sources = [
            os.path.join(self.source_folder, "lib", name)
            for name in ("of_externals.c", "of_internals.c", "of_standard.c")
        ]
        flags = ["-fPIC", "-D_REENTRANT", "-Wall"]
        if str(self.settings.build_type) == "Release":
            flags.extend(["-O2", "-DNDEBUG"])
        command = [
            cc,
            *flags,
            "-shared",
            "-Wl,-soname,libofapi.so.0",
            *sources,
            "-o",
            output,
        ]
        self.run(" ".join(shlex.quote(str(arg)) for arg in command))

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        include_dir = os.path.join(self.package_folder, "include", "ofapi")
        copy(self, "*.h", src=os.path.join(self.source_folder, "lib"), dst=include_dir)
        copy(self, "libofapi.so.0.0.0", src=self.build_folder, dst=lib_dir)

        real_library = os.path.join(lib_dir, "libofapi.so.0.0.0")
        for alias in ("libofapi.so.0", "libofapi.so"):
            shutil.copy2(real_library, os.path.join(lib_dir, alias))

    def package_info(self):
        self.cpp_info.libs = ["ofapi"]
        self.cpp_info.set_property("cmake_file_name", "oflib")
        self.cpp_info.set_property("cmake_target_name", "oflib::oflib")
        self.cpp_info.set_property("pkg_config_name", "ofapi")
