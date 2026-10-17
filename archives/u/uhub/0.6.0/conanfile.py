#!/usr/bin/env python3
"""Conan recipe — uhub 0.6.0 (C, CMake).

OHOS 适配三处要点：
1. 上游 CMakeLists 走 MODULE 模式找依赖（OPENSSL_INCLUDE_DIR / SQLite::SQLite3），
   而 CMakeDeps 默认 config 模式既不生成 openssl 目标、也不填 OPENSSL_INCLUDE_DIR；
   这里关掉其自动生成文件，改用工具链变量把两个依赖钉到 conan 包内实际路径。
2. 真机上 CMake 主机探测得到 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 没有该平台模块，
   UNIX 变量为假 → 上游 if(UNIX) 分支（install 规则、pthread 链接、uhub-admin）被静默跳过；
   显式钉为 Linux（本仓 afmize 等配方的既有做法）。
3. OHOS libc 未提供 pthread_cancel()（头文件无声明、libc.so 无该符号），
   patches/0002 用 SIGUSR1 + pthread_exit() 实现等价的中断语义。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class UhubConan(ConanFile):
    name = "uhub"
    version = "0.6.0"
    description = "Tiny, high performance ADC p2p connection hub"
    license = "GPL-3.0-only"
    url = "https://github.com/janvidar/uhub"
    homepage = "https://github.com/janvidar/uhub"
    topics = ("adc", "p2p", "hub", "direct-connect")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("sqlite3/3.53.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]
        get(self, **data, strip_root=True)

    def _dep_library(self, dep_name, lib_name):
        """返回依赖包内实际存在的库文件绝对路径（本 profile 下为静态库）。"""
        pkg_folder = self.dependencies[dep_name].package_folder.replace("\\", "/")
        for suffix in (".a", ".so"):
            candidate = os.path.join(pkg_folder, "lib", "lib" + lib_name + suffix)
            if os.path.exists(candidate):
                return candidate
        return os.path.join(pkg_folder, "lib", "lib" + lib_name + ".a")

    def generate(self):
        deps = CMakeDeps(self)
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            openssl_folder = self.dependencies["openssl"].package_folder.replace("\\", "/")
            sqlite3_folder = self.dependencies["sqlite3"].package_folder.replace("\\", "/")
            tc.variables["OPENSSL_ROOT_DIR"] = openssl_folder
            tc.variables["OPENSSL_INCLUDE_DIR"] = os.path.join(openssl_folder, "include")
            tc.variables["OPENSSL_SSL_LIBRARY"] = self._dep_library("openssl", "ssl")
            tc.variables["OPENSSL_CRYPTO_LIBRARY"] = self._dep_library("openssl", "crypto")
            tc.variables["SQLite3_INCLUDE_DIR"] = os.path.join(sqlite3_folder, "include")
            tc.variables["SQLite3_LIBRARY"] = self._dep_library("sqlite3", "sqlite3")
            # 见文件头说明 2：让上游的 UNIX 分支在 HarmonyOS 平台名下生效
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            deps.set_property("openssl", "cmake_find_mode", "none")
            deps.set_property("sqlite3", "cmake_find_mode", "none")
        deps.generate()
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.OpenSSL", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
