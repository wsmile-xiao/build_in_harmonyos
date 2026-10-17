#!/usr/bin/env python3
"""Conan recipe — c-blosc2 2.23.1 (high-performance lossless compression library).

c-blosc2 is the next generation of the Blosc compression library. It ships
internal copies of LZ4, zlib-ng and ZSTD, so by default it has no external
runtime dependencies. Threads (pthreads) is the only system requirement.

Build system: CMake (cmake_minimum_required 3.16.3, no policy workaround needed).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class CBlosc2Conan(ConanFile):
    name = "c-blosc2"
    version = "2.23.1"
    description = "A blocking, shuffling and lossless compression library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Blosc/c-blosc2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"c-blosc2 only supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build only the library; skip fuzzers/benchmarks/examples/plugins
        # (benchmarks depend on clock_gettime which is unavailable on OHOS).
        # BUILD_TESTS=ON enables the upstream CTest suite (test_blosc2, frame,
        # shuffle_roundtrip, compat, etc.) so rule 5 (上游测试必须运行) is met.
        tc.cache_variables["BUILD_TESTS"] = "ON"
        tc.cache_variables["BUILD_FUZZERS"] = "OFF"
        tc.cache_variables["BUILD_BENCHMARKS"] = "OFF"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_PLUGINS"] = "OFF"
        # Static/shared selection driven by the Conan "shared" option.
        tc.cache_variables["BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.cache_variables["BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        # Use the internal codec sources (no external lz4/zlib/zstd deps).
        tc.cache_variables["PREFER_EXTERNAL_LZ4"] = "OFF"
        tc.cache_variables["PREFER_EXTERNAL_ZLIB"] = "OFF"
        tc.cache_variables["PREFER_EXTERNAL_ZSTD"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the upstream CTest suite (rule 5: 上游测试必须运行).
        # OHOS arm64 binaries are musl-based ELF; on an aarch64 host with the
        # OHOS sysroot musl ld (/lib/ld-musl-aarch64.so.1) they execute natively.
        # Serial -j1 execution avoids flaky parallel races (test_fill_special /
        # test_frame_get_offsets touch shared temp files).
        self.run(
            "ctest --output-on-failure --timeout 120 -j1",
            env="conanrun",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Library OUTPUT_NAME is "blosc2" (libblosc2.a / libblosc2.so).
        self.cpp_info.libs = ["blosc2"]
        self.cpp_info.set_property("cmake_file_name", "Blosc2")
        self.cpp_info.set_property("cmake_target_name", "Blosc2::blosc2")
        self.cpp_info.set_property("pkg_config_name", "blosc2")
