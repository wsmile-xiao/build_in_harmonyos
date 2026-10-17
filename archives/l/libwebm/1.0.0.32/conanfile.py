#!/usr/bin/env python3
"""Conan CMake recipe for the libwebm 1.0.0.32 library (HarmonyOS PC)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
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


class LibWebMConan(ConanFile):
    name = "libwebm"
    version = "1.0.0.32"
    description = "WebM container muxer/parser library by the WebM project"
    license = "BSD-3-Clause"
    homepage = "https://github.com/webmproject/libwebm"
    url = "https://github.com/webmproject/libwebm"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_webm_parser": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "enable_webm_parser": True,
    }

    def export_sources(self):
        pass  # no patches: conandata.yml only carries pinned sources

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libwebm supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        get(
            self,
            **sources["libwebm"],
            destination=self.source_folder,
            strip_root=True,
        )
        get(
            self,
            **sources["googletest"],
            destination=os.path.join(self.source_folder, "third_party", "googletest"),
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # E383: CMake 4.x has no Platform/HarmonyOS.cmake, so the SONAME link
        # flags are empty on OHOS. Provide them explicitly so the shared webm
        # library gets a DT_SONAME (libwebm.so.1) without versioned symlinks.
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # E330: avoid versioned symlink churn on HMDFS-backed paths; the
        # unversioned .so keeps a relocatable DT_SONAME.
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.shared
        ) or bool(self.options.get_safe("fPIC", True))
        # Upstream sample programs/tools are not shipped with the package.
        tc.cache_variables["ENABLE_SAMPLE_PROGRAMS"] = False
        tc.cache_variables["ENABLE_WEBMINFO"] = False
        # ENABLE_WEBMTS builds webm2pes/webm2ts executables only (no library
        # impact); disable to keep the package focused on the webm library.
        tc.cache_variables["ENABLE_WEBMTS"] = False
        tc.cache_variables["ENABLE_TESTS"] = False
        tc.cache_variables["ENABLE_WEBM_PARSER"] = bool(
            self.options.enable_webm_parser
        )
        tc.generate()

    @staticmethod
    def _quoted(value):
        return '"{}"'.format(str(value).replace('"', '\\"'))

    def _build_upstream_tests(self):
        """Configure a second static tree with upstream tests enabled.

        libwebm registers no tests with CTest: each suite is a standalone
        gtest binary. They are invoked directly, with the suites that need
        test data run from the source testdata directory.
        """
        test_build_folder = os.path.join(self.build_folder, "upstream-tests")
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
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
                "-DCMAKE_TOOLCHAIN_FILE={}".format(toolchain_file),
                "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
                "-DBUILD_SHARED_LIBS=OFF",
                "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                # googletest ddb8012 (2015) declares cmake_minimum_required(2.8);
                # CMake 4 rejects < 3.5 without this policy override (leveldb precedent).
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                "-DENABLE_TESTS=ON",
                # GTEST_SRC_DIR must point at the googletest repo root (it
                # add_subdirectory()s it and references googletest/include and
                # googlemock/include below it).
                "-DGTEST_SRC_DIR={}".format(
                    os.path.join(self.source_folder, "third_party", "googletest")
                ),
                "-DENABLE_WEBM_PARSER=ON",
                "-DENABLE_WEBMTS=ON",
                "-DENABLE_WEBMINFO=ON",
                "-DENABLE_SAMPLE_PROGRAMS=ON",
            ]
        )
        self.run(" ".join(configure_args))
        self.run(
            "cmake --build {} --config {} --parallel".format(
                self._quoted(test_build_folder),
                self._quoted(self.settings.build_type),
            )
        )

        if not can_run(self):
            self.output.info(
                "cross-building: upstream tests compiled but cannot run"
            )
            return

        # Suites that read test data resolve files via the
        # LIBWEBM_TEST_DATA_PATH environment variable
        # (testing/test_util.cc), pointing at testing/testdata.
        testdata_folder = os.path.join(self.source_folder, "testing", "testdata")
        test_env = Environment()
        test_env.define("LIBWEBM_TEST_DATA_PATH", testdata_folder)
        # mkvmuxer tests write temp files via TEST_TMPDIR or the CWD
        # (common/file_util.cc GetTempFileName).
        test_tmpdir = os.path.join(test_build_folder, "test-tmp")
        rmdir(self, test_tmpdir)
        mkdir(self, test_tmpdir)
        test_env.define("TEST_TMPDIR", test_tmpdir)
        suites = [
            "mkvmuxer_tests",
            "mkvparser_tests",
            "webm_parser_tests",
            "vp9_header_parser_tests",
            "vp9_level_stats_tests",
            "webm2pes_tests",
        ]
        with test_env.vars(self).apply():
            for suite in suites:
                suite_path = os.path.join(test_build_folder, suite)
                if not os.path.isfile(suite_path):
                    self.output.warn(f"upstream test binary missing: {suite}")
                    continue
                self.run(self._quoted(suite_path), cwd=testdata_folder)

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
        cmake = CMake(self)
        cmake.install()
        # Shared builds get DT_SONAME=libwebm.so via the E383 toolchain flags
        # (no versioned symlinks per E330). Upstream installs only the webm
        # target and its public headers, so nothing else needs cleanup.

    def package_info(self):
        self.cpp_info.libs = ["webm"]
        self.cpp_info.set_property("cmake_file_name", "webm")
        # Upstream target is `webm`; namespace it for consumers.
        self.cpp_info.set_property("cmake_target_name", "webm::webm")
        self.cpp_info.set_property("pkg_config_name", "webm")
