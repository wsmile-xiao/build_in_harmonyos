#!/usr/bin/env python3
"""Conan recipe — BoringSSL 0.20260927 (CMake build system).

BoringSSL 是 Google 维护的 OpenSSL 分支（Chromium / Android 的 TLS 栈）。
上游没有与任务版本一致的 tag：`0.20260927` 固定为官方 main 快照
`e98a6564575520260ef95b2389e5d63a24917093`（2026-09-25，见 notes.md）。

关键规则：
  - R26: libssl / libcrypto 是系统同名库（系统自带 /usr/lib/libssl.so.3、
    /usr/lib/libcrypto.so.3）→ 只允许静态构建（BUILD_SHARED_LIBS=OFF），
    不产出 .so，避免污染系统库目录。
  - R32: 平台判断使用 `in ("Linux", "OHOS")`（本配方无需手动分支）。
  - R33: 编译器与编译标志全部来自 Conan CMakeToolchain，不使用裸 shell 变量。
  - R38: 包内含 `bssl` 命令行工具 → 软件级 commands.json 声明。
  - R49: 不注入共享系统前缀（/usr/local）；安装前缀由 Conan 包目录管理。
  - E092: CMake 4.x 在 HarmonyOS 上无平台文件（"System is unknown to cmake"）
    → 别名 CMAKE_SYSTEM_NAME=Linux（先例 archives/a/airspy 等），使上游
    Linux 专用适配生效（-D_XOPEN_SOURCE=700 等）。
  - Go 工具链非必需：汇编为预生成文件（gen/*-linux.S，平台宏守卫），
    所有 Go 相关目标位于 `if(GO_EXECUTABLE)`（cmake/go.cmake 注释确认
    Go 为 optional dependency，仅测试 runner / FIPS 需要）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BoringSSLConan(ConanFile):
    name = "boringssl"
    version = "0.20260927"
    description = ("BoringSSL: Google's fork of OpenSSL (TLS / cryptography "
                   "library used by Chromium and Android); pinned to official "
                   "main@e98a6564 snapshot")
    license = "OpenSSL"
    homepage = "https://boringssl.googlesource.com/boringssl/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # BoringSSL 自包含：无外部库依赖（仅 libc / pthread）。
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: 系统同名库（/usr/lib/libssl.so.3、libcrypto.so.3）禁止动态链接。
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "boringssl: R26 要求静态构建 —— 系统存在同名库 "
                "/usr/lib/libssl.so.3 与 /usr/lib/libcrypto.so.3，"
                "shared=True 被拒绝")
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        # E092: CMake 在 HarmonyOS 上判为未知系统 → 按 Linux 处理。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 上游测试二进制需要构建（build() 内实际运行，R51）；不安装。
        tc.cache_variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 只构建库 + CLI + 两个上游测试二进制（不构建 benchmark / fuzz 等）。
        for target in ("crypto", "ssl", "bssl", "crypto_test", "ssl_test"):
            cmake.build(target=target)

        # R51: 实际运行上游测试（gtest 单进程用例）。
        #  - crypto_test / ssl_test 的 DeathTest 依赖 /tmp 可写：鸿蒙 /tmp
        #    只读（E002）→ 运行时过滤（用例数量差异见 notes.md R51 申报表）；
        #  - urandom_test 依赖 ptrace(PTRACE_TRACEME)，平台拒绝 → 不纳入本步。
        # 测试数据路径相对于源码根目录（上游 util/all_tests.go 同口径）。
        for binary in ("crypto_test", "ssl_test"):
            exe = os.path.join(self.build_folder, binary)
            self.run(
                f'timeout 1800 "{exe}" --gtest_filter=-*DeathTest* '
                f'--gtest_color=no',
                cwd=self.source_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 静态库，链接顺序：ssl 依赖 crypto。
        self.cpp_info.libs = ["ssl", "crypto"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # libcrypto 使用 pthread（pthread_once / pthread_key_create 等）。
        self.cpp_info.system_libs = ["pthread"]
