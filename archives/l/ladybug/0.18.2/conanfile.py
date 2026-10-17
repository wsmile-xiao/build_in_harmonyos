#!/usr/bin/env python3
"""Conan recipe — ladybug 0.18.2 (Lbug 图数据库 + lbug CLI).

CMake 构建。依赖 openssl/3.5.6.1.1（ohpcd 制品仓预编译包，R35 已验证）。

OHOS 适配要点（对应 patches/ 中的 10 个补丁）：
  - simsimd SVE/dotprod/fp16/bf16 扩展后端禁用（OHOS clang15 不支持 arm_sve.h /
    target(arch=+dotprod/...) 内建函数），仅 NEON baseline；
  - _LIBCPP_ENABLE_EXPERIMENTAL + -lc++experimental（OHOS 共享 libc++ 缺
    std::format 符号，静态 libc++experimental.a 有）；
  - 跳过 -latomic（OHOS 无 libatomic，aarch64 clang 内联 128 位原子操作）；
  - 依赖类型补 typename、结构化绑定改普通变量、std::atomic_ref 改
    __atomic_exchange_n（OHOS libc++15 兼容）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LadybugConan(ConanFile):
    name = "ladybug"
    version = "0.18.2"
    description = "Lbug - 嵌入式图数据库 (Property Graph + Cypher)，含 lbug 交互式 shell 命令行工具"
    license = "MIT"
    homepage = "https://github.com/LadybugDB/ladybug"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: settings.os 判断用 in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            # OHOS: 让 CMake 明确识别 HarmonyOS 平台，触发 CMakeLists 中
            # 的 OHOS 适配分支（simsimd NEON baseline / std::format 处理）。
            # native 构建时 CMake 从 uname 也能推断出 HarmonyOS，这里显式
            # 设置保证 CI 上结果一致。
            if str(self.settings.os) == "OHOS":
                tc.cache_variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                    "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
            # OpenSSL 3: 指向 conan openssl 包自带的 OpenSSLConfig.cmake
            # （提供 OpenSSL::SSL / OpenSSL::Crypto imported targets，静态库）
            if self.dependencies.get("openssl"):
                openssl_pkg = self.dependencies["openssl"].package_folder
                tc.cache_variables["OpenSSL_DIR"] = os.path.join(openssl_pkg, "lib/cmake/OpenSSL")

        # ladybug 构建选项
        tc.variables["BUILD_SHARED_LBUG"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LBUG"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_SHELL"] = "ON"       # lbug CLI（R38 commands.json）
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_EXTENSION_TESTS"] = "OFF"
        tc.variables["BUILD_SINGLE_FILE_HEADER"] = "OFF"  # 不生成单头文件（避免 Python 依赖）
        tc.variables["ENABLE_BACKTRACES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lbug"]
        self.cpp_info.bindirs = ["bin"]          # lbug CLI -> R38 commands.json
        # liblbug.a/.so 内部引用 OpenSSL 符号（EVP_*/BIO_*/SSL_*），
        # 静态/动态消费者均需传递链接 openssl
        self.cpp_info.requires = ["openssl::openssl"]
        # OHOS: liblbug.a 引用 std::format 的 std::format_error 运行时符号，
        # 符号位于工具链的 libc++experimental.a（共享 libc++ 缺该符号）。
        # 消费者必须链接 -lc++experimental，否则 ld.lld 报
        # "undefined symbol: typeinfo for std::format_error"。
        if str(self.settings.os) == "OHOS":
            self.cpp_info.system_libs = ["c++experimental"]
