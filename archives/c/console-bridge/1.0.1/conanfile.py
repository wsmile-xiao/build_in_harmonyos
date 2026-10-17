#!/usr/bin/env python3
"""Conan recipe for console-bridge 1.0.1."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ConsoleBridgeConan(ConanFile):
    name = "console-bridge"
    version = "1.0.1"
    description = "Logging shim that forwards log calls to a pluggable output handler"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ros/console_bridge"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = True
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # CMake 4 在读取 toolchain 前就校验 cmake_minimum_required，必须作为
        # 命令行 cache 变量传入，普通 tc.variables 来不及生效。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游发现 wget 时会联网下载 lint 脚本；正式测试只保留 13 项功能用例。
        tc.cache_variables["WGET_EXE"] = "WGET_EXE-NOTFOUND"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        import glob

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        targets = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"),
            recursive=True,
        )
        for path in targets:
            if os.path.islink(path):
                continue
            self.run(
                f'{objcopy} --remove-section .codesign "{path}" '
                "2>/dev/null || true"
            )
            self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["console_bridge"]
        self.cpp_info.set_property("cmake_file_name", "console_bridge")
        self.cpp_info.set_property(
            "cmake_target_name", "console_bridge::console_bridge"
        )
        self.cpp_info.set_property("pkg_config_name", "console_bridge")
