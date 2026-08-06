#!/usr/bin/env python3
"""Conan recipe for WasmEdge 0.17.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class WasmEdgeConan(ConanFile):
    name = "wasmedge"
    version = "0.17.1"
    description = "WasmEdge is a lightweight, high-performance WebAssembly runtime"
    license = "Apache-2.0"
    homepage = "https://github.com/WasmEdge/WasmEdge"
    url = "https://github.com/WasmEdge/WasmEdge"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for name, metadata in self.conan_data.get("third_party", {}).items():
            get(
                self,
                url=metadata["url"],
                sha256=metadata["sha256"],
                destination=os.path.join(self.source_folder, "third_party", name),
                strip_root=True,
                filename=f"{name}.tar.gz",
            )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WASMEDGE_BUILD_TESTS"] = "ON"
        tc.variables["WASMEDGE_BUILD_COVERAGE"] = "OFF"
        tc.variables["WASMEDGE_BUILD_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["WASMEDGE_BUILD_STATIC_LIB"] = "OFF" if self.options.shared else "ON"
        tc.variables["WASMEDGE_BUILD_TOOLS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_PLUGINS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_EXAMPLES"] = "OFF"
        tc.variables["WASMEDGE_BUILD_WASI_NN_RPC"] = "OFF"
        tc.variables["WASMEDGE_USE_LLVM"] = "OFF"
        tc.variables["WASMEDGE_FORCE_DISABLE_LTO"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        if str(self.settings.compiler) == "gcc":
            tc.extra_cxxflags.append("-Wno-error=maybe-uninitialized")
        if str(self.settings.compiler) in ("gcc", "clang", "apple-clang"):
            tc.extra_cxxflags.append("-Wno-error=array-bounds")
        third_party = os.path.join(self.source_folder, "third_party")
        tc.variables["FETCHCONTENT_SOURCE_DIR_FMT"] = os.path.join(third_party, "fmt")
        tc.variables["FETCHCONTENT_SOURCE_DIR_SPDLOG"] = os.path.join(third_party, "spdlog")
        tc.variables["FETCHCONTENT_SOURCE_DIR_SIMDJSON"] = os.path.join(third_party, "simdjson")
        tc.variables["FETCHCONTENT_SOURCE_DIR_STB"] = os.path.join(third_party, "stb")
        tc.variables["FETCHCONTENT_SOURCE_DIR_GTEST"] = os.path.join(third_party, "gtest")
        tc.generate()

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            upstream_tests = "|".join(
                [
                    "expectedTests",
                    "poTests",
                    "spanTests",
                    "wasmedgeCommonTests",
                    "wasmedgeLoaderFileMgrTests",
                    "wasmedgeValidatorRegressionTests",
                    "wasmedgeExecutorRegressionTests",
                    "wasmedgeThreadTests",
                    "wasmedgeMemInstanceTests",
                    "wasmedgeHostMockTests",
                ]
            )
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure --timeout 60 -R "{upstream_tests}"',
                env="conanbuild",
            )

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        if self.options.shared:
            build_lib_dirs = [
                os.path.join(self.build_folder, "lib"),
                os.path.join(self.build_folder, "_deps", "fmt-build"),
                os.path.join(self.build_folder, "_deps", "spdlog-build"),
            ]
            for lib_dir in build_lib_dirs:
                copy(self, "*.so*", lib_dir, os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["wasmedge"]
        self.cpp_info.system_libs = []
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs.extend(["dl", "pthread", "m"])
        if str(self.settings.os) == "Linux":
            self.cpp_info.system_libs.append("rt")
