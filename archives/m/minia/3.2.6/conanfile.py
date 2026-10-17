#!/usr/bin/env python3
"""Conan recipe for Minia 3.2.6, including its pinned GATB submodule."""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class MiniaConan(ConanFile):
    name = "minia"
    version = "3.2.6"
    description = "Short-read assembler based on a de Bruijn graph"
    license = "AGPL-3.0-or-later"
    homepage = "https://gatb.inria.fr/software/minia/"
    url = "https://github.com/GATB/minia"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Vendored HDF5 enables the zlib filter and looks up ZLIB. The
        # harmonybrew ZLIB config package reports ZLIB_FOUND=FALSE.
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # uname -s is HarmonyOS, and CMake ships no Platform/HarmonyOS module.
        # The Conan toolchain prepends the generators directory to
        # CMAKE_MODULE_PATH before platform detection, so the shim below is
        # picked up when CMake adopts the host name. Do not pass
        # -DCMAKE_SYSTEM_NAME: CMakeDetermineSystem then forces
        # CMAKE_CROSSCOMPILING=TRUE even if the name matches the host, and
        # the bundled HDF5 try_run() stops with PLEASE_FILL_OUT-FAILED_TO_RUN.
        # Renaming the system to Linux does the same, because the host name
        # stays HarmonyOS.
        if str(self.settings.os) == "OHOS":
            platform_dir = os.path.join(self.generators_folder, "Platform")
            os.makedirs(platform_dir, exist_ok=True)
            with open(os.path.join(platform_dir, "HarmonyOS.cmake"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    "set(UNIX 1)\n"
                    "set(CMAKE_SYSTEM_PROCESSOR aarch64)\n"
                    "include(Platform/Linux)\n"
                )
        deps = CMakeDeps(self)
        deps.generate()
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["HDF5_BUILD_TOOLS"] = "OFF"
        toolchain.generate()

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(
            self,
            **sources["minia"],
            strip_root=True,
            filename=f"minia-{self.version}.tar.gz",
        )
        gatb_root = os.path.join(self.source_folder, "thirdparty", "gatb-core")
        os.makedirs(gatb_root, exist_ok=True)
        gatb_source = sources["gatb_core"]
        get(
            self,
            url=gatb_source["url"],
            sha256=gatb_source["sha256"],
            strip_root=True,
            filename=f"gatb-core-{gatb_source['revision']}.tar.gz",
            destination=gatb_root,
        )

    def _run_upstream_tests(self):
        # test/simple_test.sh calls the unqualified command "python".
        # The device has python3 only. The wrapper is outside the upstream
        # tree and does not modify the test script.
        shim = os.path.join(self.build_folder, "python3-as-python")
        os.makedirs(shim, exist_ok=True)
        wrapper = os.path.join(shim, "python")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\nexec python3 \"$@\"\n")
        os.chmod(wrapper, 0o755)

        bin_dir = os.path.join(self.source_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        built = os.path.join(self.build_folder, "bin", "minia")
        staged = os.path.join(bin_dir, "minia")
        shutil.copy2(built, staged)
        os.chmod(staged, 0o755)

        path = shim + os.pathsep + os.environ.get("PATH", "")
        self.run(
            f'PATH="{path}" bash simple_test.sh',
            cwd=os.path.join(self.source_folder, "test"),
        )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Command-line -D is read before cmake_minimum_required(VERSION 2.6).
        # A toolchain cache variable is applied too late for that check.
        cmake.configure(variables={
            "PATCH": "6",
            "NO_SSE": "ON",
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        })
        cmake.build(target="minia")
        self._run_upstream_tests()

    def package(self):
        CMake(self).install()
        gatb = os.path.join(self.source_folder, "thirdparty", "gatb-core", "gatb-core")
        copy(self, "LICENCE", src=gatb, dst=os.path.join(self.package_folder, "licenses", "gatb-core"))
        copy(self, "THIRDPARTIES.md", src=gatb,
             dst=os.path.join(self.package_folder, "licenses", "gatb-core"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "minia")
