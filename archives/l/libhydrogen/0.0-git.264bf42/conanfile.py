#!/usr/bin/env python3
"""Conan recipe — libhydrogen 0.0-git.264bf42 (CMake, zero external deps).

libhydrogen is a lightweight, secure, easy-to-use cryptographic library
by jedisct1 (Frank Denis). It implements the same primitives as WireGuard
(Gimli/X25519/Ed25519-style signatures), targets constrained environments,
and builds as a single C translation unit with no external dependencies.

Upstream: https://github.com/jedisct1/libhydrogen master @ 264bf42.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LibhydrogenConan(ConanFile):
    name = "libhydrogen"
    version = "0.0-git.264bf42"
    description = (
        "A lightweight, secure, easy-to-use crypto library "
        "(Gimli permutation, WireGuard-protocol primitives)"
    )
    license = "ISC"
    homepage = "https://github.com/jedisct1/libhydrogen"
    url = "https://github.com/jedisct1/libhydrogen"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2/kpeople5 precedent).
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # Upstream declares cmake_minimum_required(VERSION 3.1); CMake >= 4.0
        # removed compatibility with < 3.5. Pass the official escape hatch as
        # a command-line cache variable (-D) so it is already set when line 1
        # of the upstream CMakeLists.txt is parsed (toolchain-file variables
        # are only loaded at project(), which is too late here). Older CMake
        # (3.x, as used by CI workers) ignores this unknown cache variable.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Default ALL target: the `hydrogen` library only. Upstream sets
        # EXCLUDE_FROM_ALL on the tests executable when CMAKE_CROSSCOMPILING
        # (OHOS cross builds map CMAKE_SYSTEM_NAME=HarmonyOS), so build it
        # explicitly and run it when the host can execute target binaries.
        cmake.build()

        # Upstream official test suite: single `hydrogen-tests` executable
        # registered via enable_testing() + add_test() in CMakeLists.txt,
        # covering 11 test functions (core/hash/kdf/kx_*/pwhash/randombytes/
        # secretbox/sign) with assert-based checks.
        cmake.build(target="hydrogen-tests")
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0], "hydrogen-tests")
            self.run(test_bin, env="conanrun")
            self.output.info(
                "Upstream hydrogen-tests suite passed "
                "(11/11 test functions, exit code 0)"
            )
        else:
            self.output.info(
                "Cross build: hydrogen-tests built for target execution"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["hydrogen"]
        self.cpp_info.set_property("cmake_file_name", "hydrogen")
        self.cpp_info.set_property("cmake_target_name", "hydrogen::hydrogen")
        self.cpp_info.set_property("pkg_config_name", "hydrogen")
