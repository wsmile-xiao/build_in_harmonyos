#!/usr/bin/env python3
"""Conan recipe for KWStyle 1.1.0-git20250114.eb1e46d on HarmonyOS PC.

KWStyle (Kitware Style Checker) is Kitware 官方的源码风格检查器，用于在多人协作
的软件流程中强制统一代码风格（缩进、头注释、行长、命名、空行等）。

上游事实（已核对 eb1e46d57db0 源码树）：
  - 语言：C++11（project(KWStyle ... LANGUAGES C CXX)），构建系统 CMake >= 3.10.2
  - 外部依赖：**零** —— CMakeLists.txt 全文没有任何 find_package/find_library/
    find_program；随源码 vendored 一份 KWSys（Utilities/KWSys）并作为静态库
    `kwssys` 一起编译
  - 产物：可执行文件 `bin/KWStyle` + 内部静态库 KWStyleLib/kwssys（不安装）
  - 安装：install(TARGETS KWStyle RUNTIME DESTINATION bin)，另安装若干
    Documentation/*.kws.xml 示例规则与 Web/headers 到 share/KWStyle

OHOS 适配要点：
  - 零外部依赖 → 不存在依赖链断裂风险（本项目最重要的简化）
  - R26：终端工具静态构建（BUILD_SHARED_LIBS=OFF）
  - 交叉编译守卫：源码根 CMakeLists 在 BUILD_TESTING=ON 时 add_subdirectory(Testing)，
    不设 CMAKE_CROSSCOMPILING_EMULATOR 则不会生成 try_run，配置阶段安全。
    本机（OHOS aarch64）上 can_run() 为真 → 上游 CTest 真实执行（W3 本地 CI）。
    远端交叉编译环境下 can_run() 为假 → 只构建不执行，与 benchmark 1.9.5 同范式。
  - 上游 CTest 共 41 项：6 个注册单测 + 35 个 bug-tracker 对比测试
    （Testing/CMakeLists.txt 的 add_test/ADD_TEST_FROM_BUG_TRACKER），
    详见 test_package/MANIFEST.yml 的用例统计。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)


class KWStyleConan(ConanFile):
    name = "kwstyle"
    version = "1.1.0-git20250114.eb1e46d"
    description = "Kitware Style Checker - source code style consistency checker (C++ CLI)"
    license = "BSD-3-Clause AND Apache-2.0 AND BSL-1.0"
    homepage = "https://github.com/Kitware/KWStyle"
    # 配方所在仓库（仓库主流取值；code-style §5 禁止留 "CI fills this" 占位符）
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 构建产物是 bin/KWStyle 可执行文件 → application（R38：需 commands.json）
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 必须显式约束，避免在未知平台产出错误结论
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kwstyle is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 终端工具静态构建（R26）
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # 打开上游测试（Testing/ 子目录 + enable_testing）
        tc.variables["BUILD_TESTING"] = "ON"
        # 上游默认 CMAKE_CXX_STANDARD=11；显式固定以对齐 KWStyle 自身要求，
        # 同时避免继承 CI profile 的 cppstd=17 造成行为漂移。
        tc.variables["CMAKE_CXX_STANDARD"] = "11"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_EXTENSIONS"] = "OFF"

        # ── CMAKE_SYSTEM_NAME 必须取平台真名 "OHOS"（知识库 E577）──────────
        # 本机 uname -s 返回 HarmonyOS，CMake 遂取 CMAKE_SYSTEM_NAME=HarmonyOS；
        # 但 CMake 只随带 Modules/Platform/OHOS.cmake（内容为 include(Platform/Linux)），
        # 没有 Platform/HarmonyOS.cmake。平台模块不加载 → UNIX、SONAME flag、
        # find_package(Threads) 等 POSIX 语义全部未定义（CMake 只打印
        # "System is unknown to cmake"，不是错误、退出码仍为 0）。
        # 实测后果：KWSys 以 `if(NOT UNIX)` 选择 ProcessWin32.c，OHOS 上误选
        # Windows 实现 → "windows.h file not found" 编译失败。
        # 显式设为平台真名 OHOS 后 Platform/OHOS.cmake 生效，UNIX 为真，
        # KWSys 正确选用 ProcessUNIX.c。
        # 仓库同口径先例：archives/a/astromenace、archives/a/avogadrolibs、
        # archives/d/dbus（均为 tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"）。
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"

        # ── OHOS musl 不提供 POSIX 线程取消 API（知识库 E507/E099）──────────
        # KWStyle 自带（vendored）的 boost 经 boost/shared_ptr.hpp →
        # spinlock_pool → yield_k → sp_thread_sleep.hpp 间接包含该头，其中
        # pthread_setcancelstate() 在 OHOS musl 上未声明 → 编译失败。
        # 上游该头已为 Android 留了 `!defined(__ANDROID__)` 例外（Android 同样
        # 缺该函数），但未给 OHOS 留口。修复分两步，均不使用平台宏：
        #   1) patches/0001 给该头守卫补上能力宏
        #      BOOST_SP_NO_PTHREAD_SETCANCELSTATE（与仓库 boost/1.85.0 的补丁
        #      同口径，该补丁自述 R8-compliant、无平台宏）；
        #   2) 此处定义该能力宏，跳过 pthread_setcancelstate 调用但保留 nanosleep。
        # 先例：archives/b/boost-1.85（补丁 + 宏）、archives/a/afmize、
        # archives/a/autodock-vina。
        tc.preprocessor_definitions["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"] = "1"

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # 上游测试套件（41 项）。本机原生构建时真实执行；交叉编译时只构建不执行。
        # 上游把测试程序输出到 ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}（即构建目录 bin/），
        # ctest 依赖的可执行文件均已在该目录下就绪。
        if can_run(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" '
                "--output-on-failure --no-tests=error",
                cwd=self.build_folder,
            )
        else:
            self.output.info(
                "cross-building: upstream CTest binaries were built but not run"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 剥离内部开发文件（KWStyleLib/kwssys 为内部静态库；头文件仅供自身编译），
        # 包内只保留用户实际需要的 bin/KWStyle。
        rm(self, "*.cmake", self.package_folder, recursive=True)
        rm(self, "cmake", self.package_folder, recursive=True)
        rm(self, "include", self.package_folder, recursive=True)
        rm(self, "lib", self.package_folder, recursive=True)

    def package_info(self):
        # 纯命令行工具：无库可链接，下游通过 PATH 调用 KWStyle
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
