#!/usr/bin/env python3
"""Conan recipe — libcec 8.1.7 (Pulse-Eight libCEC).

控制 CEC 能力 HDMI 设备（电视/功放）的 C/C++ 库，同时构建 CLI:
cec-client / cecc-client（因此软件级 commands.json 由 L0k/R38 校验）。
构建系统: CMake（根 CMakeLists.txt）。

OHOS 适配点:
  - DISABLE_BUILDINFO=ON：设备无 whoami，SetBuildInfo.cmake 的 string(STRIP)
    BUILD_USER 会因空值报 "requires two arguments" 导致 configure 失败；
    关闭内嵌 git/日期/用户/host 的构建信息即规避（上游官方可复现构建选项）。
  - CMAKE_SYSTEM_NAME=Linux：沿用项目 json-c 同款做法，让 CMake 按 Linux
    约定生成带 SONAME 的版本化共享库（libcec.so.8 → libcec.so.8.1.7），
    cec-client/cecc-client 的 cecloader 运行期按 libcec.so.8 动态加载。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibcecConan(ConanFile):
    name = "libcec"
    version = "8.1.7"
    description = "Pulse-Eight libCEC - control CEC-capable HDMI devices via Pulse-Eight USB-CEC and SoC-native CEC"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Pulse-Eight/libcec"
    url = "https://github.com/Pulse-Eight/libcec"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        # OHOS 无 whoami → 必须关闭上游构建信息注入（见模块 docstring）
        tc.variables["DISABLE_BUILDINFO"] = "ON"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
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
        self.cpp_info.libs = ["cec"]
        self.cpp_info.set_property("cmake_file_name", "libcec")
        self.cpp_info.set_property("cmake_target_name", "libcec::libcec")
        self.cpp_info.set_property("pkg_config_name", "libcec")
        # cec-client / cecc-client 等 CLI 安装到 bin/（L0k 依据 bindirs 要求 commands.json）
        self.cpp_info.bindirs = ["bin"]