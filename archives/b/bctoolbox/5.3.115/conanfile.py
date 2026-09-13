#!/usr/bin/env python3
"""Conan recipe — bctoolbox 5.3.115 (CMake)"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir


class BctoolboxConan(ConanFile):
    name = "bctoolbox"
    version = "5.3.115"
    description = "Portable utility toolbox used by Belledonne Communications software (logging; lists; maps; VFS; sockets)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.linphone.org/BC/public/bctoolbox"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream builds its BCUnit test suite as soon as ENABLE_TESTS_COMPONENT
        # is on (top-level CMakeLists: find_package(BCUnit 3.0.2 REQUIRED)). This
        # library is only used by the tester executable, which is executed during
        # build() as the upstream test evidence, so it is declared as a test
        # requirement: it never enters the package dependency chain of consumers.
        self.test_requires("bcunit/5.3.113")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream asks for `find_package(BCUnit 3.0.2 REQUIRED)`, but the Belledonne
        # BCUnit repository is versioned in lockstep with the linphone SDK while its
        # CMake project version has been frozen at "3.0.2" for years: the 5.3.113 tag
        # *is* the content that satisfies (and extends) the 3.0.2 API this release
        # needs. The generated config therefore has to accept a newer version than the
        # stale one upstream requests, otherwise CMake rejects the config file
        # ("compatible with requested version 3.0.2" ... found 5.3.113).
        deps.set_property("bcunit", "cmake_config_version_compat", "AnyNewerVersion")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # The Conan toolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so
        # upstream's find_package(BCUnit 3.0.2) resolves the CMakeDeps config
        # directly and its own FindBCUnit.cmake module never runs. The variables
        # that module would have produced (BCUnit_TARGET and the feature macros it
        # writes into config.h) therefore have to be provided here; without them
        # upstream passes an empty target to the tester link line and compiles the
        # CU_get_suite / CU_set_trace_handler code paths out (-Werror then fails on
        # the resulting unused parameters). bcunit/5.3.113 defines CU_get_suite and
        # CU_set_trace_handler, but is built without the curses UI, so
        # CU_curses_run_tests is absent and HAVE_CU_CURSES stays undefined.
        tc.variables["BCUnit_TARGET"] = "bcunit::bcunit"
        tc.variables["HAVE_CU_GET_SUITE"] = True
        tc.variables["HAVE_CU_SET_TRACE_HANDLER"] = True
        tc.variables["HAVE_CU_CURSES"] = False
        # Build and run the upstream BCUnit test suite (bctoolbox-tester) in
        # build(); the run output is the upstream test evidence of this recipe.
        tc.variables["ENABLE_TESTS_COMPONENT"] = "ON"
        tc.variables["ENABLE_UNIT_TESTS"] = "ON"
        # mbedtls wrapper in 5.3.115 targets the mbedtls v2/v3 API only (upstream
        # warns "requires v2 or v3"; v4 dropped headers it includes such as
        # mbedtls/ctr_drbg.h). Only mbedtls 4.1.0 is published on the OHOS
        # profile, so the package is built without the optional crypto backend.
        tc.variables["ENABLE_MBEDTLS"] = "OFF"
        # decaf is not published on the OHOS profile (optional ECC feature).
        tc.variables["ENABLE_DECAF"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the upstream tester for real: every suite compiled into this build
        # (the mbedtls-gated crypto/encrypted_vfs suites are absent when the
        # crypto backend is off) is executed here and its exit code gates the
        # package build.
        tester = os.path.join(self.build_folder, "tester", "bctoolbox-tester")
        if not os.path.isfile(tester):
            raise ConanException(f"upstream tester was not built at {tester}")
        env = Environment()
        libdirs = [os.path.join(self.build_folder, "src")]
        for dep in self.dependencies.test.values():
            libdirs.extend(dep.cpp_info.libdirs)
        env.define("LD_LIBRARY_PATH", os.pathsep.join(libdirs))
        # Run from the tester's own directory: in the shared build the executable records
        # relative DT_NEEDED entries ("../src/libbctoolbox.so"), and a loader resolves
        # such a name as a literal path against the current directory, so the dynamic
        # libraries are only found when started from there.
        with env.vars(self).apply():
            self.run(f'"{tester}"', cwd=os.path.dirname(tester), env=None)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The tester executable is a build-time verification artifact (already
        # executed in build()), not a deliverable of this library package: drop
        # it so the package ships the library and its headers alone.
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["bctoolbox"]
        # The library is built from C++17 objects behind a C-compatible API. When
        # packaged as a static archive a pure C consumer must also link the C++
        # runtime or the link fails on std::length_error / __cxa_throw / vtables.
        # With shared=True the .so already carries DT_NEEDED libc++_shared.so.
        if not self.options.shared:
            self.cpp_info.system_libs = ["c++"]
