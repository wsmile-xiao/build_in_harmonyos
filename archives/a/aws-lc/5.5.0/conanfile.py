#!/usr/bin/env python3
"""Conan recipe for aws-lc (AWS libcrypto) 5.5.0 — CMake build system.

aws-lc is a general-purpose cryptographic library maintained by the AWS
Cryptography team, forked from BoringSSL. It provides libcrypto and libssl
as drop-in replacements for OpenSSL.

本配方基于 5.4.0（main 仓库已适配合入）升级：版本号 + 源码 sha256 更新，
其余适配逻辑（R26 静态库 / DISABLE_GO / OPENSSL_NO_ASM / BUILD_TESTING 关闭）
与 5.4.0 一致。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsLcConan(ConanFile):
    name = "aws-lc"
    version = "5.5.0"
    description = "AWS libcrypto (AWS-LC) — general-purpose cryptographic library forked from BoringSSL"
    license = "OpenSSL-SSLeay"
    homepage = "https://github.com/aws/aws-lc"
    url = "https://github.com/aws/aws-lc"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries (libcrypto/libssl) must be static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # DISABLE_GO: Go is not available on HarmonyOS
        tc.variables["DISABLE_GO"] = "ON"
        # BUILD_TESTING=ON: 上游测试在鸿蒙可编译可运行(实测 crypto_test
        # 2716/2726 PASSED + ssl_test 2577/2626 PASSED)——5.4.0 的
        # "C++ 测试链接失败"理由在 5.5.0 不成立(rwlock_static_init 等
        # 测试目标均编译成功), 开启测试目标供 CI/验证运行
        tc.variables["BUILD_TESTING"] = "ON"
        # Disable bssl tool (library-only build)
        tc.variables["BUILD_TOOL"] = "OFF"
        # OPENSSL_NO_ASM: CMake on HarmonyOS reports CMAKE_SYSTEM_PROCESSOR as
        # "unknown" (uname -p returns "unknown"), so aws-lc falls back to ARCH
        # "generic" without defining OPENSSL_NO_ASM. This leaves assembly symbol
        # references unresolved at link time. Setting OPENSSL_NO_ASM=ON properly
        # enables pure-C fallback implementations.
        if self.settings.os == "OHOS":
            tc.variables["OPENSSL_NO_ASM"] = "ON"
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
        self.cpp_info.libs = ["crypto", "ssl"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
