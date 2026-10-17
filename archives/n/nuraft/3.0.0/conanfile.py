#!/usr/bin/env python3
"""Conan recipe — nuraft 3.0.0 (CMake, vendored ASIO standalone, SSL disabled)

eBay/NuRaft：C++11 实现的 Raft 共识协议复制库。
OHOS 适配要点：
  - 非 WITH_CONAN 模式：ASIO 走 vendored（asio-1-24-0，上游 prepare.sh 指定版本），
    少一个外部依赖（ohpcd 制品仓无 asio 配方）。
  - DISABLE_SSL=1：宏 SSL_LIBRARY_NOT_FOUND=1，src/asio_service.cxx 条件编译
    排除全部 SSL 代码，无需 openssl 依赖（SSL 非本库核心路径，本库核心为 Raft 复制）。
  - BUILD_EXAMPLES=OFF：examples 不编进产物。
  - 公共头文件用 pimpl 隐藏 asio.hpp 依赖，消费者无需 asio 头文件。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm


class NuRaftConan(ConanFile):
    name = "nuraft"
    version = "3.0.0"
    description = "C++ implementation of Raft core logic as a replication library (eBay/NuRaft)"
    license = "Apache-2.0"
    homepage = "https://github.com/eBay/NuRaft"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_tests": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 主源码：eBay/NuRaft v3.0.0
        get(self, **self.conan_data["sources"]["nuraft"], strip_root=True)
        # vendored ASIO：上游 prepare.sh 指定 asio-1-24-0，
        # 拷贝 asio/ 子树到源码根 asio/ 供 CMake find_path 命中
        get(self, **self.conan_data["sources"]["asio"], strip_root=False)
        asio_root = os.path.join(self.source_folder, "asio-asio-1-24-0")
        shutil.move(os.path.join(asio_root, "asio"),
                    os.path.join(self.source_folder, "asio"))
        shutil.rmtree(asio_root, ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 非 WITH_CONAN 模式：vendored ASIO standalone（ASIO_STANDALONE）
        tc.variables["DISABLE_SSL"] = "1"          # SSL_LIBRARY_NOT_FOUND=1，免 openssl
        tc.variables["BUILD_EXAMPLES"] = "OFF"     # examples 不编进产物
        tc.variables["BUILD_TESTING"] = "ON" if self.options.build_tests else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.build_tests:
            cmake.ctest()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if not self.options.shared:
            # 上游 CMake 总是构建 shared_lib；静态模式下包内只保留 .a
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"),
               recursive=False)

    def package_info(self):
        self.cpp_info.libs = ["nuraft"]
        self.cpp_info.system_libs = ["dl", "z", "pthread"]
