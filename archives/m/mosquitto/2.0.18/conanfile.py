#!/usr/bin/env python3
"""Conan recipe for mosquitto 2.0.18 — CMake projects.

Mosquitto is an MQTT broker and client library. It produces both
shared libraries (libmosquitto, libmosquittopp) and executables
(mosquitto broker, mosquitto_pub/sub/rr/ctrl/passwd).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MosquittoConan(ConanFile):
    name = "mosquitto"
    version = "2.0.18"
    description = "Open Source MQTT broker and client library"
    license = "EPL-2.0"
    homepage = "https://mosquitto.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_tls": [True, False],
        "with_cjson": [True, False],
        "with_threading": [True, False],
    }
    default_options = {
        "shared": True,
        "with_tls": True,
        "with_cjson": True,
        "with_threading": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_tls:
            self.requires("openssl/3.5.6.1")
        if self.options.with_cjson:
            self.requires("cjson/1.7.19")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DOCUMENTATION"] = False
        tc.variables["WITH_BUNDLED_DEPS"] = True
        tc.variables["WITH_TLS"] = self.options.with_tls
        tc.variables["WITH_CJSON"] = self.options.with_cjson
        tc.variables["WITH_THREADING"] = self.options.with_threading
        tc.variables["WITH_STATIC_LIBRARIES"] = not self.options.shared
        tc.variables["WITH_UNIX_SOCKETS"] = True
        tc.variables["WITH_SOCKS"] = True
        tc.variables["WITH_BRIDGE"] = True
        tc.variables["WITH_PERSISTENCE"] = True
        tc.variables["WITH_SYS_TREE"] = True
        tc.variables["WITH_CONTROL"] = True
        tc.variables["WITH_EPOLL"] = True
        tc.variables["WITH_EC"] = True
        tc.variables["WITH_TLS_PSK"] = self.options.with_tls
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
        self.cpp_info.set_property("cmake_file_name", "mosquitto")
        self.cpp_info.libs = ["mosquitto"]
        requires = []
        if self.options.with_tls:
            requires.append("openssl::openssl")
        if self.options.with_cjson:
            requires.append("cjson::cjson")
        self.cpp_info.requires = requires
