#!/usr/bin/env python3
"""Conan recipe for distorm 3.5.2.b — Makefile build system.

diStorm3 is a lightweight x86/AMD64 binary stream disassembler library (pure C,
no dependencies). Upstream provides per-OS Makefiles (make/linux/Makefile);
this recipe compiles src/*.c directly with the Conan-provided compiler (R33)
using the same flags as the upstream Linux Makefile.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DistormConan(ConanFile):
    name = "distorm"
    version = "3.5.2.b"
    description = "Powerful lightweight x86/AMD64 binary stream disassembler library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/gdabah/distorm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # distorm builds in-source (object files next to src/*.c, like upstream)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        # R33: compiler paths come from Conan conf, never from shell env vars.
        # The ohos profile registers tools.build:compiler_executables as a dict.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        return cc, ar, ranlib

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._toolchain()
        # Same flags as upstream make/linux/Makefile
        opt = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        cflags = "-fPIC {} -Wall -DSUPPORT_64BIT_OFFSET -DDISTORM_STATIC -std=c99".format(opt)
        inc = '-I"{}" -I"{}"'.format(os.path.join(self.source_folder, "include"),
                                     os.path.join(self.source_folder, "src"))
        sources = ["decoder.c", "distorm.c", "instructions.c", "insts.c",
                   "mnemonics.c", "operands.c", "prefix.c", "textdefs.c"]
        objects = []
        for src in sources:
            obj = src.replace(".c", ".o")
            self.run('"{cc}" {cflags} {inc} -c "src/{src}" -o "{obj}"'.format(
                cc=cc, cflags=cflags, inc=inc, src=src, obj=obj),
                cwd=self.source_folder)
            objects.append('"{}"'.format(obj))
        if self.options.shared:
            self.run('"{cc}" -shared -o libdistorm3.so {objs}'.format(
                cc=cc, objs=" ".join(objects)),
                cwd=self.source_folder)
        else:
            self.run('"{ar}" rcs libdistorm3.a {objs}'.format(
                ar=ar, objs=" ".join(objects)),
                cwd=self.source_folder)
            self.run('"{ranlib}" libdistorm3.a'.format(ranlib=ranlib),
                     cwd=self.source_folder)

    def package(self):
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "libdistorm3.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libdistorm3.so*", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Upstream library file is libdistorm3.a / libdistorm3.so, keep the name
        self.cpp_info.libs = ["distorm3"]
