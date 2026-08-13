#!/usr/bin/env python3
"""mailio 0.26.0 Conan 配方 — CMake 构建系统。

mailio 是一个跨平台 C++ 库，用于 MIME 格式以及 SMTP、POP3、IMAP 协议。
基于 C++17，依赖 Boost（date_time、regex）和 OpenSSL（SSL）。

构建方式：共享库（BUILD_SHARED_LIBS=ON），禁用测试/示例/文档。
许可证：BSL-1.0（Boost 软件许可证）
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MailioConan(ConanFile):
    name = "mailio"
    version = "0.26.0"
    description = "Cross-platform MIME library for SMTP, POP3, and IMAP protocols"
    license = "BSL-1.0"
    homepage = "https://github.com/karastojko/mailio"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0.4")
        self.requires("openssl/3.5.6")

    def validate(self):
        # R32：平台检测必须使用 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33：所有标志来自 Conan 工具链，不使用 shell 环境变量
        # CMakeDeps 生成 FindBoost.cmake 和 FindOpenSSL.cmake，
        # 使上游 CMakeLists.txt 的 find_package() 调用成功。
        deps = CMakeDeps(self)
        # 上游 CMakeLists.txt 使用 find_package("OpenSSL" COMPONENTS "SSL")
        # 和 target_link_libraries(... "OpenSSL::SSL")，但本地 OpenSSL
        # conan 配方未定义组件。通过 CMakeDeps 属性映射，使生成的
        # CMake 目标与 CMakeLists.txt 期望的名称匹配。
        deps.set_property("openssl", "cmake_file_name", "OpenSSL")
        deps.set_property("openssl", "cmake_target_name", "OpenSSL::SSL")
        deps.generate()
        tc = CMakeToolchain(self)
        # 构建共享库（默认），但尊重用户选项
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # 禁用测试、示例和文档
        tc.variables["MAILIO_BUILD_TESTS"] = False
        tc.variables["MAILIO_BUILD_EXAMPLES"] = False
        tc.variables["MAILIO_BUILD_DOCUMENTATION"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9：OHOS worker 并行约束，单任务构建
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 复制许可证文件
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mailio")
        self.cpp_info.set_property("cmake_target_name", "mailio::mailio")
        self.cpp_info.set_property("pkg_config_name", "mailio")
        self.cpp_info.libs = ["mailio"]
        self.cpp_info.includedirs = ["include"]
        # 声明传递依赖
        self.cpp_info.requires = ["boost::date_time", "boost::regex", "openssl::openssl"]
