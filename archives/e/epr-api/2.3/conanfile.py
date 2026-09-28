#!/usr/bin/env python3
"""Conan recipe for epr-api 2.3 (ENVISAT product reader C API).

Build system: upstream CMake (CMakeLists.txt).  The upstream file declares
cmake_minimum_required(2.8), which modern CMake (>=3.5) rejects, so we pass
CMAKE_POLICY_VERSION_MINIMUM=3.5 to keep compatibility (same approach as the
raw cmake configure used during adaptation).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class EprApiConan(ConanFile):
    name = "epr-api"
    version = "2.3"
    description = "epr-api 2.3: C API for reading ENVISAT products"
    license = "MIT"
    homepage = "https://github.com/bcdev/epr-api"
    url = "https://github.com/bcdev/epr-api"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # 非系统同名库默认动态（R26）；shared 库时 VirtualRunEnv 会把包 libdir
    # 注入 LD_LIBRARY_PATH，test_package 消费者运行时才能找到 libepr_api.so.3。
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(2.8); CMake >= 3.5 refuses it.
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMake has no OHOS platform module.  The package is pure C, builds
        # natively with clang on OHOS, no Linux-specific APIs.
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        toolchain.cache_variables["BUILD_TESTS"] = False
        toolchain.cache_variables["BUILD_STATIC_LIB"] = not self.options.shared
        toolchain.cache_variables["BUILD_DOCS"] = False
        # Upstream symbol version script (-Wl,--version-script) produces GNU
        # versioned symbols that fail to relocate under the OHOS runtime
        # linker ("Error relocating ... symbol not found"); the upstream
        # option exists exactly for non-standard linkers.
        toolchain.cache_variables["DISABLE_SYMBOL_CONTROL"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["epr_api"]
