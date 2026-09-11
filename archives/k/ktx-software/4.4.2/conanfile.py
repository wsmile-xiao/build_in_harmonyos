#!/usr/bin/env python3
"""Conan recipe for KTX-Software (Khronos Texture) — CMake build.

KTX is a lightweight container for textures for OpenGL, Vulkan and other GPU APIs.
This recipe builds libktx (static), libktx_read, and command-line tools.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KtxSoftwareConan(ConanFile):
    name = "ktx-software"
    version = "4.4.2"
    description = "Khronos KTX library and tools for reading/writing KTX texture files"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/KTX-Software"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "tools": [True, False],
        "gl_upload": [True, False],
        "vk_upload": [True, False],
    }
    default_options = {
        "shared": False,
        "tools": True,
        "gl_upload": False,
        "vk_upload": False,
    }

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["KTX_FEATURE_TESTS"] = "OFF"
        tc.variables["KTX_FEATURE_LOADTEST_APPS"] = "OFF"
        tc.variables["KTX_FEATURE_DOC"] = "OFF"
        tc.variables["KTX_FEATURE_JNI"] = "OFF"
        tc.variables["KTX_FEATURE_PY"] = "OFF"
        tc.variables["KTX_FEATURE_TOOLS"] = "ON" if self.options.tools else "OFF"
        tc.variables["KTX_FEATURE_GL_UPLOAD"] = "ON" if self.options.gl_upload else "OFF"
        tc.variables["KTX_FEATURE_VK_UPLOAD"] = "ON" if self.options.vk_upload else "OFF"
        tc.variables["KTX_GIT_VERSION_FULL"] = "v{}".format(self.version)
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
        self.cpp_info.libs = ["ktx"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++", "dl", "pthread", "m"]
        if self.options.tools:
            self.cpp_info.bindirs = ["bin"]
