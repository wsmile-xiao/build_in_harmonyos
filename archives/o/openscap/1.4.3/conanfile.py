#!/usr/bin/env python3
"""Conan recipe for OpenSCAP 1.4.3 - CMake build system.

OpenSCAP is an open-source SCAP (Security Content Automation Protocol) framework.
This recipe builds the openscap library and oscap utility for OpenHarmony.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenscapConan(ConanFile):
    name = "openscap"
    version = "1.4.3"
    description = "OpenSCAP - Open Source Security Compliance Solution"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.openscap.io"
    url = "https://github.com/OpenSCAP/openscap"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "enable_sha1": [True, False],
        "enable_md5": [True, False],
    }
    default_options = {
        "shared": True,
        "enable_sha1": True,
        "enable_md5": True,
    }

    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.2")
        self.requires("xmlsec1/1.3.11")
        self.requires("openssl/3.5.6")
        self.requires("pcre2/10.47")
        self.requires("libgcrypt/1.12.2")
        self.requires("bzip2/1.0.8")
        self.requires("libcurl/8.5.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_PROBES_LINUX"] = "OFF"
        tc.cache_variables["ENABLE_PROBES_UNIX"] = "ON"
        tc.cache_variables["ENABLE_TESTS"] = "OFF"
        tc.cache_variables["ENABLE_DOCS"] = "OFF"
        tc.cache_variables["ENABLE_SCE"] = "OFF"
        tc.cache_variables["ENABLE_OSCAP_UTIL_DOCKER"] = "OFF"
        tc.cache_variables["ENABLE_OSCAP_UTIL_AS_RPM"] = "OFF"
        tc.cache_variables["ENABLE_OSCAP_UTIL_SSH"] = "OFF"
        tc.cache_variables["ENABLE_OSCAP_UTIL_VM"] = "OFF"
        tc.cache_variables["ENABLE_OSCAP_UTIL_PODMAN"] = "OFF"
        tc.cache_variables["ENABLE_OSCAP_UTIL_IM"] = "OFF"
        tc.cache_variables["ENABLE_OSCAP_UTIL_CHROOT"] = "OFF"
        tc.cache_variables["ENABLE_PYTHON3"] = "OFF"
        tc.cache_variables["ENABLE_PERL"] = "OFF"
        tc.cache_variables["OPENSCAP_ENABLE_SHA1"] = "ON" if self.options.enable_sha1 else "OFF"
        tc.cache_variables["OPENSCAP_ENABLE_MD5"] = "ON" if self.options.enable_md5 else "OFF"
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
        self.cpp_info.libs = ["openscap"]
        self.cpp_info.set_property("cmake_file_name", "openscap")
        self.cpp_info.set_property("pkg_config_name", "libopenscap")
