#!/usr/bin/env python3
"""Conan recipe for iowow 1.4.18 — the skiplist based persistent key/value storage engine.

iowow 1.4.18 使用 CMake 构建系统（顶层 CMakeLists.txt，cmake_minimum_required 3.12），
与 1.5.x 的 Autark build.sh 不同：
  cmake -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF -DBUILD_EXAMPLES=OFF ...
  构建产出 lib/libiowow-1.a（src/CMakeLists.txt OUTPUT_NAME 为 iowow-${PROJECT_VERSION_MAJOR}）。

配方要点：
- 官方源码 GitHub Softmotions/iowow tag v1.4.18（R39），CI 自动镜像 fallback；
- 默认静态库（R26 语义，包内 libiowow-1.a），不输出系统同名 .so；
- R33：编译器由 CMakeToolchain 从 Conan conf（tools.build:compiler_executables）注入，
  不使用裸 ${CC} 等可能未定义的 shell 变量；
- 上游 CUnit 测试不固化进 build()（沿 1.5.2 先例 upstream_test_in_build: false），
  全量上游测试单独运行并留痕于 reports/test-report.md；
- 头文件安装于 include/iowow/，消费者 include <iowow/iwkv.h> 等；
- 平台探针（qsort_r / clock_gettime / pthread 等）全走 CMake capability detection，
  对 OHOS musl 无需任何补丁、无平台条件编译。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IowowConan(ConanFile):
    name = "iowow"
    version = "1.4.18"
    description = "iowow — the skiplist based persistent key/value storage engine"
    license = "MIT"
    homepage = "https://github.com/Softmotions/iowow"
    url = ""  # CI fills this

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
        # R26: system-name library defaults to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游选项：关闭示例/测试/基准，避免 conan create 引入 cunit 测试依赖
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 构建卫生：__FILE__ 日志宏会把 conan 缓存绝对路径固化进 rodata
        # （上游 IWLOG 用 __FILE__），-ffile-prefix-map 映射为干净相对路径，
        # 保证产物可重现且无宿主路径泄漏（clang/gcc 均支持，纯通用选项）。
        src = str(self.folders.base_source)
        cmake.configure(
            variables={"CMAKE_C_FLAGS": f"-ffile-prefix-map={src}=/iowow-src"}
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游 OUTPUT_NAME 为 iowow-${PROJECT_VERSION_MAJOR}，实际产物 libiowow-1.a；
        # 上游 .pc 文件写 -liowow 系笔误，以实际落盘文件为准
        self.cpp_info.libs = ["iowow-1"]
        # OHOS/Linux 链接：Threads::Threads + m（上游 configure 输出 LINK LIBS: -lpthread;-lm）
        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD", "Android"):
            self.cpp_info.system_libs = ["pthread", "m"]
