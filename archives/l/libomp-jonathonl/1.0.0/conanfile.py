#!/usr/bin/env python3
"""Conan recipe — libomp-jonathonl 1.0.0 (CMake)."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


required_conan_version = ">=2.0"


class LibompJonathonlConan(ConanFile):
    name = "libomp-jonathonl"
    version = "1.0.0"
    description = "A C++11 parallel programming library that mimics OpenMP syntax"
    license = "MIT"
    homepage = "https://github.com/jonathonl/omp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The OHOS SDK already ships libomp.so/libomp.a. Keep the default
        # static so this unrelated library cannot shadow the system runtime.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream declares CMake 3.5; CMake 4 needs an explicit policy floor.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run(
                os.path.join(self.build_folder, "omp-test"),
                env="conanrun",
            )
            print(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(
                    {
                        "status": "passed",
                        "framework": "standalone executable",
                        "command": "./omp-test",
                        "discovered": 1,
                        "executed": 1,
                        "passed": 1,
                        "failed": 0,
                        "skipped": 0,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["omp"]
        self.cpp_info.set_property("cmake_file_name", "libomp-jonathonl")
        self.cpp_info.set_property(
            "cmake_target_name", "libomp-jonathonl::libomp-jonathonl"
        )
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
