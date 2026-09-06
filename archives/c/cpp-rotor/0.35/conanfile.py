#!/usr/bin/env python3
"""Conan recipe — cpp-rotor 0.35 (CMake project, boost dependency).

cpp-rotor: Event loop friendly C++ actor micro-framework (MIT).
Build: CMake; core library `rotor` (+ optional thread/asio/ev/wx/fltk plugins).
Dependencies: Boost (date_time/system/regex) — Boost.System header-only.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.build import check_min_cppstd


class CpprotorConan(ConanFile):
    name = "cpp-rotor"
    version = "0.35"
    description = "Event loop friendly C++ actor micro-framework"
    license = "MIT"
    homepage = "https://github.com/basiliscos/cpp-rotor"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "CMakeLists.txt", "src/*", "include/*", "cmake/*", "tests/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ROTOR_BUILD_TESTS"] = "OFF"
        tc.variables["ROTOR_BUILD_EXAMPLES"] = "OFF"
        tc.variables["ROTOR_BUILD_DOC"] = "OFF"
        tc.variables["ROTOR_BUILD_ASIO"] = "OFF"
        tc.variables["ROTOR_BUILD_EV"] = "OFF"
        tc.variables["ROTOR_BUILD_WX"] = "OFF"
        tc.variables["ROTOR_BUILD_FLTK"] = "OFF"
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
        self.cpp_info.libs = ["rotor"]
        self.cpp_info.requires = ["boost::boost_date_time", "boost::boost_system", "boost::boost_regex"]
