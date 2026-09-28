#!/usr/bin/env python3
"""Conan recipe — erkir 2.1.1 (geodesic / trigonometric calculations, C++11, CMake).

Upstream facts (audited from the v2.1.1 tarball, 33117 bytes,
sha256 b314824c126bf933e2f08e5335e12b7ef3ded9ceb341d542276455d991e7e85d,
byte-identical to the ConanCenterIndex recipe for 2.1.1):

  * Pure CMake project: 7 translation units in src/, 8 public headers in
    include/, zero external dependencies (no requires()).
  * Upstream tests: a single test/test.cpp compiled into the `unittest`
    binary and registered as ONE ctest entry (`unittests`, add_test in
    test/CMakeLists.txt). The binary is self-counting: it prints
    "Total tests: N, passed: P, failed: F" and returns 1 when F != 0.
    N is the assertion execution count (325 on this device): the 106
    source-level assertion sites include loops over coordinate/vector
    variants, so a single site can execute many times.
  * Test code is not modified by this adaptation; the upstream test
    sources ship byte-identical.

OHOS / HarmonyOS PC notes:

  * The top-level CMakeLists.txt hard-codes an x86/x64-only architecture
    block: `if (NOT MSVC)` sets TARGET_ARCH=x86 (default) and injects
    `-m32`, and anything else FATAL_ERRORs with "Incorrect target
    architecture specified". On arm64 that is fatal before the first
    compile, so patch 0001 disables the whole block (same approach the
    ConanCenterIndex recipe takes). The block also carried
    `-Wall -Wextra -pedantic -Werror`; with clang 15 treating upstream
    warnings as errors that would only hide real portability signal, so
    losing it along with the -m32 flags is intended.
  * BUILD_SHARED_LIBS defaults to ON upstream; this recipe pins it from
    the `shared` option (default OFF, R26/R4 static-by-default).
  * CODE_COVERAGE is ON by default whenever ENABLE_TESTING is set and
    would inject --coverage (extra link runtime, no value for a release
    package), so the recipe turns it off explicitly.
  * The upstream install tree drops an erkirConfig.cmake into
    lib/cmake/erkir and README.md into share/doc — both collide with the
    CMakeDeps-generated config / are docs, so they are removed from the
    package (same as the ConanCenterIndex recipe).
  * Math symbols come from libm on Linux/OHOS (R32: os test accepts
    "OHOS").
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class ErkirConan(ConanFile):
    name = "erkir"
    version = "2.1.1"
    description = "C++ library for geodesic and trigonometric calculations"
    license = "MIT"
    homepage = "https://github.com/vahancho/erkir"
    url = "https://github.com/vahancho/erkir"
    topics = ("earth", "geodesy", "geography", "coordinate-systems", "geodetic", "datum")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # erkir has zero external dependencies (audited: no find_package /
        # ExternalProject / FetchContent anywhere in the v2.1.1 sources).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # 层1（TEST_QUALITY_SPEC §3.1）：build() 末尾跑上游 ctest。
        tc.cache_variables["ENABLE_TESTING"] = True
        tc.cache_variables["CODE_COVERAGE"] = False
        # GNUInstallDirs: keep every artifact in lib/ (no lib64 split).
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 并行度上限：Conan 的 CMake helper 会无条件追加 `-j<tools.build:jobs>`，
        # 而该 conf 缺省取 os.cpu_count()（本机 20 / CI worker 亦 20，affinity 只有 8
        # ⇒ 2.5× 超订）。CI 构建 #62527 实测在 worker 内存受限窗口里 -j20 触发
        # `make[2]: /bin/sh: Out of memory` + `can't fork - try again` →
        # `Error 127 / Error 1`，被上层报成「编译失败」（源码与工具链本身无错）。
        # 取 2 与槽位纪律一致（2 槽 × j2 = 4 路 ≤ affinity 8）；同族先例
        # archives/l/libheif-openjpeg/1.23.0、archives/o/openjpeg2/2.5.4、
        # archives/l/librtpi/1.0.0（均在 build() 内、cmake.build() 之前 define）。
        if str(self.settings.os) == "OHOS":
            self.conf.define("tools.build:jobs", 2)
        cmake.build()
        # 层1：上游官方测试（test/test.cpp → unittests 单个 ctest 条目）。
        # 交叉编译时由 tools.build:skip_test 控制跳过。
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream ships its own CMake package config; it would collide
        # with the CMakeDeps-generated one, and share/ is README.md only.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["erkir"]
        self.cpp_info.set_property("cmake_file_name", "erkir")
        self.cpp_info.set_property("cmake_target_name", "erkir::erkir")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
