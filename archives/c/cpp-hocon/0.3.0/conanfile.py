#!/usr/bin/env python3
"""Conan recipe — cpp-hocon 0.3.0 (C++ HOCON config parser, Puppet Labs).

cpp-hocon is the C++ port of TypesafeConfig. Upstream builds on the
puppetlabs/leatherman CMake framework and requires Boost >= 1.54.
Leatherman is not published for OHOS, so this port ships minimal
header shims for the three leatherman APIs cpp-hocon actually uses
(locale::_/format/translate, util::environment::each, util::scope_exit)
and replaces the leatherman/gettext/cpplint CMake scaffolding with a
plain CMake build (patches 0001/0002), keeping the library sources,
public headers and the upstream unit_tests target unchanged.

Upstream test suite (lib/tests, Catch v1): builds and runs on the
device — 114 test cases / 3229 assertions, all passing (9 cases /
12 assertions "failed as expected" are the upstream pending '+='
tests, Catch v1 expected-failure semantics, zero unexpected
failures).

Dependencies (all published on ohpcd, W0 verified via conan
download):
  * boost1.84/1.84.0        — headers + filesystem/program_options/
                              regex/iostreams static libs
  * boost1.84-thread/1.84.0 — boost_thread static lib (tss)
  * catch/1.12.2            — Catch v1 single header (tests only)

Note on libuv: task notes mentioned libuv as a dependency, but
cpp-hocon 0.3.0 sources contain no libuv usage (verified: grep
uv_/libuv/uv.h over lib/ and acceptance/ returns nothing). libuv is
a leatherman-internal dependency, not a cpp-hocon one.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CppHoconConan(ConanFile):
    name = "cpp-hocon"
    version = "0.3.0"
    description = "C++ parser for the HOCON configuration file format (TypesafeConfig port)"
    license = "Apache-2.0"
    homepage = "https://github.com/puppetlabs/cpp-hocon"
    url = "https://github.com/puppetlabs/cpp-hocon"
    topics = ("hocon", "config", "configuration", "parser")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # W0/R36: all published on ohpcd with OHOS binaries.
        # boost1.84 carries the full boost include tree (format/nowide/
        # variant/... headers plus filesystem/program_options/regex/iostreams
        # static libs); boost1.84-thread adds libboost_thread (tss).
        # Note: boost/1.91.0.1.1 was tried first but its package is trimmed
        # (no boost/format.hpp, no boost/nowide/*) which cpp-hocon needs.
        self.requires("boost1.84/1.84.0")
        self.requires("boost1.84-thread/1.84.0")
        self.requires("catch/1.12.2")

    def build_requirements(self):
        pass

    def validate(self):
        # R32: platform check must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cpp-hocon only supports Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # boost1.84 and boost1.84-thread both export cmake_file_name
        # "Boost"; in one generator folder the later install overwrites
        # the other's BoostConfig.cmake. Rename the thread package config
        # so both are findable (the port's CMakeLists looks it up under
        # this name; other consumers are unaffected).
        deps.set_property("boost1.84-thread", "cmake_file_name",
                          "hocon-boost-thread")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["HOCON_BUILD_TESTS"] = bool(self.options.with_upstream_tests)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # The upstream unit_tests binary runs on the device via ctest;
        # statically link the C++ runtime so the loader finds all symbols
        # (dynamic libc++_shared.so is only in the SDK sysroot).
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-static-libstdc++"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_upstream_tests and can_run(self):
            # Upstream test entry: ctest target "unit_tests"
            # (lib/tests, Catch v1 single binary).
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Public headers include boost/* (variant/optional/nowide/...) and
        # the leatherman compat shim, so the boost requirements must
        # propagate to consumers; catch.hpp is header-only and propagates
        # as a test dep.
        self.cpp_info.requires = ["boost1.84::boost1.84",
                                  "boost1.84-thread::boost1.84-thread",
                                  "catch::catch"]
        self.cpp_info.libs = ["hocon"]
        self.cpp_info.includedirs = ["include"]
        # Public headers include leatherman/locale/locale.hpp through the
        # compat shim shipped in the package (include/leatherman/...), so
        # downstream consumers do not need leatherman installed.
        self.cpp_info.set_property("cmake_file_name", "cpp-hocon")
        self.cpp_info.set_property("cmake_target_name", "cpp-hocon::cpp-hocon")
        self.cpp_info.set_property("pkg_config_name", "cpp-hocon")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def package_id(self):
        # The upstream tests are a build-time check only; they do not
        # change the packaged artifacts.
        del self.info.options.with_upstream_tests
