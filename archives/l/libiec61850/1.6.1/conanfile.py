#!/usr/bin/env python3
"""Conan recipe - libiec61850 1.6.1 (CMake).

libiec61850 是 IEC 61850（MMS/GOOSE/Sampled Values）协议栈的开源 C 实现，
产物为静态/动态库 libiec61850 + HAL 层库 hal。构建系统为 CMake，无外部依赖。

适配要点：
1. 设备 `uname -s` 返回 HarmonyOS，CMake 无对应 platform module
   （"System is unknown to cmake, create: Platform/HarmonyOS"），导致
   `IF(UNIX)` 分支不成立、`libhal_SRCS` 为空 → `add_library` 报
   "No SOURCES given to target"。按知识条目 E092 在 OHOS 下显式置
   CMAKE_SYSTEM_NAME=Linux（HarmonyOS 基于 Linux 内核）。
2. 上游测试面在 examples/**（无 tests/ 目录、无有效 ctest 注册），
   故构建期保留 BUILD_EXAMPLES=ON 作为上游用例的编译+链接验证。
3. third_party/{mbedtls,sqlite,winpcap} 在官方发布 tarball 中只有 README
   （组件内容不随 tag 归档），上游据此自动关闭 TLS / R-GOOSE / R-SMV /
   sqlite-log 相关目标，属上游自身门控，不引入额外依赖。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
    rm,
)


class Libiec61850Conan(ConanFile):
    name = "libiec61850"
    version = "1.6.1"
    description = "An open-source library for the IEC 61850 protocols (MMS/GOOSE/SV)"
    license = "LGPL-3.0"
    homepage = "https://libiec61850.com/libiec61850"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("iec61850", "mms", "goose", "sampled-values")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092：设备 uname=HarmonyOS，CMake 无该 platform module；
        # 上游 hal/src 大量 IF(UNIX) 分支依赖它（否则 add_library 无源文件）。
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 上游测试面在 examples/**（无 tests/ 目录），构建期保留作为上游用例验证。
        tc.cache_variables["BUILD_EXAMPLES"] = True
        # pyiec61850 绑定不在本包范围（上游唯一的 add_test 挂在其下）。
        tc.cache_variables["BUILD_PYTHON_BINDINGS"] = False
        tc.cache_variables["FIND_PACKAGE_DISABLE_Doxygen"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 不指定 target：同时构建 libiec61850/hal 与 examples（上游测试面）。
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING",
             src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游同时产出静态与共享两种 libiec61850，按选项只保留一种，避免消费者
        # 链接到与 options.shared 不符的产物。
        if self.options.shared:
            rm(self, pattern="libiec61850.a", folder=os.path.join(self.package_folder, "lib"))
            rm(self, pattern="libhal.a", folder=os.path.join(self.package_folder, "lib"))
            rm(self, pattern="libhal-shared.a", folder=os.path.join(self.package_folder, "lib"))
        else:
            rm(self, pattern="libiec61850.so*", folder=os.path.join(self.package_folder, "lib"))
            rm(self, pattern="libhal-shared.a", folder=os.path.join(self.package_folder, "lib"))
        # Conan 自己生成 libiec61850.pc，避免与上游 share/pkgconfig 副本冲突。
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libiec61850")
        self.cpp_info.set_property("cmake_file_name", "libiec61850")
        self.cpp_info.set_property("cmake_target_name", "libiec61850::libiec61850")
        # iec61850 依赖 hal（HAL 层为独立静态库，不编进 libiec61850.a）。
        if self.options.shared:
            self.cpp_info.libs = ["iec61850"]
        else:
            self.cpp_info.libs = ["iec61850", "hal"]
        self.cpp_info.system_libs = ["pthread", "m", "rt"]
