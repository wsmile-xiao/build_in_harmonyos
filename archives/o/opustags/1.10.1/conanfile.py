#!/usr/bin/env python3
"""Conan recipe — opustags 1.10.1 (Ogg Opus 标签读写工具, CMake, C++20).

CLI 工具交付:上游唯一外部依赖是 libogg(Ogg 容器解析,CMake 用
pkg_check_modules(OGG REQUIRED ogg) 探测),由制品仓 ogg/1.1.1 提供
(pkg_config_name=ogg);Iconv 用 musl 内建(FindIconv 命中 libc)。
CMake >= 3.11 + C++20,OHOS clang 15 直接支持。不做 strip(llvm-strip
产物被平台拒绝,yices 2.7.0 先例);交付二进制不做签名(平台 CI 侧
exec 环境自处理,tidy/jpnevulator 先例)。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import apply_conandata_patches, copy, get


class OpustagsConan(ConanFile):
    name = "opustags"
    version = "1.10.1"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def requirements(self):
        # CMakeLists.txt:18 pkg_check_modules(OGG REQUIRED ogg)
        self.requires("ogg/1.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # pkg_check_modules 需要 pkg-config 看到 conan 生成的 ogg.pc
        PkgConfigDeps(self).generate()
        import os
        os.environ["PKG_CONFIG_PATH"] = self.generators_folder + ":" + os.environ.get("PKG_CONFIG_PATH", "")
        tc = CMakeToolchain(self)
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
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define_path("PATH", bindir)
