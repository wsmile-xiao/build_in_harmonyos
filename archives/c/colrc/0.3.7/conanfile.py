#!/usr/bin/env python3
"""Conan recipe for colrc — C library for terminal colors/formatting.

colrc is a command-line tool and C library for terminal color formatting.
This recipe packages the colrc binary and header files.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class ColrcConan(ConanFile):
    name = "colrc"
    version = "0.3.7"
    description = "C library for terminal colors and color formatting"
    license = "MIT"
    homepage = "https://github.com/welbornprod/colrc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: obtain the compiler from Conan's toolchain configuration.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        self.run(
            f"make release CC={cc} CFLAGS='-fPIC -O2 -std=c11' -j1",
            cwd=self.source_folder,
        )
        test_folder = os.path.join(self.source_folder, "test")
        for filename in os.listdir(test_folder):
            if filename.endswith(".o") or filename == "test_colrc":
                os.remove(os.path.join(test_folder, filename))
        self.run(
            f"make -C test test_colrc CC={cc} "
            "CFLAGS='-fPIC -O2 -std=gnu11 -D_GNU_SOURCE -DCOLR_TEST' -j1",
            cwd=self.source_folder,
        )
        self.run("./test/test_colrc --quiet", cwd=self.source_folder)
        self.run(
            f"{cc} -shared -o libcolr.so colr.o colr.controls.o -lm",
            cwd=self.source_folder,
        )

    def package(self):
        # Manual install since makefile install is interactive.
        copy(self, "colrc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libcolr.so", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "*.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            excludes="test/*",
        )
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["colr"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
