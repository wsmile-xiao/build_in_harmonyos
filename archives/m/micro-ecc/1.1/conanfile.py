#!/usr/bin/env python3
"""Conan recipe — micro-ecc 1.1 (custom clang build).

Small and fast ECDH/ECDSA implementation for 8/32/64-bit processors.
Upstream ships C sources without a build system (copy-into-project style);
compiled directly with clang and archived with llvm-ar. Static by default.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MicroEccConan(ConanFile):
    name = "micro-ecc"
    version = "1.1"
    description = "A small and fast ECDH and ECDSA implementation"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kmackay/micro-ecc"
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
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        cflags = "-fPIC -O2"
        if self.options.shared:
            self.run(
                f"{cc} {cflags} -I. -c uECC.c -o uECC.o",
                cwd=self.source_folder,
            )
            self.run(
                f"{cc} -shared uECC.o -o libuecc.so",
                cwd=self.source_folder,
            )
        else:
            self.run(
                f"{cc} {cflags} -I. -c uECC.c -o uECC.o",
                cwd=self.source_folder,
            )
            self.run(f"{ar} rcs libuecc.a uECC.o", cwd=self.source_folder)

    def package(self):
        copy(self, "uECC.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "uECC_vli.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "types.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        for inc in ("platform-specific.inc", "curve-specific.inc",
                    "asm_arm.inc", "asm_arm_mult_square.inc",
                    "asm_arm_mult_square_umaal.inc", "asm_avr.inc",
                    "asm_avr_mult_square.inc"):
            copy(self, inc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))
        copy(self, "libuecc.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libuecc.so", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["uecc"]