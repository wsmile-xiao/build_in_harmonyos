#!/usr/bin/env python3
"""Conan recipe — platform_folders 4.2.0 (CMake).

platform_folders 是一个用于查询各平台"特殊目录"的小型 C++11 库：
XDG 目录（DataHome/ConfigHome/CacheDir/StateDir）、Documents/Desktop/
Download/Music 等用户目录，以及 Windows/Apple 平台对应目录。
单 .cpp + 单头文件，零第三方依赖；OHOS 走非 Windows/非 Apple 的 XDG/Linux 分支。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class PlatformFoldersConan(ConanFile):
    name = "platform_folders"
    version = "4.2.0"
    description = "A C++ library to look for special directories like 'My Documents' and XDG folders"
    license = "MIT"
    homepage = "https://github.com/sago007/PlatformFolders"
    url = ""  # CI fills this
    topics = ("directories", "xdg", "special-folders", "cpp11")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: OHOS 走 CMakeToolchain generic_system 显式映射（与本仓 gcem 等一致）
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = str(self.settings.os)
            if self.settings.os == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 上游 cmake_minimum_required(VERSION 3.1)，CMake 4 拒绝 min<3.5 的项目
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["PLATFORMFOLDERS_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 层1 上游官方测试（16 个 ctest 用例，值非空断言，CI worker=OHOS PC currentUser）
        tc.variables["PLATFORMFOLDERS_BUILD_TESTING"] = "ON"
        tc.variables["PLATFORMFOLDERS_ENABLE_INSTALL"] = "ON"
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON" if self.options.fPIC else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 层1 上游官方测试：test/CMakeLists.txt _def_test 注册 16 个 ctest 用例
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游 install(EXPORT) 以 NAMESPACE sago:: 导出 platform_foldersConfig
        self.cpp_info.set_property("cmake_file_name", "platform_folders")
        self.cpp_info.set_property("cmake_target_name", "sago::platform_folders")
        self.cpp_info.libs = ["platform_folders"]
