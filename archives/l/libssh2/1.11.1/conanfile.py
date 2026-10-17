#!/usr/bin/env python3

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class Libssh2Conan(ConanFile):
    name = "libssh2"
    version = "1.11.1"
    description = "Client-side C library implementing the SSH2 protocol"
    license = "BSD-3-Clause"
    homepage = "https://libssh2.org/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libssh2 supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        if self.settings.os == "OHOS":
            rules = os.path.join(
                self.generators_folder, "ohos-cmake-rules.cmake"
            )
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules

        openssl = self.dependencies["openssl"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info

        tc.cache_variables["OPENSSL_ROOT_DIR"] = self.dependencies[
            "openssl"
        ].package_folder
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl.includedirs[0]
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libssl.a"
        )
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libcrypto.a"
        )
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib.includedirs[0]
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(
            zlib.libdirs[0], "libz.a"
        )

        shared = bool(self.options.shared)
        tc.cache_variables["CRYPTO_BACKEND"] = "OpenSSL"
        tc.cache_variables["ENABLE_ZLIB_COMPRESSION"] = True
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["BUILD_STATIC_LIBS"] = not shared
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["ENABLE_WERROR"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            shared or bool(self.options.get_safe("fPIC", True))
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["ssh2"]
        self.cpp_info.set_property("cmake_file_name", "libssh2")
        self.cpp_info.set_property("cmake_target_name", "libssh2::libssh2")
        self.cpp_info.set_property("pkg_config_name", "libssh2")
