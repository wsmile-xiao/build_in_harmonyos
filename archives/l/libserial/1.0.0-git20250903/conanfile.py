#!/usr/bin/env python3
"""Conan recipe for LibSerial 1.0.0 (git snapshot 2025-09-03)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibSerialConan(ConanFile):
    name = "libserial"
    version = "1.0.0-git20250903"
    description = "Cross-platform C++ serial port library (SerialPort/SerialStream APIs)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/crayzeewulf/LibSerial"
    url = "https://github.com/crayzeewulf/LibSerial"
    topics = ("serial", "serial-port", "termios", "tty")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # 上游核心库只依赖 C++17 标准库与 POSIX threads；测试目标额外需要
        # Boost.Test 与构建期下载 googletest，且 gtest 套件硬编码物理串口
        # /dev/ttyUSB0、/dev/ttyUSB1，OHOS 设备与 CI 均无该硬件，整体关闭。
        toolchain.variables["LIBSERIAL_ENABLE_TESTING"] = False
        toolchain.variables["LIBSERIAL_BUILD_EXAMPLES"] = False
        # Python SIP 绑定需要 PythonLibs/SIP，Doxygen 文档需要 doxygen，
        # 均非库本体所需，关闭以保持配方自包含。
        toolchain.variables["LIBSERIAL_PYTHON_ENABLE"] = False
        toolchain.variables["LIBSERIAL_BUILD_DOCS"] = False
        toolchain.variables["INSTALL_STATIC"] = True
        toolchain.variables["INSTALL_SHARED"] = bool(self.options.shared)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游以 PREFIX "" + OUTPUT_NAME libserial 产出 libserial.a/libserial.so，
        # 链接名即 serial；头文件安装在 include/libserial/ 下，以
        # #include <libserial/SerialPort.h> 方式使用。
        self.cpp_info.libs = ["serial"]
        self.cpp_info.set_property("cmake_file_name", "LibSerial")
        self.cpp_info.set_property("cmake_target_name", "LibSerial::LibSerial")
        self.cpp_info.set_property("pkg_config_name", "libserial")
