#!/usr/bin/env python3
"""Conan recipe for dmtx 0.7.8 (libdmtx) on HarmonyOS PC.

libdmtx is a Data Matrix barcode reading/writing library. Pure C, zero
external deps (only libm). Upstream v0.7.8 ships a native CMakeLists.txt
(unlike 0.7.5 where a CMakeLists had to be generated in-recipe — see
archives/l/libdmtx/0.7.5).

Upstream tests (test/): test_simple (encode→decode in-memory roundtrip)
and test_unit (timeAddTest), registered via add_test when BUILD_TESTING
is on. The consumer test_package performs its own encode/decode roundtrip
against the packaged library.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class DmtxConan(ConanFile):
    name = "dmtx"
    version = "0.7.8"
    description = ("Data Matrix barcode reading/writing library "
                   "(libdmtx), published under the short package name "
                   "'dmtx' — version follow-up of libdmtx/0.7.5")
    license = "BSD-2-Clause"
    homepage = "https://github.com/dmtx/libdmtx"
    url = "https://github.com/dmtx/libdmtx"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 DMTX_SHARED/DMTX_STATIC 默认双开（0.7.8 上游注释：static
        # 默认 ON "will default to OFF someday later (maybe 0.7.9/0.8)"）
        # ——按 Conan options 单一形态构建，避免同产物双 .so+.a 混装
        tc.variables["DMTX_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["DMTX_STATIC"] = "OFF" if self.options.shared else "ON"
        # 上游 test/ 注册 test_simple/test_unit（BUILD_TESTING 默认 OFF，
        # CI 侧无需源内测试——consumer test_package 独立 roundtrip 验证；
        # 本地验证轮实测：BUILD_TESTING=ON + 宏修复后 ctest 2/2 全过——
        # test_simple（roundtrip）与 test_unit（timeAddTest）均 Passed）
        tc.variables["BUILD_TESTING"] = "OFF"
        # 上游 0.7.8 CMakeLists 丢失了 0.7.5 时代的
        # check_include_file(sys/time.h)/check_function_exists(gettimeofday)
        # 检测——dmtxtime.c 落到 "#else Generic 1-second resolution" 分支
        # （DMTX_TIME_PREC_USEC=1000000），导致 dmtxTimeAdd(t,1) 直接跳整秒
        # （实测 usec=999000 不进位）→ 上游 unit_test 的 timeAddTest
        # FAIL(3)。OHOS/Linux 有 gettimeofday——显式补 define 走正确分支
        tc.variables["CMAKE_C_FLAGS"] = (
            "-DHAVE_SYS_TIME_H=1 -DHAVE_GETTIMEOFDAY=1"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["dmtx"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
