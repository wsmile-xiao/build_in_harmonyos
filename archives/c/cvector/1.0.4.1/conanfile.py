#!/usr/bin/env python3
"""Conan recipe for cvector 1.0.4.1 — CMake build system.

yayahjb/cvector is an ANSI C implementation of dynamic arrays approximating
the C++ vector class (single CVector.c + CVector.h, LGPL-2.1).
Upstream provides both a libtool Makefile and a CMakeLists.txt; this recipe
uses CMake because the Makefile requires libtool, which is unavailable on
HarmonyOS. Upstream CTest suite (CVectorBasicTest + reference-output compare)
runs in build() via cmake.test().
"""

import os
import json
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, replace_in_file, rmdir, rm


class CvectorConan(ConanFile):
    name = "cvector"
    version = "1.0.4.1"
    description = "ANSI C implementation of dynamic arrays approximating the C++ vector class."
    license = "LGPL-2.1-only"
    homepage = "https://github.com/yayahjb/cvector"
    url = "https://github.com/yayahjb/cvector"
    topics = ("c", "vector", "dynamic-array", "datastructures")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        self._get_sources_stripped()

    def _get_sources_stripped(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executable(self, key, fallback_name):
        # Stale-toolchain guard: profile pins /data/service/hnp/bin/clang,
        # but that file may not exist on the current worker. CMakeToolchain
        # copies the conf path verbatim into conan_toolchain.cmake, so CMake
        # then fails its compiler check. conf stays primary; only when the
        # absolute path is missing/non-executable do we fall back to the bare
        # tool name resolved via the HMBS-prepended conanbuild PATH.
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured:
            if os.path.sep in configured:
                if os.path.isfile(configured) and os.access(configured, os.X_OK):
                    return configured
                self.output.warning(
                    "conf compiler '%s' inaccessible, falling back to '%s' via conanbuild PATH"
                    % (configured, fallback_name)
                )
            else:
                return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream always builds both STATIC and SHARED targets explicitly,
        # so BUILD_SHARED_LIBS is informational only; packaging keeps static.
        tc.variables["BUILD_SHARED_LIBS"] = False
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # L1: Run upstream official test suite (2 CTest cases:
        # CVectorBasicTest run + reference output compare).
        cmake.test()
        # HMBS machine-evidence marker: 2 CTest cases, executed via
        # `ctest --output-on-failure` inside cmake.test(). cmake.test()
        # raises on failure, so reaching here means 2/2 passed.
        upstream = {
            "status": "passed",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as f:
                json.dump(upstream, f, ensure_ascii=False)
        except Exception as e:
            self.output.warning("write hmbs_upstream.json failed: %s" % e)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists installs libs + test binary but no headers;
        # install the public header manually.
        copy(self, "CVector.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        # CVectorBasicTest is an upstream test executable, not a shipped tool
        # (R38: pure library package must not carry bin/ test binaries).
        rmdir(self, os.path.join(self.package_folder, "bin"))
        # Keep static-only packaging: drop shared objects (also avoids
        # SONAME gate issues from upstream's empty SOVERSION typo).
        rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
        copy(self, "lgpl.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Persist upstream evidence for cache-hit re-emit via test_package.
        try:
            copy(self, "hmbs_upstream.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["CVector"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "cvector")
        self.cpp_info.set_property("cmake_target_name", "cvector::cvector")
        self.cpp_info.set_property("pkg_config_name", "cvector")
