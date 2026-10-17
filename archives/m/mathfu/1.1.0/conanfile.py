#!/usr/bin/env python3
"""Conan recipe for mathfu 1.1.0, Google's header-only C++ math library.

The library consists of templates only (vectors, matrices, quaternions,
rects, GLSL-style typedefs); the package ships the headers plus the
Apache-2.0 license.  The three upstream Google Test suites are compiled
and executed during conan create so the header templates are validated on
the target platform.
"""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MathfuConan(ConanFile):
    name = "mathfu"
    version = "1.1.0"
    description = (
        "Google's C++ math library for games and graphics: templated "
        "vectors, matrices, quaternions and rects (header-only)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/google/mathfu"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def build_requirements(self):
        # googletest is only used to compile the upstream unit tests during
        # conan create; the library itself has zero dependencies.
        self.tool_requires("googletest/1.12.1")

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.cppstd:
            from conan.tools.build import check_min_cppstd

            check_min_cppstd(self, "11")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The v1.1.0 release tarball ships the dependencies/ git submodules
        # (fplutil, googletest, vectorial) as empty directories, so the
        # upstream CMake build (cmake/find_fplutil.cmake) cannot configure.
        # The three upstream test translation units are therefore compiled
        # directly with the toolchain compiler, mirroring the flags the
        # upstream CMake would use:
        #   * MATHFU_COMPILE_WITHOUT_SIMD_SUPPORT selects the upstream
        #     "no_simd" test variant (unit_tests/*/no_simd).  The vectorial
        #     NEON/SSE backend headers are not part of the release tarball,
        #     and the OHOS clang only defines __ARM_NEON (without trailing
        #     underscores) so upstream's __ARM_NEON__ detection never fires
        #     either; the macro makes the scalar contract explicit.
        #   * -ffp-contract=off disables FMA contraction: clang's default
        #     contraction on aarch64 changes the rounding path of the
        #     determinant computation and breaks the exact-cancellation
        #     boundary cases MatrixTests.InverseNonInvertible_{float,double}_3
        #     and QuaternionTests.Inverse (see notes.md and the knowledge
        #     draft DRAFT-mathfu-1.1.0-aarch64-fma-contraction-determinant).
        #   * -Wno-deprecated-copy(-with-user-provided-copy) keeps the
        #     2014-era user-provided copy constructors warning-free under
        #     clang 15 -Werror (upstream builds -Wall -Wextra -Werror).
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        compiler = compiler_executables.get("cpp") or "c++"
        gtest = self.dependencies.build["googletest"]
        gtest_include = os.path.join(gtest.package_folder, "include")
        gtest_lib = os.path.join(gtest.package_folder, "lib", "libgtest.a")
        include_dir = os.path.join(self.source_folder, "include")
        unit_tests_dir = os.path.join(self.source_folder, "unit_tests")

        base_flags = [
            "-std=c++11",
            "-O2",
            "-ffp-contract=off",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wno-long-long",
            "-Wno-variadic-macros",
            "-Wno-deprecated-copy-with-user-provided-copy",
            "-Wno-deprecated-copy",
            "-DMATHFU_COMPILE_WITHOUT_SIMD_SUPPORT",
        ]
        # The OHOS SDK libc++.so is a linker script (INPUT(-lc++_shared));
        # statically linked test binaries run natively on the device.
        link_flags = ["-static"] if self.settings.os == "OHOS" else []

        suites = (
            ("vector_test", "vector_test"),
            ("matrix_test", "matrix_test"),
            ("quaternion_test", "quaternion_test"),
        )
        for binary_name, suite_dir in suites:
            binary = os.path.join(self.build_folder, binary_name)
            command = " ".join(
                [shlex.quote(str(compiler))]
                + base_flags
                + [
                    "-I",
                    shlex.quote(include_dir),
                    "-I",
                    shlex.quote(unit_tests_dir),
                    "-isystem",
                    shlex.quote(gtest_include),
                    shlex.quote(
                        os.path.join(
                            unit_tests_dir, suite_dir, binary_name + ".cpp"
                        )
                    ),
                    shlex.quote(gtest_lib),
                    "-lpthread",
                ]
                + link_flags
                + ["-o", shlex.quote(binary)]
            )
            self.run(command)
            self.run('"{}"'.format(binary))

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # aarch64 + vectorial headers not in the release tarball: expose the
        # compilable configuration to consumers (see notes.md).
        self.cpp_info.defines = ["MATHFU_COMPILE_WITHOUT_SIMD_SUPPORT"]
        self.cpp_info.set_property("cmake_file_name", "mathfu")
        self.cpp_info.set_property("cmake_target_name", "mathfu::mathfu")
