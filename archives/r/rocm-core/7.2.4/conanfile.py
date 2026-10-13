#!/usr/bin/env python3
"""Conan recipe for rocm-core 7.2.4 (ROCm release version / install-path query library).

rocm-core is the base ROCm component every other ROCm package depends on: it
exposes the ROCm release version (getROCmVersion) and the ROCm install-path
resolution helper (getROCmInstallPath).

OHOS scope of this adaptation
-----------------------------
The OHOS clang toolchain shipped with the platform (clang 15.0.4, target
aarch64-unknown-linux-ohos) registers only host CPU backends; it has no
AMDGCN/amdgcn target and the device exposes no /dev/kfd or /dev/dri. rocm-core
itself contains no GPU device code -- it is a plain host-side C++ library, so
the GPU toolchain is irrelevant here. We therefore build ONLY the host-side
library with the ordinary OHOS C++ toolchain and never reach for hipcc or any
AMDGPU code path. See notes.md for the `clang -print-targets` evidence.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class RocmCoreConan(ConanFile):
    name = "rocm-core"
    version = "7.2.4"
    description = ("ROCm core component: query the ROCm release version and the "
                   "ROCm install path")
    license = "MIT"
    homepage = "https://github.com/ROCm/rocm-core"
    url = "https://github.com/ROCm/rocm-core"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Intentionally empty: rocm-core is fully self-contained (CMakeLists.txt
        # + rocm_version.cpp + rocm_getpath.cpp + utils.cmake). It has no
        # external Conan requires and no tool_requires -- the OHOS toolchain and
        # cmake come from the profile / CI environment.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The upstream build requires -DROCM_VERSION=<x.y.z>; parse_rocm_version()
        # in utils.cmake derives VERSION_MAJOR/MINOR/PATCH from it.
        tc.variables["ROCM_VERSION"] = self.version
        # Default to a static library (upstream defaults to shared). A static
        # archive keeps the package self-contained: with BUILD_SHARED_LIBS=0
        # getROCmInstallPath() resolves the install path from ROCM_PATH
        # deterministically (no runtime dlopen of lib<name>.so to resolve).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Injected project prelude. CMAKE_PROJECT_INCLUDE is processed at the end
        # of the upstream project() call, i.e. before any target is declared, so
        # both settings reach the library:
        #
        #   1. enable_testing() -- upstream never calls it, so the generated
        #      Makefile has no `test` target and conan's cmake.test() (which runs
        #      `cmake --build --target test`) aborts with
        #      "No rule to make target 'test'". (The upstream suite registers 0
        #      cases -- see test_package/MANIFEST.yml.)
        #   2. -fno-delete-null-pointer-checks -- the public headers declare the
        #      API __attribute__((nonnull)), so from -O1 upwards clang legally
        #      assumes the out-parameters are never NULL and deletes the
        #      NULL_CHECK guards in rocm_version.cpp / rocm_getpath.cpp. The
        #      Release (-O3) object stores straight through the pointer, so
        #      getROCmVersion(NULL, ...) / getROCmInstallPath(NULL, ...) SIGSEGV
        #      instead of returning VerIncorrectParameters / PathIncorrecPararmeters.
        #      The flag makes the compiler honour the guards as written. Verified
        #      by an A/B compile of the same sources at -O0/-O3 (see notes.md).
        # Note: upstream's own `set(CXX_FLAGS ...)` (CMakeLists.txt:91) is a plain
        # variable that is never applied to any target, so it cannot be used here.
        project_prelude = os.path.join(
            self.generators_folder, "rocm-core-project-prelude.cmake")
        save(self, project_prelude,
             "enable_testing()\n"
             "add_compile_options(-fno-delete-null-pointer-checks)\n")
        tc.variables["CMAKE_PROJECT_INCLUDE"] = project_prelude
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # -- Layer 1: upstream official test suite (TEST_QUALITY_SPEC 3.1) --
        # rocm-core 7.2.4 ships NO test directory and registers no CTest cases,
        # but the recipe still drives the upstream test entry point so the
        # conan build log carries the ctest execution trace (required by the
        # test-quality spec / CI L1c trace check).
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Drop upstream's non-library helper tooling. They are Python tools
        # that cannot work on OHOS (rdhc.py needs the prettytable/PyYAML
        # modules the platform does not ship; runpath_to_rpath.py needs
        # pyelftools). Because the Conan/OHOS install layout maps
        # CMAKE_INSTALL_LIBEXECDIR onto bin/, they land under bin/ and would
        # (a) make the package look like a CLI tool and (b) fail the L2 smoke
        # test. Remove the whole bin/, libexec/ and share/rdhc/ trees and keep
        # the library, its public headers, the CMake package config, the ROCm
        # .info/version marker and the Lmod module file.
        for relative in ("bin", "libexec", os.path.join("share", "rdhc")):
            target = os.path.join(self.package_folder, relative)
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "rocm-core")
        self.cpp_info.set_property("cmake_target_name", "rocm-core::rocm-core")
        self.cpp_info.libs = ["rocm-core"]
        self.cpp_info.includedirs = ["include", "include/rocm-core"]
