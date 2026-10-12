#!/usr/bin/env python3
"""Conan recipe for mosquitto 2.0.22 — CMake projects.

Mosquitto is an MQTT broker and client library. It produces both
shared libraries (libmosquitto, libmosquittopp) and executables
(mosquitto broker, mosquitto_pub/sub/rr/ctrl/passwd).

Upgraded from 2.0.18: bugfix-only release line (2.0.19..2.0.22),
including security fixes for CVE-2023-28366 follow-up and malicious
SUBSCRIBE leak (#248). No build-system rework needed; the cmake
_minimum_required bump patch (0001) is no longer necessary because
upstream raised it to 3.18. The pthread_cancel HarmonyOS guard
(0002) is still required.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class MosquittoConan(ConanFile):
    name = "mosquitto"
    version = "2.0.22"
    description = "Open Source MQTT broker and client library"
    license = "EPL-2.0"
    homepage = "https://mosquitto.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # CMakeDeps is required since 2.0.22: upstream links the broker via the
    # OpenSSL::SSL imported target (was ${OPENSSL_LIBRARIES} in 2.0.18).
    # Without CMakeDeps, find_package(OpenSSL) resolves against a host
    # prefix (e.g. harmonybrew) whose libssl.so lacks libcrypto, producing
    # undefined X509_*/EVP_* symbols at link time. CMakeDeps makes
    # find_package(OpenSSL) hit the Conan-pinned openssl package instead.
    generators = "CMakeDeps"
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
        if self.options.with_tls:
            # Upstream consumes the *module-mode* variable OPENSSL_INCLUDE_DIR
            # in include_directories() of lib/, client/, apps/, src/ and
            # plugins/. find_package(OpenSSL) in CONFIG mode (CMakeDeps) does
            # not define it, so plugins that do not link OpenSSL::SSL fail to
            # find <openssl/opensslconf.h>. The root CMakeLists only clears
            # this variable when WITH_TLS is OFF, so a toolchain-level value
            # survives and reaches every subdirectory.
            openssl = self.dependencies["openssl"]
            tc.variables["OPENSSL_INCLUDE_DIR"] = ";".join(
                openssl.cpp_info.aggregated_components().includedirs)
        if self.options.with_cjson:
            # Upstream gates clients and the dynamic-security plugin on the
            # CamelCase CJSON_* variables around FIND_PACKAGE(cJSON), while
            # Conan CMakeDeps exports the lowercase cjson_* set (its
            # cmake_file_name is "cjson") and CMake itself only records the
            # call-case cJSON_FOUND. Without a bridge the build silently
            # disables cJSON support ("Optional dependency cJSON not found")
            # and drops mosquitto_sub -F / the dynamic-security plugin.
            # Toolchain-level cache variables reach every subdirectory.
            cjson = self.dependencies["cjson"]
            tc.variables["CJSON_FOUND"] = True
            tc.variables["CJSON_LIBRARIES"] = "cjson::cjson"
            tc.variables["CJSON_INCLUDE_DIRS"] = ";".join(
                cjson.cpp_info.aggregated_components().includedirs)
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
