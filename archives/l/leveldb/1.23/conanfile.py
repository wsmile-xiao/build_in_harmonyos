#!/usr/bin/env python3
"""Conan CMake recipe for the LevelDB 1.23 shared library."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    rmdir,
)


class LevelDBConan(ConanFile):
    name = "leveldb"
    version = "1.23"
    description = "Fast ordered key-value storage library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/leveldb"
    url = "https://github.com/google/leveldb"
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
                f"LevelDB supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        get(
            self,
            **sources["leveldb"],
            destination=self.source_folder,
            strip_root=True,
        )
        for dependency in ("googletest", "benchmark"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(
                    self.source_folder, "third_party", dependency
                ),
                strip_root=True,
            )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.shared
        ) or bool(self.options.get_safe("fPIC", True))
        tc.cache_variables["LEVELDB_BUILD_TESTS"] = False
        tc.cache_variables["LEVELDB_BUILD_BENCHMARKS"] = False
        tc.cache_variables["LEVELDB_INSTALL"] = True
        # CMake 4 removed the compatibility mode required by bundled googletest.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # These upstream checks otherwise pick up undeclared host libraries.
        tc.cache_variables["HAVE_CRC32C"] = False
        tc.cache_variables["HAVE_SNAPPY"] = False
        tc.cache_variables["HAVE_TCMALLOC"] = False
        tc.generate()

    @staticmethod
    def _quoted(value):
        return '"{}"'.format(str(value).replace('"', '\\"'))

    def _build_upstream_tests(self):
        test_build_folder = os.path.join(self.build_folder, "upstream-tests")
        toolchain_file = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        configure_args = [
            "cmake",
            "-S",
            self.source_folder,
            "-B",
            test_build_folder,
        ]
        generator = self.conf.get(
            "tools.cmake.cmaketoolchain:generator",
            default=None,
            check_type=str,
        )
        if generator:
            configure_args.extend(["-G", generator])
        configure_args.extend(
            [
                f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
                f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                # The separate test tree configures bundled googletest again.
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                "-DLEVELDB_BUILD_TESTS=ON",
                "-DLEVELDB_BUILD_BENCHMARKS=OFF",
                "-DLEVELDB_INSTALL=OFF",
                "-DHAVE_CRC32C=OFF",
                "-DHAVE_SNAPPY=OFF",
                "-DHAVE_TCMALLOC=OFF",
            ]
        )
        self.run(" ".join(self._quoted(arg) for arg in configure_args))
        self.run(
            "cmake --build {} --config {} --parallel".format(
                self._quoted(test_build_folder),
                self._quoted(self.settings.build_type),
            )
        )

        if not can_run(self):
            self.output.info(
                "cross-building: 30 POSIX upstream tests compiled but cannot run"
            )
            return
        test_tmpdir = os.path.join(test_build_folder, "test-tmp")
        rmdir(self, test_tmpdir)
        mkdir(self, test_tmpdir)
        test_env = Environment()
        test_env.define("TEST_TMPDIR", test_tmpdir)
        with test_env.vars(self).apply():
            self.run(
                "ctest --output-on-failure --no-tests=error -C {}".format(
                    self._quoted(self.settings.build_type)
                ),
                cwd=test_build_folder,
            )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._build_upstream_tests()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["leveldb"]
        self.cpp_info.set_property("cmake_file_name", "leveldb")
        self.cpp_info.set_property("cmake_target_name", "leveldb::leveldb")
        if self.options.shared:
            self.cpp_info.defines.append("LEVELDB_SHARED_LIBRARY")
        elif self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
