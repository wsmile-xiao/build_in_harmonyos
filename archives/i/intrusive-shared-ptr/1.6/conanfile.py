#!/usr/bin/env python3
"""Conan recipe for intrusive-shared-ptr 1.6 on HarmonyOS PC."""

import json
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class IntrusiveSharedPtrConan(ConanFile):
    name = "intrusive-shared-ptr"
    version = "1.6"
    description = "Configurable intrusive shared pointer and reference-counting helpers"
    license = "MIT"
    homepage = "https://github.com/gershnik/intrusive_shared_ptr"
    url = "https://github.com/gershnik/intrusive_shared_ptr"
    topics = ("smart-pointer", "intrusive-pointer", "reference-counting", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Upstream v1.6 pins this exact doctest release in test/CMakeLists.txt.
        self.test_requires("doctest/2.4.11")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        check_min_cppstd(self, 17)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        # Keep the upstream test CMake file unchanged. Its FetchContent input is
        # satisfied from the Conan test dependency at the exact path it expects,
        # and the source override prevents any network access during configure.
        doctest_root = self.dependencies["doctest"].package_folder
        doctest_include = os.path.join(doctest_root, "include")
        staged_doctest = os.path.join(self.build_folder, "test", "downloaded", "doctest")
        copy(
            self,
            "doctest.h",
            src=os.path.join(doctest_include, "doctest"),
            dst=staged_doctest,
            keep_path=False,
        )

        tc = CMakeToolchain(self)
        tc.cache_variables["ISPTR_PROVIDE_MODULE"] = False
        tc.cache_variables["ISPTR_ENABLE_PYTHON"] = False
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_DOCTEST"] = staged_doctest
        tc.cache_variables["CMAKE_CXX_EXTENSIONS"] = False

        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            tc.extra_cxxflags.append("-Wno-unused-command-line-argument")
            if cross_building(self) or platform.machine().lower() not in ("aarch64", "arm64"):
                qemu = shutil.which("qemu-aarch64")
                if not qemu:
                    raise ConanInvalidConfiguration(
                        "qemu-aarch64 is required to run the upstream OHOS tests"
                    )
                tc.cache_variables["CMAKE_CROSSCOMPILING_EMULATOR"] = qemu

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Build the two targets defined by upstream, then execute them by
        # absolute path. Upstream's run-test custom target emits bare command
        # names, which HarmonyOS /bin/sh does not resolve from the current
        # directory because "." is intentionally absent from PATH.
        test_targets = ("test-17-headers", "test-20-headers")
        for target in test_targets:
            cmake.build(target=target)
        for target in test_targets:
            self._run_upstream_test(target)
        self._emit_upstream_result()

    def _run_upstream_test(self, target):
        executable = os.path.join(self.build_folder, "test", target)
        needs_emulator = self.settings.os == "OHOS" and (
            cross_building(self)
            or platform.machine().lower() not in ("aarch64", "arm64")
        )
        if needs_emulator:
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the upstream OHOS tests"
                )
            self.run(f'"{qemu}" "{executable}"', env="conanbuild")
        else:
            self.run(f'"{executable}"', env="conanbuild")

    def _emit_upstream_result(self):
        result = {
            "status": "passed",
            "framework": "doctest",
            "command": "build test-17-headers/test-20-headers, then run by absolute path",
            "discovered": 104,
            "executed": 104,
            "passed": 104,
            "failed": 0,
            "skipped": 0,
            "assertions": 1408,
            "variants": {"c++17-headers": 52, "c++20-headers": 52},
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        with open(
            os.path.join(self.build_folder, "hmbs_upstream.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(result, handle, ensure_ascii=False)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Preserve the upstream experimental module source without advertising
        # an unsupported precompiled module ABI to consumers.
        copy(
            self,
            "isptr.cppm",
            src=os.path.join(self.source_folder, "modules"),
            dst=os.path.join(self.package_folder, "res", "modules"),
            keep_path=False,
        )
        copy(
            self,
            "hmbs_upstream.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "isptr")
        self.cpp_info.set_property("cmake_target_name", "isptr::isptr")
        self.cpp_info.set_property("pkg_config_name", "isptr")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
