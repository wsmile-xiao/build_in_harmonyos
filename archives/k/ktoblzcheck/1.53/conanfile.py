#!/usr/bin/env python3
"""Conan recipe for ktoblzcheck 1.53 — German bank account number check.

CMake 构建，install 规则完整（库/头/工具/pkgconfig/cmake-config/bankdata）。
适配点：
1) ENABLE_BANKDATA_DOWNLOAD=OFF：默认 ON 会按当天日期联网下载银行数据
   （bundesbank.de，CI/本地均不可达），改为使用仓库自带的
   src/bankdata/bankdata_20200420.txt。
2) 禁用 python 绑定：OHOS 无 Python 开发环境（交叉编译 python 扩展不可行），
   patch 顶层 FindPython3 只要求 Interpreter 组件（避免 Development 缺失时
   fallback 到 REQUIRED Python2 导致 configure 失败），并跳过 src/python 子目录。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, patch


class KtoblzcheckConan(ConanFile):
    name = "ktoblzcheck"
    version = "1.53"
    description = "Library and tools to check German bank account numbers"
    license = "LGPL-2.1-or-later"
    homepage = "https://ktoblzcheck.sourceforge.net/"
    url = "https://sourceforge.net/projects/ktoblzcheck/"
    topics = ("banking", "germany", "blz", "iban")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        patch(self, patch_file="patches/0001-disable-python.patch")

    def generate(self):
        tc = CMakeToolchain(self)
        # 使用仓库自带 bankdata 文件，禁止联网下载银行数据
        tc.variables["ENABLE_BANKDATA_DOWNLOAD"] = "OFF"
        # 上游 cmake_minimum_required(3.0) 与新版 CMake 不兼容
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ktoblzcheck"]
        if self.settings.os in ("Linux", "Android", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
