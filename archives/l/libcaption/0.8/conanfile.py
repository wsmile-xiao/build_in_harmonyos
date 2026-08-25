#!/usr/bin/env python3
"""Conan recipe for libcaption 0.8 (CEA-608 / CEA-708 closed-caption codec).

Upstream: szatmary/libcaption tag v0.8 (MIT).
Build system: CMake (in-tree). Pure C, no external runtime dependencies.
re2c is optional (ENABLE_RE2C, default OFF) — the committed
src/eia608_from_utf8.c.cached is used verbatim, so re2c is not required.

OHOS adaptation is minimal:
  - bump cmake_minimum_required 2.8 -> 3.10 (CMake 4.x dropped <3.5
    compatibility; NixOS carries the identical patch).
No source-level platform changes are needed: the library is pure C with no
OS-specific calls (no uname/config.guess/config.sub, no pthread, no dlopen).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibcaptionConan(ConanFile):
    name = "libcaption"
    version = "0.8"
    description = "Free open-source CEA-608 / CEA-708 closed-caption encoder/decoder"
    license = "MIT"
    homepage = "https://github.com/szatmary/libcaption"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # re2c not required: use committed cached eia608_from_utf8.c
        tc.variables["ENABLE_RE2C"] = "OFF"
        # Build the library only. Examples are CLI tools (flv2srt, ts2srt, ...)
        # registered in examples/CMakeLists.txt — not part of the library
        # package, and they are not formal tests. Keep the package minimal.
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official test: only `test_wrap` is registered (un-commented)
        # in the top-level CMakeLists.txt. eia608_test and test_sei are
        # commented out upstream and are therefore NOT formal tests.
        # test_wrap exercises utf8 line-wrapping with deterministic input and
        # exits 0 on success (no media sample dependency).
        #
        # The upstream CMakeLists.txt never calls enable_testing()/add_test(),
        # so there is no CTest `test` target — run the built binary directly.
        # In shared mode the just-built libcaption.so lives in the build folder,
        # which the dynamic linker does not search by default; expose it.
        test_wrap = os.path.join(self.build_folder, "test_wrap")
        if self.options.shared and self.settings.os in ("Linux", "OHOS", "Macos", "FreeBSD"):
            self.run(
                f'LD_LIBRARY_PATH="{self.build_folder}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}" "{test_wrap}"'
            )
        else:
            self.run(f'"{test_wrap}"')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["caption"]
        self.cpp_info.set_property("cmake_file_name", "caption")
        self.cpp_info.set_property("cmake_target_name", "caption::caption")
        self.cpp_info.set_property("pkg_config_name", "caption")
