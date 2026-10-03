#!/usr/bin/env python3
"""Conan recipe — libtlx 0.6.1 (tlx: C++ algorithms/containers/templates library).

libtlx 是 "Collection of Sophisticated C++ Data Structures, Algorithms, and
Helpers"（tlx，Timo Bingmann 维护）。形态为 **header-only 为主 + 少量编译库**：
183 个头文件直接 #include 即用，另有 47 个 .cpp（string 算子族、digest 四族、
logger、thread_pool、timestamp、port/setenv、algorithm/parallel_multiway_merge）
编译进 libtlx.a（上游默认 TLX_BUILD_STATIC_LIBS=ON / SHARED=OFF）。

OHOS 适配要点（详见 notes.md）：

  * 零重依赖：上游唯一硬依赖 find_package(Threads REQUIRED)（pthread，
    musl libc 集成），无任何 conan requires / tool_requires；部分可选
    boost 组件实际未引用（grep boost 上游 CMake 零命中）。
  * 唯一补丁 0001：上游 cmake_minimum_required(VERSION 2.8.12) 被 CMake 4.x
    拒绝（<3.5 已移除），bump 为 3.5...3.22（知识库 E103 / 历史归档
    archives/t/tlx/0.6.1 同结论复现）。
  * backtrace.cpp 的 glibc execinfo 路径由上游 #if defined(__GNU_LIBRARY__)
    守卫，OHOS musl 下自动降级 TLX_HAVE_BACKTRACE_FUNC=0（空实现），
    无需补丁（W0-3 可移植性档：平台守卫已内建）。
  * 配方 build() 内 TLX_BUILD_TESTS=OFF（纯库构建）；上游 41 个测试目标
    在设备端用原生 CMake 真跑 41/41 全绿（见 test_package/MANIFEST.yml
    四口径统计与取数命令）。
  * cmake_file_name/cmake_target_name 对齐上游 install(EXPORT tlx-targets)
    的导出目标 `tlx`（无 NAMESPACE）：find_package(tlx) + tlx::tlx。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)

import os

required_conan_version = ">=2.0"


class LibtlxConan(ConanFile):
    name = "libtlx"
    version = "0.6.1"
    package_type = "static-library"

    description = ("Collection of sophisticated C++ data structures, "
                   "algorithms, and miscellaneous helpers (tlx): mostly "
                   "header-only plus a small compiled static library")
    homepage = "https://github.com/tlx/tlx"
    license = "BSL-1.0"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游用自有开关 TLX_BUILD_STATIC_LIBS/TLX_BUILD_SHARED_LIBS 控制
        # add_library 的显式 STATIC/SHARED 类型（不读 BUILD_SHARED_LIBS），
        # 必须显式映射 conan 的 options.shared。
        tc.variables["TLX_BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        tc.variables["TLX_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # 配方构建纯库（默认即 OFF，显式钉死保证 G2 干净轮不拉测试树）
        tc.variables["TLX_BUILD_TESTS"] = False
        tc.variables["TLX_USE_GCOV"] = False
        tc.variables["TLX_TRY_COMPILE_HEADERS"] = False
        tc.variables["TLX_MORE_TESTS"] = False
        tc.variables["TLX_WARNINGS_ARE_ERRORS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 对齐上游 install(EXPORT tlx-targets)（目标名 tlx，无 NAMESPACE）
        # 与 misc/cmake/tlx.pc（pkg-config 名 tlx）
        self.cpp_info.set_property("cmake_file_name", "tlx")
        self.cpp_info.set_property("cmake_target_name", "tlx::tlx")
        self.cpp_info.set_property("pkg_config_name", "tlx")
        self.cpp_info.libs = ["tlx"]
        # 上游 find_package(Threads REQUIRED) → -lpthread（musl libc 集成）
        self.cpp_info.system_libs = ["pthread"]
