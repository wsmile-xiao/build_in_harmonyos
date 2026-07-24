#!/usr/bin/env python3
"""Conan recipe — Berkeley SoftFloat 3e (Makefile)."""

import os
from os.path import join

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class SoftfloatConan(ConanFile):
    name = "softfloat"
    version = "3e"
    description = "Berkeley software implementation of IEEE binary floating-point arithmetic"
    license = "BSD-3-Clause"
    homepage = "https://www.jhauser.us/arithmetic/SoftFloat.html"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        build_dir = join(self.build_folder, "softfloat-build")
        source_build_dir = join(self.source_folder, "build", "Linux-ARM-VFPv2-GCC")
        copy(self, "Makefile", source_build_dir, build_dir)
        copy(self, "platform.h", source_build_dir, build_dir)

        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        ar = compiler_executables.get("ar", "llvm-ar")
        debug = str(self.settings.build_type) == "Debug"
        opt = "-O0 -g" if debug else "-O2"
        slow_opt = opt if debug else "-O3"
        inline_level = 0 if debug else 5
        if debug:
            replace_in_file(
                self,
                join(build_dir, "platform.h"),
                "#define SOFTFLOAT_BUILTIN_CLZ 1",
                "/* Use generic CLZ functions when Debug disables inlining. */",
            )
        compile_c = (
            f"{cc} -std=c99 -c -Werror-implicit-function-declaration "
            f"-DSOFTFLOAT_ROUND_ODD -DINLINE_LEVEL={inline_level} -fPIC "
            f"-I. -I\\$(SOURCE_DIR)/\\$(SPECIALIZE_TYPE) -I\\$(SOURCE_DIR)/include {opt} -o \\$@"
        )
        self.run(
            f'make -C "{build_dir}" -j1 '
            f'"SOURCE_DIR={join(self.source_folder, "source")}" '
            "SPECIALIZE_TYPE=ARM-VFPv2 "
            f'"COMPILE_C={compile_c}" "MAKELIB={ar} crs \\$@"'
        )

        testfloat_dir = join(self.build_folder, "testfloat-3e")
        get(
            self,
            url=self.conan_data["test_sources"]["url"],
            sha256=self.conan_data["test_sources"]["sha256"],
            destination=testfloat_dir,
            strip_root=True,
        )
        test_build_dir = join(testfloat_dir, "build", "Linux-ARM-VFPv2-GCC")
        test_compile = (
            f"{cc} -std=c99 -c -Werror-implicit-function-declaration "
            f"\\$(TESTFLOAT_OPTS) -fPIC \\$(C_INCLUDES) {opt} -o \\$@"
        )
        test_slow_compile = test_compile.replace(opt, slow_opt)
        test_args = (
            f'"SOFTFLOAT_INCLUDE_DIR={join(self.source_folder, "source", "include")}" '
            f'"SOFTFLOAT_LIB={join(build_dir, "softfloat.a")}" '
            f'"COMPILE_C={test_compile}" '
            f'"COMPILE_SLOWFLOAT_C={test_slow_compile}" '
            f'"LINK={cc} -o \\$@" "MAKELIB={ar} crs \\$@"'
        )
        self.run(f'make -C "{test_build_dir}" testsoftfloat -j1 {test_args}')
        self.run(
            f'"{join(test_build_dir, "testsoftfloat")}" -seed 1 -level 1 -errorstop -all1 '
            f'> "{join(test_build_dir, "testsoftfloat-all1.log")}"'
        )
        self.run(
            f'"{join(test_build_dir, "testsoftfloat")}" -seed 1 -level 1 -errorstop -all2 '
            f'> "{join(test_build_dir, "testsoftfloat-all2.log")}"'
        )

    def package(self):
        copy(self, "*.h", join(self.source_folder, "source", "include"), join(self.package_folder, "include"))
        copy(self, "softfloat.a", join(self.build_folder, "softfloat-build"), join(self.package_folder, "lib"))
        # Conan/CMake expects lib<name>.a; the Makefile produces softfloat.a without lib prefix
        src = join(self.package_folder, "lib", "softfloat.a")
        dst = join(self.package_folder, "lib", "libsoftfloat.a")
        if os.path.exists(src):
            os.rename(src, dst)

    def package_info(self):
        self.cpp_info.libs = ["softfloat"]
