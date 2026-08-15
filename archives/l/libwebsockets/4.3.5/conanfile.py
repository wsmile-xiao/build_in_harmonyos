#!/usr/bin/env python3
"""Conan recipe for libwebsockets 4.3.5 (OpenHarmony PC)."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LibwebsocketsConan(ConanFile):
    name = "libwebsockets"
    version = "4.3.5"
    description = (
        "A lightweight, pure C library for websockets and web server "
        "implementation, used by ttyd and other realtime web consumers"
    )
    license = "MIT"
    homepage = "https://libwebsockets.org"
    url = "https://github.com/warmcat/libwebsockets"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libwebsockets is validated only for Linux and OHOS, "
                f"not {self.settings.os}"
            )

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        openssl_pkg = self.dependencies["openssl"]
        openssl_root = openssl_pkg.package_folder.replace("\\", "/")
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # libwebsockets 4.3.5 用传统 OPENSSL_INCLUDE_DIRS/OPENSSL_LIBRARIES
        # 变量探测 OpenSSL，而 CMakeDeps 只提供 openssl::openssl target，
        # 因此显式把依赖包的头文件/库路径传给 LWS_OPENSSL_* cache 变量。
        tc.variables["LWS_OPENSSL_INCLUDE_DIRS"] = os.path.join(
            openssl_root, "include"
        ).replace("\\", "/")
        tc.variables["LWS_OPENSSL_LIBRARIES"] = ";".join(
            os.path.join(openssl_root, "lib", lib)
            for lib in ("libssl.a", "libcrypto.a")
        )
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["LWS_WITH_SSL"] = "ON"
        tc.variables["LWS_WITH_HTTP2"] = "ON"
        tc.variables["LWS_WITHOUT_TESTAPPS"] = "ON"
        tc.variables["LWS_WITH_MINIMAL_EXAMPLES"] = "OFF"
        tc.variables["LWS_WITHOUT_EXTENSIONS"] = "ON"
        tc.variables["LWS_WITH_NETLINK"] = "ON"
        tc.variables["LWS_WITH_IPV6"] = "ON"
        tc.variables["LWS_WITH_CLIENT"] = "ON"
        tc.variables["LWS_WITH_SERVER"] = "ON"
        if not self.options.shared and self.settings.os != "Windows":
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
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
        self.cpp_info.set_property("pkg_config_name", "libwebsockets")
        # libwebsockets.h 会 #include <openssl/ssl.h>，消费者编译时必须拿到
        # OpenSSL 头文件与库，因此无论 shared/static 都传递 openssl 依赖。
        self.cpp_info.requires = ["openssl::openssl"]
        self.cpp_info.libs = ["websockets"] if self.options.shared else ["websockets_static"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["ssl", "crypto"]  # libwebsockets_static needs OpenSSL
