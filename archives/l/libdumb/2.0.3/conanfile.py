#!/usr/bin/env python3
"""Conan recipe — libdumb 2.0.3 (CMake, OHOS).

libdumb = Dynamic Universal Music Bibliotheque(IT/XM/S3M/MOD 解码,纯 C,零外部依赖)。
上游 katajakasa 仓库已死,de facto 维护 fork = kode54/dumb(CMake)。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class LibdumbConan(ConanFile):
    name = "libdumb"
    version = "2.0.3"
    description = "libdumb — Dynamic Universal Music Bibliotheque (IT/XM/S3M/MOD tracker decoding)"
    license = "Unlicense"
    homepage = "https://github.com/kode54/dumb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # 仅 libc/libm;allegro4 支持与 examples 关闭后零第三方
        pass

    def source(self):
        get(self, **self.conan_data["sources"]["2.0.3"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_ALLEGRO4"] = "OFF"
        # aarch64 无 x86 SSE(上游 check_c_compiler_flag 会自动跳过,显式关更稳)
        tc.cache_variables["USE_SSE"] = "OFF"
        tc.cache_variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # LICENSE 由 CMake install 到 share/licenses?上游未装,显式补
        import shutil
        lic = os.path.join(self.package_folder, "licenses")
        os.makedirs(lic, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "LICENSE"),
                    os.path.join(lic, "LICENSE"))

    def package_info(self):
        self.cpp_info.libs = ["dumb"]
        self.cpp_info.set_property("cmake_file_name", "libdumb")
        self.cpp_info.set_property("cmake_target_name", "libdumb::dumb")
        self.cpp_info.set_property("pkg_config_name", "dumb")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
