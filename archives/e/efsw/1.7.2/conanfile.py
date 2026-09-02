#!/usr/bin/env python3
"""Conan recipe — efsw 1.7.2 (CMake file/folder watching library).

efsw (Entropia File System Watcher) 是跨平台文件/目录监视 C/C++ 库。
本机 OHOS aarch64 走 posix + inotify 后端（CMakeLists 已为 OHOS/HarmonyOS
扩展 inotify 后端匹配，见 patches/）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class EfswConan(ConanFile):
    name = "efsw"
    version = "1.7.2"
    description = "Cross-platform file system watcher (C/C++)"
    license = "MIT"
    homepage = "https://github.com/SpartanJ/efsw"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "efsw 只支持 Linux/OHOS，当前: {}".format(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092 模式: CMake 无法识别 OHOS 目标平台，映射为 Linux
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # 作为 Conan 依赖构建时上游默认 EFSW_INSTALL=OFF（非主项目），必须强制安装
        tc.cache_variables["ESFW_INSTALL"] = True
        tc.cache_variables["BUILD_TEST_APP"] = False
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
        # 上游 export target: efsw::efsw（install(EXPORT efswExport ...)）
        self.cpp_info.set_property("cmake_file_name", "efsw")
        self.cpp_info.set_property("cmake_target_name", "efsw::efsw")
        self.cpp_info.libs = ["efsw"]
        # efsw 为 C++ 库，静态链接时消费者需 C++ 运行时与线程库
        self.cpp_info.system_libs = ["c++", "pthread"]
