from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os
import shutil


class LibqrcodegenConan(ConanFile):
    name = "libqrcodegen"
    version = "1.8.0"
    description = "QR code generator library (C implementation by Project Nayuki)"
    license = "MIT"
    homepage = "https://www.nayuki.io/page/qr-code-generator-library"
    url = ""  # CI fills this

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
        # The tarball contains multi-language subdirs (c/, cpp/, java/, etc.)
        # Promote the C implementation from c/ to the source root
        c_dir = os.path.join(self.source_folder, "c")
        if os.path.isdir(c_dir):
            for f in os.listdir(c_dir):
                src = os.path.join(c_dir, f)
                dst = os.path.join(self.source_folder, f)
                if os.path.exists(dst):
                    continue
                shutil.move(src, dst)
            shutil.rmtree(c_dir, ignore_errors=True)
        # Create CMakeLists.txt (upstream only provides Makefile)
        cmake_content = """cmake_minimum_required(VERSION 3.10)
project(qrcodegen VERSION 1.8.0 LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(qrcodegen qrcodegen.c)

set_target_properties(qrcodegen PROPERTIES
    OUTPUT_NAME "qrcodegen"
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

include(GNUInstallDirs)

install(TARGETS qrcodegen
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

install(FILES qrcodegen.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# Upstream test target
add_executable(qrcodegen-test qrcodegen-test.c qrcodegen.c)
target_compile_definitions(qrcodegen-test PRIVATE QRCODEGEN_TEST)
enable_testing()
add_test(NAME qrcodegen-test COMMAND qrcodegen-test)
"""
        save(self, "CMakeLists.txt", cmake_content)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run upstream tests (521 test cases)
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["qrcodegen"]
