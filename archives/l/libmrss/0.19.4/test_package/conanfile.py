#!/usr/bin/env python3
"""Conan test_package — libmrss 0.19.4 (RSS/Atom feed API)

消费者验证：必须使用 Conan 安装后的公共头文件（include/mrss.h）与库
（lib/libmrss.so），真实调用公开 API 完成内联 RSS fixture 的创建、
解析、字段读取、保存与非法 XML 拒绝。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibmrssTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libmrss 公共 API 运行期传递依赖：libmrss.so NEEDED
        # libnxml.so.0 + libcurl.so；mrss_parse_url 系列需要 curl。
        self.requires("libnxml/0.18.5")
        self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.build()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libmrss")
        # conanrun 聚合 env 未携带 libnxml/curl 的 libdir（profile 无
        # 全局 buildenv）——包内 .so 已按鸿蒙规范清空 RUNPATH，运行
        # 查找路径需要显式给到（含被测包自身 libdir）。direct_host
        # 完整 ref 写法（L0o）。
        env = Environment()
        tested = self.dependencies.direct_host["libmrss/0.19.4"]
        env.prepend_path("LD_LIBRARY_PATH",
                         os.path.join(tested.package_folder, "lib"))
        for ref in ("libnxml/0.18.5", "curl/8.15.0"):
            dep = self.dependencies.direct_host[ref]
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", str(libdir))
        with env.vars(self).apply():
            # env="conanrun" 会重置 PATH；bin_path 用绝对路径，且
            # LD_LIBRARY_PATH 由上方 Environment 显式给全
            self.run(bin_path)
