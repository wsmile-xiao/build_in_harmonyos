#!/usr/bin/env python3
"""Conan recipe — ssldump 1.9 (CMake).

ssldump is an SSL/TLS traffic analyzer for network security monitoring.
Build system: CMake with custom FindXXX.cmake modules.
Depends: openssl, libpcap, libnet, json-c.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


def _sdk_llvm_libdir():
    """Locate OHOS SDK llvm/lib dir containing libxml2.so.16 for lld."""
    for root in ("/data/service/hnp", "/usr"):
        for f in glob.glob(os.path.join(root, "**", "ohos-sdk*", "ohos", "native", "llvm", "lib", "libxml2.so.16"), recursive=True):
            return os.path.dirname(f)
    return None


class SsldumpConan(ConanFile):
    name = "ssldump"
    version = "1.9"
    description = "SSL/TLS traffic analyzer for network security monitoring"
    license = "OpenSSL"
    homepage = "https://github.com/adulau/ssldump"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ssldump supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("libpcap/1.10.6")
        self.requires("libnet/1.2")
        self.requires("json-c/0.18")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        sdk_llvm = _sdk_llvm_libdir()
        if sdk_llvm:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = sdk_llvm + ((":" + old) if old else "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
