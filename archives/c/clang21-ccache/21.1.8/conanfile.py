#!/usr/bin/env python3
"""Conan recipe — clang21-ccache 21.1.8

C/C++ compiler cache (upstream ccache v4.14 source) adapted for HarmonyOS PC
(arm64). The package version 21.1.8 pairs with the clang 21.1.8 toolchain
naming of the competition registry; the actual upstream source is the latest
official ccache release v4.14 (tag v4.14, SHA-256 cross-verified dual-source).

Build system: CMake (project(ccache LANGUAGES C CXX), C++20 required).
OHOS 适配要点:
  1. libcxx-ohos (LLVM 15.0.4) 未提供 std::ranges::all_of/any_of/equal 算法，
     0001-0004 补丁将其替换为迭代器版 std::all_of/std::any_of/std::equal。
  2. FetchContent 依赖 (hiredis/xxhash/zstd) 预下载并指向本地目录，
     避免构建期 GitHub 网络不可达（与 clang18-ccache / clang20-ccache
     配方同策略）。
License: GPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


# FetchContent 依赖（ccache 构建期下载），预下载到本地以规避网络问题。
_FETCHCONTENT_DEPS = [
    {
        "name": "Hiredis",
        "urls": [
            "https://gh-proxy.com/https://github.com/redis/hiredis/archive/refs/tags/v1.4.1.tar.gz",
            "https://mirror.ghproxy.com/https://github.com/redis/hiredis/archive/refs/tags/v1.4.1.tar.gz",
            "https://github.com/redis/hiredis/archive/refs/tags/v1.4.1.tar.gz",
        ],
        "sha256": "ca3180359a8b1275838a45415851f8cd5c411e27bdbf18f4823012e45507d2e4",
        "subdir": "hiredis-1.4.1",
    },
    {
        "name": "Xxhash",
        "urls": [
            "https://gh-proxy.com/https://github.com/Cyan4973/xxhash/archive/refs/tags/v0.8.3.tar.gz",
            "https://mirror.ghproxy.com/https://github.com/Cyan4973/xxhash/archive/refs/tags/v0.8.3.tar.gz",
            "https://github.com/Cyan4973/xxhash/archive/refs/tags/v0.8.3.tar.gz",
        ],
        "sha256": "aae608dfe8213dfd05d909a57718ef82f30722c392344583d3f39050c7f29a80",
        "subdir": "xxHash-0.8.3",
    },
    {
        "name": "Zstd",
        "urls": [
            "https://gh-proxy.com/https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
            "https://mirror.ghproxy.com/https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
            "https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
        ],
        "sha256": "eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3",
        "subdir": "zstd-1.5.7",
    },
]


class CcacheConan(ConanFile):
    name = "clang21-ccache"
    version = "21.1.8"
    description = "A fast C/C++ compiler cache (ccache v4.14 source) for HarmonyOS"
    license = "GPL-3.0-or-later"
    homepage = "https://ccache.dev/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # ccache 4.14 要求 C++20
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # FetchContent 依赖指向本地预下载目录
        deps_dir = os.path.join(self.build_folder, "deps")
        for dep in _FETCHCONTENT_DEPS:
            dep_dir = os.path.join(deps_dir, dep["subdir"])
            var_name = f"FETCHCONTENT_SOURCE_DIR_{dep['name'].upper()}"
            tc.variables[var_name] = dep_dir
        tc.variables["DEPS"] = "DOWNLOAD"
        tc.variables["REDIS_STORAGE_BACKEND"] = "ON"
        tc.variables["HTTP_STORAGE_BACKEND"] = "ON"
        # 上游测试在适配阶段单独启用执行；包构建默认关测试
        tc.variables["ENABLE_TESTING"] = "OFF"
        tc.variables["ENABLE_IPO"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        deps_dir = os.path.join(self.build_folder, "deps")
        for dep in _FETCHCONTENT_DEPS:
            dep_dir = os.path.join(deps_dir, dep["subdir"])
            if not os.path.isdir(dep_dir):
                get(self, url=dep["urls"], sha256=dep["sha256"],
                    destination=deps_dir, strip_root=False)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]