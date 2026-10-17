#!/usr/bin/env python3
"""Conan recipe — vzlogger 0.8.9 (CMake).

vzlogger is the smart-meter logging daemon of the volkszaehler.org project.
This recipe builds the daemon and its static helper libs (libvz/libvz-api/
libproto) with CMake.  Optional meter protocols SML (libsml) and OMS
(libmbus) are disabled at configure time: the conan `sml` package is the
unrelated Boost.SML header library and libmbus is not published, so keep
the daemon on the supported protocols (file/exec/random/s0/d0/fluksov2/
w1therm) plus MQTT and the local HTTPd.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class VzloggerConan(ConanFile):
    name = "vzlogger"
    version = "0.8.9"
    description = "vzlogger: smart meter reading and logging daemon (volkszaehler)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/volkszaehler/vzlogger"
    url = "https://github.com/volkszaehler/vzlogger"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vzlogger supports Linux and OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        # Hard deps of the daemon (FindJson/FindGnutls/FindCURL/FindOpenSSL/
        # find_library uuid/gcrypt + unistring link).
        # Versions match the published conan packages; openssl is constrained by
        # mosquitto/2.0.18 and libgcrypt by gnutls/3.8.10 (verified graph).
        self.requires("json-c/0.18")
        self.requires("libcurl/8.5.0")
        self.requires("gnutls/3.8.10")
        self.requires("openssl/3.5.6.1")
        self.requires("libuuid/2.40.4")
        self.requires("libgcrypt/1.11.0")
        self.requires("libunistring/1.0")
        # Optional features kept on: local HTTPd (ENABLE_LOCAL) + MQTT (ENABLE_MQTT)
        self.requires("libmicrohttpd/1.0.1")
        self.requires("mosquitto/2.0.18")

    def build_requirements(self):
        # gtest/gmock needed by the unit tests (BUILD_TEST=ON, FindGTest
        # via CMakeDeps). Keep as build requirement so consumers do not
        # inherit the test framework.
        self.test_requires("gtest/1.17.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # FindJson/FindGnutls/FindMicroHttpd rely on pkg_check_modules, so the
        # dependencies must be visible through PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()
        # FindCURL/FindOpenSSL/FindGTest are CMake built-ins driven by
        # find_package; CMakeDeps provides their config targets.
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if not self.options.shared:
            tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Optional meter protocols whose deps are unavailable on OHOS: keep off.
        tc.variables["ENABLE_SML"] = "OFF"
        tc.variables["ENABLE_OMS"] = "OFF"
        # gtest/gmock published; unit tests build green (see MANIFEST).
        tc.variables["BUILD_TEST"] = "ON"

        # vzlogger links several deps by bare library name (gtest/gmock/
        # unistring and gnutls transitive deps) and includes <openssl/evp.h>
        # relying on system default paths.  In the isolated conan build we
        # must point the linker at every dependency libdir and the openssl
        # finder at its package root.
        lib_dirs, inc_dirs = [], []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                # tool_requires / not-yet-rendered deps have no package folder
                continue
            ci = dep.cpp_info
            for libdir in ci.libdirs:
                lib_dirs.append(libdir if os.path.isabs(libdir)
                                else os.path.join(dep.package_folder, libdir))
            for incdir in ci.includedirs:
                inc_dirs.append(incdir if os.path.isabs(incdir)
                                else os.path.join(dep.package_folder, incdir))
        if lib_dirs:
            link_flags = " ".join("-L%s" % d for d in dict.fromkeys(lib_dirs))
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = link_flags
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = link_flags
        if inc_dirs:
            tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(dict.fromkeys(inc_dirs))
        if "openssl" in self.dependencies:
            tc.variables["OPENSSL_ROOT_DIR"] = \
                self.dependencies["openssl"].package_folder

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