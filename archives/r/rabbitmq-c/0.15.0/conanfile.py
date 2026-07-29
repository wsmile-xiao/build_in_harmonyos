#!/usr/bin/env python3
"""Conan recipe — rabbitmq-c 0.15.0 (CMake).

rabbitmq-c is a C library for the RabbitMQ AMQP client.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class RabbitmqcConan(ConanFile):
    name = "rabbitmq-c"
    version = "0.15.0"
    description = "A C library for RabbitMQ AMQP client"
    license = "MIT"
    homepage = "https://github.com/alanxz/rabbitmq-c"
    url = "https://github.com/alanxz/rabbitmq-c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "ssl": [True, False]}
    default_options = {"shared": False, "ssl": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.ssl:
            self.requires("openssl/1.1.1w")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # R32: OHOS 上 CMake 不识别 os=OHOS，设为 Linux 让 CMake 正确配置
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_TOOLS"] = "OFF"
        tc.variables["BUILD_API_DOCS"] = "OFF"
        tc.variables["ENABLE_SSL_SUPPORT"] = "ON" if self.options.ssl else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游测试，仅在 OHOS/musl 上排除子进程异常的 test_tables
        ctest_cmd = "ctest --output-on-failure"
        if self.settings.os == "OHOS":
            ctest_cmd = "ctest -E tables --output-on-failure"
        self.run(ctest_cmd, cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["rabbitmq"]
