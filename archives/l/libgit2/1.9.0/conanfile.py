#!/usr/bin/env python3
"""Conan recipe for libgit2 1.9.0 — CMake project, HarmonyOS PC (aarch64).

libgit2 是纯 C 实现的 Git 核心库，同时构建 CLI (BUILD_CLI=ON → bin/git2)。
依赖 openssl（HTTPS/SHA256 后端）与 zlib，两者均已发布到 ohpcd 制品仓。
R49: CMakeDeps/CMakeToolchain 由 generate() 生成（build_folder），依赖注入仅走
conan 依赖链，不触碰共享系统前缀。CONAN_HOME 由任务执行端注入私有目录以避免
并发缓存竞争；本配方不含任何执行端绝对路径。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Libgit2Conan(ConanFile):
    name = "libgit2"
    version = "1.9.0"
    description = "Lightweight cross-platform Git core library implementation"
    license = "GPL-2.0-only WITH GCC-exception-2.0"
    homepage = "https://libgit2.org/"
    url = "https://github.com/libgit2/libgit2"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # HTTPS/SHA256 后端与压缩依赖（W0 核验二者均已发布）
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 关闭无需带入 CI 的构建目标：测试套件由上游测试台账单独覆盖
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_FUZZERS"] = "OFF"
        # CLI（bin/git2）为交付物之一（R38 commands.json 已声明）
        tc.variables["BUILD_CLI"] = "ON"
        # HTTPS 后端 = OpenSSL；SSH 可选（libssh2 未启用，与历史适配一致）
        tc.variables["USE_HTTPS"] = "OpenSSL"
        tc.variables["USE_SSH"] = "OFF"
        # 让 libgit2 的 SelectHTTPSBackend.cmake 用模块模式检测 OpenSSL：
        # conan 生成的 openssl-config.cmake 只置 openssl_FOUND（小写），而 libgit2
        # 检查的是大写 OPENSSL_FOUND —— 关闭 PREFER_CONFIG 并显式给 OPENSSL_ROOT_DIR，
        # 使 CMake 内置 FindOpenSSL 模块走 find_library 精确找到包内 libssl/libcrypto。
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "OFF"
        openssl_folder = self.dependencies["openssl"].package_folder
        if openssl_folder:
            tc.variables["OPENSSL_ROOT_DIR"] = openssl_folder
            tc.variables["OPENSSL_INCLUDE_DIR"] = os.path.join(openssl_folder, "include")
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
        # 库文件名为 libgit2.so/.a，链接名是 git2
        self.cpp_info.libs = ["git2"]
        self.cpp_info.set_property("pkg_config_name", "libgit2")