#!/usr/bin/env python3
"""Conan recipe for qrcodegen 1.8.0 (C++ implementation by Project Nayuki).

Upstream: https://github.com/nayuki/QR-Code-generator (tag v1.8.0, cpp/ subdir).
The upstream release tarball contains multiple language implementations; the
C++ library lives in the cpp/ subdirectory (qrcodegen.cpp + qrcodegen.hpp).
Upstream only provides a Makefile, so this recipe generates a CMakeLists.txt
in source() to integrate with the Conan CMake workflow (same approach as the
archived libqrcodegen/1.8.0 C recipe).

No external dependencies (zero-dependency pure C++11).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QrcodegenConan(ConanFile):
    name = "qrcodegen"
    version = "1.8.0"
    description = "QR Code generator library (C++ implementation by Project Nayuki), single-file C++11 library"
    license = "MIT"
    homepage = "https://www.nayuki.io/page/qr-code-generator-library"
    url = "https://github.com/nayuki/QR-Code-generator"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The tarball contains multi-language subdirs (c/, cpp/, java/, ...).
        # Promote the C++ implementation from cpp/ to the source root.
        cpp_dir = os.path.join(self.source_folder, "cpp")
        if os.path.isdir(cpp_dir):
            for f in os.listdir(cpp_dir):
                src = os.path.join(cpp_dir, f)
                dst = os.path.join(self.source_folder, f)
                if os.path.exists(dst):
                    continue
                shutil.move(src, dst)
            shutil.rmtree(cpp_dir, ignore_errors=True)
        # Upstream only provides a Makefile; generate a CMakeLists.txt so the
        # Conan CMake workflow can build and install the library.
        cmake_content = """cmake_minimum_required(VERSION 3.10)
project(qrcodegen VERSION 1.8.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(qrcodegen qrcodegen.cpp)

set_target_properties(qrcodegen PROPERTIES
    OUTPUT_NAME "qrcodegen"
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

include(GNUInstallDirs)

install(TARGETS qrcodegen
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(FILES qrcodegen.hpp
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
"""
        save(self, "CMakeLists.txt", cmake_content)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
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
            self._sign_shared_objects()

    def _sign_shared_objects(self):
        """Sign OHOS ELF shared objects with the target's native signer."""
        objcopy = os.environ.get("OHOS_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("OHOS_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for name in files:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                path = os.path.join(root, name)
                self.run('{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(objcopy, path))
                self.run('{0} sign "{1}" 2>/dev/null || true'.format(signer, path))

    def package_info(self):
        self.cpp_info.libs = ["qrcodegen"]
