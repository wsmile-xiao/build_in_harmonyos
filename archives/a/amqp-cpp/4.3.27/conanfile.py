#!/usr/bin/env python3
"""Conan recipe — amqp-cpp 4.3.27 (CMake, static library).

AMQP-CPP is a C++17 RabbitMQ client library. The core library is
IO-layer agnostic and has NO external dependencies: it only needs the
compiler. The optional Linux TCP module (AMQP-CPP_LINUX_TCP) pulls in
OpenSSL and is not part of this build; consumers plug in their own
event loop / socket layer instead.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AmqpcppConan(ConanFile):
    name = "amqp-cpp"
    version = "4.3.27"
    description = "C++ library for communicating with a RabbitMQ message broker"
    license = "MIT"
    homepage = "https://github.com/CopernicaMarketingSoftware/AMQP-CPP"
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

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform module; force the Linux branch
        # so upstream selects the Linux platform files (same as ableton-link).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["AMQP-CPP_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        # The Linux TCP module requires OpenSSL; the core library does not.
        tc.variables["AMQP-CPP_LINUX_TCP"] = "OFF"
        tc.variables["AMQP-CPP_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists.txt declares cmake_minimum_required(3.4); CMake
        # >= 3.5 dropped compatibility with < 3.5, so pass the policy minimum
        # on the configure command line (toolchain cache var is not honored
        # early enough for the cmake_minimum_required check).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["amqpcpp"]
