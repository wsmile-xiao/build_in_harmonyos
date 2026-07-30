#!/usr/bin/env python3
"""Conan recipe — pam-reattach 1.3.

pam-reattach is a macOS PAM helper for reattaching to the user's Aqua
bootstrap namespace via XPC / Mach bootstrap port APIs.  These APIs are
Darwin-specific and have no equivalent on OpenHarmony.  The OHOS build
preserves the reattach_aqua() API surface but returns ENOTSUP at runtime
(stub).  PAM module and CLI are disabled because they also depend on the
Aqua session concept that does not exist on OHOS.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PamReattachConan(ConanFile):
    name = "pam-reattach"
    version = "1.3"
    description = "PAM module for reattaching to the user's GUI Aqua session"
    license = "MIT"
    homepage = "https://github.com/fabianishere/pam_reattach"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["ENABLE_PAM"] = False
        tc.cache_variables["ENABLE_CLI"] = False
        # CMAKE_SYSTEM_NAME 由 Conan toolchain 根据 settings.os 自动设置
        # （os=OHOS → CMAKE_SYSTEM_NAME=HarmonyOS），无需手工指定。
        # 通过 settings.os 检测 OHOS 平台，供源码条件编译使用。
        if self.settings.os == "OHOS":
            tc.preprocessor_definitions["OHOS_PLATFORM"] = "1"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["reattach"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "reattach")
        self.cpp_info.set_property("cmake_target_name", "reattach::reattach")
