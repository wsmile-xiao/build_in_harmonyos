#!/usr/bin/env python3
"""Conan 2.x recipe — Fathom 1.0 (Syzygy tablebase probing library)

Upstream has no library build system (src/apps/Makefile only builds the
CLI), so this recipe injects a minimal CMakeLists.txt that compiles
src/tbprobe.c (a single translation unit which #includes src/tbcore.c)
into the static library `fathom`, using the same flags as upstream's
Makefile: C99 (GNU extensions), -DTB_NO_THREADS -DTB_NO_HW_POP_COUNT.

Two x86-only constructs in src/tbprobe.c are patched in source()
(see comments there). No external dependencies.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    copy,
    get,
    replace_in_file,
)


class FathomConan(ConanFile):
    name = "fathom"
    version = "1.0"
    description = "Stand-alone Syzygy chess tablebase probing library"
    license = "MIT"
    homepage = "https://github.com/basil00/Fathom"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder,
             self.export_sources_folder)

    def validate(self):
        # R32: platform check must accept OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported")

    def configure(self):
        # Pure C89/C99 library: C++ management flags are meaningless
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # Portability patch (R8: keep upstream style, append platform
        # branch, no behavior change on x86). tbprobe.c 1.0 hard-codes two
        # x86-only constructs:
        #
        # 1) An unconditional `#include <x86intrin.h>`. The only thing it
        #    feeds is _mm_popcnt_u64, which is already behind the
        #    TB_NO_HW_POP_COUNT guard — and this recipe defines that macro,
        #    exactly like upstream's own src/apps/Makefile. On
        #    aarch64/ohos clang the header self-errors out
        #    ("This header is only for x86").
        #
        # 2) lsb() uses the x86-only `bsfq` inline asm unconditionally.
        #    Keep the asm branch for x86; every other target uses
        #    __builtin_ctzll, which has identical semantics for the only
        #    inputs lsb() ever receives (non-zero bitboards; callers
        #    always guard with `for (; b; b = poplsb(b))`).
        tbprobe_c = os.path.join(self.source_folder, "src", "tbprobe.c")
        replace_in_file(
            self, tbprobe_c,
            "#include <x86intrin.h>",
            "#if defined(__i386__) || defined(__x86_64__)\n"
            "#include <x86intrin.h>\n"
            "#endif",
        )
        replace_in_file(
            self, tbprobe_c,
            '    __asm__("bsfq %1, %0": "=r"(idx): "rm"(b));',
            "#if defined(__i386__) || defined(__x86_64__)\n"
            '    __asm__("bsfq %1, %0": "=r"(idx): "rm"(b));\n'
            "#else\n"
            "    idx = (size_t)__builtin_ctzll(b);\n"
            "#endif",
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["fathom"]
