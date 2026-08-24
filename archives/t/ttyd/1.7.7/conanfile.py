#!/usr/bin/env python3
"""Conan recipe for ttyd 1.7.7 — share your terminal over the web.

ttyd is a simple command-line tool for sharing terminal over the web,
built on libwebsockets (with libuv support) + libuv + json-c + zlib + OpenSSL.

Build system: CMake (cmake_minimum_required 3.12), pure C.
Output: `ttyd` executable installed into bin/.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class TtydConan(ConanFile):
    name = "ttyd"
    version = "1.7.7"
    description = "Share your terminal over the web (libwebsockets + libuv based web terminal server)"
    license = "MIT"
    homepage = "https://github.com/tsl0922/ttyd"
    url = "https://github.com/tsl0922/ttyd"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libwebsockets/4.3.5.1 is built with LWS_WITH_LIBUV=ON (ttyd's
        # CMakeLists unconditionally FATAL_ERRORs without it) and depends on
        # libuv internally; ttyd also links libuv directly (pty.c).
        self.requires("libwebsockets/4.3.5.1")
        self.requires("json-c/0.18")
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.6")
        self.requires("libuv/1.52.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ttyd is validated only for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libwebsockets 4.3.5.1 is newer than the 3.2.0 minimum ttyd requires;
        # CMakeDeps defaults to SameMajorVersion semantics which would reject
        # the 4.x package for a find_package(Libwebsockets 3.2.0) request.
        # Override the dependency's version-compat property so the generated
        # config-version accepts AnyNewerVersion (4.3.5.1 >= 3.2.0).
        self.dependencies["libwebsockets"].cpp_info.set_property(
            "cmake_config_version_compat", "AnyNewerVersion"
        )
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os in ("Linux", "OHOS"):
            # CMake has no OHOS platform module; native build with clang.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # ttyd's CMakeLists locates json-c / libuv via find_path/find_library
        # (not CONFIG targets), so expose their include/lib dirs explicitly.
        include_paths = []
        library_paths = []
        for dep_name in ("libwebsockets", "json-c", "zlib", "openssl", "libuv"):
            dep = self.dependencies[dep_name]
            inc = os.path.join(dep.package_folder, "include")
            lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(inc):
                include_paths.append(inc.replace("\\", "/"))
            if os.path.isdir(lib):
                library_paths.append(lib.replace("\\", "/"))
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(include_paths)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(library_paths)
        # ttyd's CMakeLists reads the UPPERCASE LIBWEBSOCKETS_* variables after
        # find_package(Libwebsockets); CMakeDeps' generated config only defines
        # lowercase libwebsockets_* variables, so expose them explicitly.
        lws = self.dependencies["libwebsockets"]
        lws_inc = os.path.join(lws.package_folder, "include").replace("\\", "/")
        tc.variables["LIBWEBSOCKETS_INCLUDE_DIRS"] = lws_inc
        tc.variables["LIBWEBSOCKETS_INCLUDE_DIR"] = lws_inc
        lws_lib = os.path.join(lws.package_folder, "lib").replace("\\", "/")
        tc.variables["LIBWEBSOCKETS_LIBRARY"] = os.path.join(lws_lib, "libwebsockets.so")
        tc.variables["LIBWEBSOCKETS_LIBRARIES"] = os.path.join(lws_lib, "libwebsockets.so")
        # Same for OpenSSL: ttyd's CMakeLists appends OPENSSL_INCLUDE_DIR and
        # links OPENSSL_LIBRARIES when libwebsockets is built with SSL support.
        openssl_dep = self.dependencies["openssl"]
        openssl_inc = os.path.join(openssl_dep.package_folder, "include").replace("\\", "/")
        openssl_lib = os.path.join(openssl_dep.package_folder, "lib").replace("\\", "/")
        tc.variables["OPENSSL_INCLUDE_DIR"] = openssl_inc
        tc.variables["OPENSSL_INCLUDE_DIRS"] = openssl_inc
        tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(openssl_lib, "libssl.a")
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(openssl_lib, "libcrypto.a")
        tc.variables["OPENSSL_LIBRARIES"] = ";".join(
            [
                os.path.join(openssl_lib, "libssl.a"),
                os.path.join(openssl_lib, "libcrypto.a"),
            ]
        )
        # ZLIB: ttyd calls find_package(ZLIB) and uses the uppercase
        # ZLIB_INCLUDE_DIR / ZLIB_LIBRARIES variables.
        zlib_dep = self.dependencies["zlib"]
        zlib_inc = os.path.join(zlib_dep.package_folder, "include").replace("\\", "/")
        zlib_lib = os.path.join(zlib_dep.package_folder, "lib").replace("\\", "/")
        zlib_a = os.path.join(zlib_lib, "libz.a")
        zlib_so = os.path.join(zlib_lib, "libz.so")
        tc.variables["ZLIB_INCLUDE_DIR"] = zlib_inc
        tc.variables["ZLIB_INCLUDE_DIRS"] = zlib_inc
        tc.variables["ZLIB_LIBRARY"] = zlib_a if os.path.isfile(zlib_a) else zlib_so
        tc.variables["ZLIB_LIBRARIES"] = zlib_a if os.path.isfile(zlib_a) else zlib_so
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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.requires = [
            "libwebsockets::libwebsockets",
            "json-c::json-c",
            "zlib::zlib",
            "openssl::openssl",
            "libuv::libuv",
        ]
