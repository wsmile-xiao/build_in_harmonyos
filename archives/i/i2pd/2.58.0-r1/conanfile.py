#!/usr/bin/env python3
"""Conan recipe for i2pd 2.58.0-r1 (upstream tag 2.58.0)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class I2pdConan(ConanFile):
    name = "i2pd"
    version = "2.58.0-r1"
    description = "Full-featured C++ implementation of the I2P anonymous network router"
    license = "BSD-3-Clause"
    homepage = "https://i2pd.website/"
    url = "https://github.com/PurpleI2P/i2pd"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # boost/1.84.0 is not published in the ohpcd registry; 1.90.0.3 is the
        # published CMake build that provides the system/filesystem/program_options
        # components required by upstream build/CMakeLists.txt.
        self.requires("boost/1.90.0.3")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        zlib = self.dependencies["zlib"].cpp_info
        zlib.set_property("cmake_file_name", "ZLIB")
        zlib.set_property("cmake_target_name", "ZLIB::ZLIB")

        openssl = self.dependencies["openssl"].cpp_info
        openssl.set_property("cmake_file_name", "OpenSSL")
        openssl.set_property("cmake_additional_variables_prefixes", ["OPENSSL"])
        package_folder = self.dependencies["openssl"].package_folder
        include_dirs = [os.path.join(package_folder, path) for path in openssl.includedirs]
        lib_dirs = [os.path.join(package_folder, path) for path in openssl.libdirs]
        system_libs = list(openssl.system_libs)
        openssl.libs = []
        openssl.system_libs = []

        crypto = openssl.components["Crypto"]
        crypto.libs = ["crypto"]
        crypto.system_libs = system_libs
        crypto.includedirs = include_dirs
        crypto.libdirs = lib_dirs
        crypto.bindirs = []
        crypto.resdirs = []
        crypto.frameworkdirs = []
        crypto.builddirs = []
        crypto.set_property("cmake_target_name", "OpenSSL::Crypto")

        ssl = openssl.components["SSL"]
        ssl.libs = ["ssl"]
        ssl.includedirs = include_dirs
        ssl.libdirs = lib_dirs
        ssl.bindirs = []
        ssl.resdirs = []
        ssl.frameworkdirs = []
        ssl.builddirs = []
        ssl.requires = ["Crypto"]
        ssl.set_property("cmake_target_name", "OpenSSL::SSL")

        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["UNIX"] = True
        tc.variables["WITH_BINARY"] = True
        tc.variables["WITH_LIBRARY"] = True
        tc.variables["WITH_STATIC"] = False
        tc.variables["WITH_UPNP"] = False
        tc.variables["WITH_GIT_VERSION"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="build")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "i2pd.conf", src=os.path.join(self.source_folder, "contrib"),
             dst=os.path.join(self.package_folder, "etc", "i2pd"))
        copy(self, "tunnels.conf", src=os.path.join(self.source_folder, "contrib"),
             dst=os.path.join(self.package_folder, "etc", "i2pd"))
        copy(self, "subscriptions.txt", src=os.path.join(self.source_folder, "contrib"),
             dst=os.path.join(self.package_folder, "etc", "i2pd"))
        copy(self, "*", src=os.path.join(self.source_folder, "contrib", "certificates"),
             dst=os.path.join(self.package_folder, "share", "i2pd", "certificates"))

    def package_info(self):
        self.cpp_info.libs = ["i2pdclient", "i2pd", "i2pdlang"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
