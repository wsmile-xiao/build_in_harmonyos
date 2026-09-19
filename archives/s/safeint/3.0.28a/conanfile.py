#!/usr/bin/env python3
"""Conan recipe for SafeInt 3.0.28a, a header-only C/C++ library."""
import os
import platform

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SafeintConan(ConanFile):
    name = "safeint"
    version = "3.0.28a"
    description = "Header-only C/C++ library for checked integer arithmetic"
    license = "MIT"
    homepage = "https://github.com/dcleblanc/SafeInt"
    url = "https://github.com/dcleblanc/SafeInt"
    topics = ("integer", "overflow", "header-only", "safety")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    _clang_targets = (
        "SafeIntTest_clang",
        "SafeIntTest_clang_NoIntrinsic",
        "SafeIntTest_clang_NoInt128",
        "CompileTest_clang",
        "CompileTest_clang14",
        "CompileTest_clang17",
        "CompileTest_clang14_NoEH",
        "CompileTest_clang17_NoEH",
        "CompileTest_clang98",
        "safe_math_test_clang",
        "safe_math_compile_clang",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # The OHOS SDK passes --gcc-toolchain for sysroot discovery.
            # Upstream uses -Werror, so retain the warning without failing.
            flag = "-Wno-error=unused-command-line-argument"
            toolchain.extra_cflags.append(flag)
            toolchain.extra_cxxflags.append(flag)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        targets = " ".join(self._clang_targets)
        self.run(
            'cmake --build "{}" --parallel 2 --target {}'.format(
                self.build_folder, targets
            ),
            env="conanbuild",
        )
        if platform.system() == "HarmonyOS":
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error -R "SafeIntTest_clang|safe_math_test_clang"'.format(
                    self.build_folder
                ),
                env="conanbuild",
            )
        else:
            self.output.info(
                "Upstream runtime tests require native HarmonyOS; "
                "all eleven Clang compile targets were built"
            )

    def package(self):
        for header in ("SafeInt.hpp", "safe_math.h", "safe_math_impl.h"):
            copy(self, header, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "safeint")
        self.cpp_info.set_property("cmake_target_name", "safeint::safeint")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
