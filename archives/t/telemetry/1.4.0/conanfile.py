#!/usr/bin/env python3
"""Conan recipe for telemetry 1.4.0 — CMake (C++20).

telemetry (CESNET) is a library for the collection and processing of telemetry
data. Upstream builds two shared libraries:

  * libtelemetry.so — core telemetry tree (files, directories, aggregation)
  * libappFs.so     — FUSE3 view of the telemetry tree as a filesystem

HarmonyOS adaptation (see patches/, generated from the source tree):
  * cmake/googletest.cmake: use an externally provided Google Test package
    (Conan gtest) instead of FetchContent, which needs github.com access and
    pins googletest v1.14.0 (not available in the artifact repository).
  * src/telemetry/node.cpp, src/telemetry/aggFile.cpp: the OHOS SDK ships
    libc++ 15, which does not provide the std::ranges algorithms used upstream;
    the classic <algorithm> equivalents are used instead.
  * src/appFs/CMakeLists.txt: stdc++fs is a GCC-only runtime library, and the
    static libfuse3.a of the dependency carries FUSE_3.x symbol versions, which
    a shared library cannot re-export. SOVERSION is pinned so that both
    libraries export a real DT_SONAME.

License: BSD-3-Clause
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class TelemetryConan(ConanFile):
    name = "telemetry"
    version = "1.4.0"
    description = "telemetry — library for the collection and processing of telemetry data"
    license = "BSD-3-Clause"
    homepage = "https://github.com/CESNET/telemetry"
    url = "https://github.com/CESNET/telemetry"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # appFs is a FUSE3 filesystem: upstream detects the dependency with
        # pkg_check_modules(fuse REQUIRED IMPORTED_TARGET fuse3>=3.2.1) and its
        # public header include/appFs.hpp includes <fuse3/fuse.h>. The headers
        # must therefore reach every consumer of appFs.
        self.requires("libfuse/3.18.2", transitive_headers=True)

    def build_requirements(self):
        # Upstream unit tests are built with Google Test. Upstream fetches
        # googletest with FetchContent; the patch replaces that with the Google
        # Test package of the ARTIFACT repository.
        self.test_requires("gtest/1.17.0.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"telemetry supports only Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # fuse3 is discovered by the upstream CMake files through pkg-config;
        # CMakeToolchain puts the .pc files generated here on PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["TELEMETRY_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["TELEMETRY_INSTALL_TARGETS"] = True
        tc.variables["TELEMETRY_ENABLE_TESTS"] = True
        tc.variables["TELEMETRY_ENABLE_DOC_DOXYGEN"] = False
        tc.variables["TELEMETRY_BUILD_EXAMPLES"] = False
        # cmake/installation.cmake resolves the install directories at configure
        # time, so keep them relative to CMAKE_INSTALL_PREFIX (Conan installs
        # into the package folder with --prefix).
        tc.variables["LIB_INSTALL_DIR"] = "lib"
        tc.variables["INCLUDE_INSTALL_DIR"] = "include"
        # The OHOS CMake platform module does not define the SONAME linker
        # flags, so CMake would drop -soname and emit unversioned libraries
        # without DT_SONAME (L5a).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        gtest = self.dependencies["gtest"]
        tc.variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream unit tests (57 cases, see reports/test-report.md). They are
        # self-contained: every case works inside the current working directory.
        test_env = Environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with test_env.vars(self).apply():
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # appFs depends on telemetry, so the dependent library comes first for
        # static linking.
        self.cpp_info.libs = ["appFs", "telemetry"]
        # include/appFs.hpp includes <fuse3/fuse.h>: consumers need the fuse3
        # headers of the libfuse package.
        self.cpp_info.requires = ["libfuse::libfuse"]
        # Public compile definitions of the appFs target upstream: the FUSE 3.0
        # ABI and a 64-bit off_t.
        self.cpp_info.defines = ["FUSE_USE_VERSION=30", "_FILE_OFFSET_BITS=64"]
