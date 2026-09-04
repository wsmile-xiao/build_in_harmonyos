#!/usr/bin/env python3
"""Conan recipe for oatpp 1.3.1 — CMake project (HarmonyOS PC aarch64).

- Builds the official release tarball from github.com/oatpp/oatpp (tag 1.3.1).
- Static library by default (BUILD_SHARED_LIBS=OFF), matching upstream defaults
  and R26 system-name isolation.
- OHOS musl sysroot lacks pthread_setaffinity_np -> OATPP_COMPAT_BUILD_NO_SET_AFFINITY=ON
  (upstream option, see CMakeLists.txt:44/86; no source patch needed).
- OHOS has no libatomic.a -> OATPP_LINK_ATOMIC=OFF (aarch64 atomics are compiler
  builtins on clang; upstream option CMakeLists.txt:21).
- Tests are built (OATPP_BUILD_TESTS=ON) and exercised via the upstream
  oatppAllTests target during adaptation; test_package performs a real HTTP
  loopback smoke test (see test_package/test_oatpp.cpp).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OatppConan(ConanFile):
    name = "oatpp"
    version = "1.3.1"
    description = "oatpp 1.3.1 — lightweight C++ web framework"
    license = "Apache-2.0"
    homepage = "https://github.com/oatpp/oatpp"
    url = "https://github.com/oatpp/oatpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["OATPP_INSTALL"] = "ON"
        tc.variables["OATPP_BUILD_TESTS"] = "ON"
        # OHOS musl: no pthread_setaffinity_np / no libatomic.a
        tc.variables["OATPP_COMPAT_BUILD_NO_SET_AFFINITY"] = "ON"
        tc.variables["OATPP_LINK_ATOMIC"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake 4.x removed compatibility with cmake_minimum_required < 3.5;
        # oatpp 1.3.1 declares 3.5, so pass the policy minimum as a configure-time
        # cache variable (command line) — toolchain variables are read too late.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # oatpp installs into version-suffixed subdirs (module-install.cmake):
        #   ${includedir}/oatpp-1.3.0/oatpp/oatpp/..., ${libdir}/oatpp-1.3.0/liboatpp.a
        # Consumer include root must reach the inner "${OATPP_MODULE_NAME}" dir,
        # so `#include "oatpp/core/..."` resolves correctly.
        self.cpp_info.libdirs = ["lib/oatpp-1.3.0"]
        self.cpp_info.includedirs = ["include/oatpp-1.3.0/oatpp"]
        self.cpp_info.libs = ["oatpp"]
        self.cpp_info.set_property("cmake_file_name", "oatpp")
        self.cpp_info.set_property("cmake_target_name", "oatpp::oatpp")
