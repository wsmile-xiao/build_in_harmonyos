#!/usr/bin/env python3
"""Conan recipe for Coturn 4.15.0 on OpenHarmony."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class CoturnConan(ConanFile):
    name = "coturn"
    version = "4.15.0"
    exports_sources = "patches/*"
    description = "Open source TURN and STUN server"
    license = "BSD-3-Clause"
    homepage = "https://github.com/coturn/coturn"
    url = "https://github.com/coturn/coturn"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "with_upstream_tests": False,
    }

    def requirements(self):
        self.requires("libevent/2.1.12", run=True)
        self.requires("openssl/3.5.6", run=True)
        self.requires("sqlite3/3.49.1", run=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["unity"],
            destination=os.path.join(self.source_folder, "third_party", "unity"),
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = self.options.shared
        toolchain.variables["BUILD_TESTING"] = self.options.with_upstream_tests
        toolchain.variables["FETCHCONTENT_SOURCE_DIR_UNITY"] = os.path.join(
            self.source_folder, "third_party", "unity"
        )
        # libmicrohttpd is not yet available for the OpenHarmony package set.
        # Keep the TURN/STUN server and its upstream tests buildable without
        # enabling the optional Prometheus HTTP exporter.
        toolchain.variables["WITH_PROMETHEUS"] = False
        # The published libevent package is built without event_openssl, so
        # do not advertise unavailable TLS/DTLS listeners in this package.
        toolchain.variables["WITH_TLS"] = False
        toolchain.variables["FUZZER"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        # The OHOS SDK linker depends on its bundled libxml2. Conan's build
        # environment can otherwise prepend package runtime directories and
        # make lld load an ABI-incompatible libxml2 before CMake's try-link.
        build_env = Environment()
        build_env.unset("LD_LIBRARY_PATH")
        with build_env.vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.options.with_upstream_tests and can_run(self):
            sqlite_test_dir = os.path.join(self.build_folder, "coturn-test-sqlite")
            os.makedirs(sqlite_test_dir, exist_ok=True)
            test_env = VirtualRunEnv(self).environment()
            test_env.define("COTURN_TEST_SQLITE_DB_DIR", sqlite_test_dir)
            with test_env.vars(self).apply():
                cmake.test()

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS":
            build_bin = os.path.join(self.build_folder, "bin")
            package_bin = os.path.join(self.package_folder, "bin")
            for binary in os.listdir(build_bin):
                source = os.path.join(build_bin, binary)
                destination = os.path.join(package_bin, binary)
                if os.path.isfile(source):
                    if os.path.exists(destination):
                        os.remove(destination)
                    self.run(f'cp "{source}" "{destination}"')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        for dependency in self.dependencies.host.values():
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", dependency.cpp_info.libdirs
            )
