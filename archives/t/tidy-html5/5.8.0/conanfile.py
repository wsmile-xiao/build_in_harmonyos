#!/usr/bin/env python3
"""Conan recipe — tidy-html5 5.8.0 (CMake)"""
import os, glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TidyHtml5Conan(ConanFile):
    name = "tidy-html5"
    version = "5.8.0"
    description = "HTML Tidy, an HTML checker and reformatter（HTML 检查格式化库，CMake 构建，鸿蒙 PC 适配）"
    license = "HTML-TIDY"
    homepage = "https://github.com/htacg/tidy-html5"
    url = ""
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
        tc.variables["BUILD_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG_SEP"] = ":"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{lang}_FLAG"] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS" and self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            sos = glob.glob(os.path.join(libdir, "**", "*.so*"), recursive=True)
            # Tool paths are read from environment with sensible defaults so the
            # recipe works across CI workers and local dev setups. Missing tools
            # are reported rather than silently swallowed.
            objcopy = os.environ.get("LLVM_OBJCOPY", "llvm-objcopy")
            signer = os.environ.get("BINARY_SIGN_TOOL", "binary-sign-tool")
            for so in sos:
                if os.path.islink(so):
                    continue
                self.run(f'{objcopy} --remove-section .codesign "{so}"')
                self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["tidy"]
        self.cpp_info.set_property("cmake_file_name", "Tidy")
        self.cpp_info.set_property("cmake_target_name", "Tidy::Tidy")
        self.cpp_info.set_property("pkg_config_name", "tidy")
