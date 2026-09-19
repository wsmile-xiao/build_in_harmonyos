#!/usr/bin/env python3
"""Conan recipe for libcxx-serial 1.2.1 — cross-platform C++ serial port library.

Upstream is wjwwood/serial (Debian source package name: libcxx-serial).
The release tarball's CMakeLists.txt requires ROS catkin
(find_package(catkin REQUIRED)); patch 0001 replaces it with a plain CMake
project that compiles the unix implementation (serial.cc + impl/unix.cc +
list_ports_linux.cc) and installs lib/include with standard destinations.
The serial_example executable is not built: this is a library-only package,
so no commands.json is declared (R38).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibcxxSerialConan(ConanFile):
    name = "libcxx-serial"
    version = "1.2.1"
    description = "Cross-platform C++ serial port (RS-232) library, upstream wjwwood/serial"
    license = "MIT"
    homepage = "https://github.com/wjwwood/serial"
    url = ""  # CI fills this
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: accept the platform family, do not compare against Linux only
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcxx-serial builds the unix implementation; supported on Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "serial")
        self.cpp_info.set_property("cmake_target_name", "serial::serial")
        self.cpp_info.libs = ["serial"]
