#!/usr/bin/env python3
"""Conan recipe for protobuf 33.6 (CMake)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    replace_in_file,
    save,
)


class ProtobufConan(ConanFile):
    name = "protobuf"
    version = "33.6"
    description = "Google's data serialization library and compiler"
    license = "BSD-3-Clause"
    homepage = "https://github.com/protocolbuffers/protobuf"
    url = "https://github.com/protocolbuffers/protobuf"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_zlib": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("protobuf supports Linux and OHOS targets")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("protobuf supports OHOS armv8 only")

    def requirements(self):
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        if self.options.with_zlib:
            self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["protobuf"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["googletest"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "googletest"),
        )
        # Keep a pinned native Abseil source tree for the host generator build.
        get(
            self,
            **self.conan_data["sources"]["host_abseil"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "host-abseil"),
        )

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Build the upstream CTest targets so the four registered test entry
        # points can be exercised on a HarmonyOS PC after cross-compilation.
        tc.variables["protobuf_BUILD_TESTS"] = True
        tc.variables["protobuf_BUILD_CONFORMANCE"] = False
        tc.variables["protobuf_BUILD_EXAMPLES"] = False
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["protobuf_BUILD_PROTOC_BINARIES"] = True
        tc.variables["protobuf_BUILD_LIBPROTOC"] = True
        tc.variables["protobuf_BUILD_LIBUPB"] = True
        tc.variables["protobuf_FORCE_FETCH_DEPENDENCIES"] = False
        tc.variables["protobuf_LOCAL_DEPENDENCIES_ONLY"] = True
        tc.variables["protobuf_GTEST_SOURCE_DIR"] = os.path.join(
            self.source_folder, "googletest"
        ).replace("\\", "/")
        if cross_building(self) and str(self.settings_build.os) == "Windows":
            tc.variables["protobuf_HOST_PROTOC"] = os.path.join(
                self.build_folder,
                "host-tools",
                "build",
                "protobuf-build",
                "protoc.exe",
            ).replace("\\", "/")
        tc.variables["protobuf_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["absl_DIR"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder,
            "lib",
            "cmake",
            "absl",
        ).replace("\\", "/")
        if self.options.with_zlib:
            tc.variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder.replace(
                "\\", "/"
            )
        if cross_building(self) and str(self.settings_build.os) == "Windows":
            tc.variables["protobuf_HOST_PLUGIN_DIR"] = os.path.join(
                self.build_folder, "host-tools", "build", "protobuf-build"
            ).replace("\\", "/")
        tc.generate()

    def _build_host_tools(self):
        """Build native upb generators used while cross-compiling target code."""
        host_tools_folder = os.path.join(self.build_folder, "host-tools")
        host_build_folder = os.path.join(host_tools_folder, "build")
        cmake_lists = os.path.join(host_tools_folder, "CMakeLists.txt")
        host_abseil = os.path.join(self.source_folder, "host-abseil").replace("\\", "/")
        protobuf_source = self.source_folder.replace("\\", "/")
        save(
            self,
            cmake_lists,
            f'''cmake_minimum_required(VERSION 3.16)
project(protobuf_host_tools LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(ABSL_BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(ABSL_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
set(ABSL_PROPAGATE_CXX_STD ON CACHE BOOL "" FORCE)
set(ABSL_MSVC_STATIC_RUNTIME OFF CACHE BOOL "" FORCE)
add_subdirectory("{host_abseil}" abseil-build EXCLUDE_FROM_ALL)

set(protobuf_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(protobuf_BUILD_CONFORMANCE OFF CACHE BOOL "" FORCE)
set(protobuf_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(protobuf_BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(protobuf_BUILD_PROTOC_BINARIES ON CACHE BOOL "" FORCE)
set(protobuf_BUILD_LIBPROTOC ON CACHE BOOL "" FORCE)
set(protobuf_BUILD_LIBUPB ON CACHE BOOL "" FORCE)
set(protobuf_WITH_ZLIB OFF CACHE BOOL "" FORCE)
set(protobuf_FORCE_FETCH_DEPENDENCIES OFF CACHE BOOL "" FORCE)
set(protobuf_LOCAL_DEPENDENCIES_ONLY ON CACHE BOOL "" FORCE)
set(protobuf_INSTALL OFF CACHE BOOL "" FORCE)
set(protobuf_MSVC_STATIC_RUNTIME OFF CACHE BOOL "" FORCE)
add_subdirectory("{protobuf_source}" protobuf-build EXCLUDE_FROM_ALL)
''',
        )
        cmake_program = self.conf.get("tools.cmake:cmake_program", default="cmake")
        self.run(
            f'"{cmake_program}" -S "{host_tools_folder}" -B "{host_build_folder}" '
            f'-G Ninja -DCMAKE_BUILD_TYPE=Release',
            cwd=host_tools_folder,
        )
        self.run(
            f'"{cmake_program}" --build "{host_build_folder}" '
            f'--target protoc protoc-gen-upb protoc-gen-upbdefs protoc-gen-upb_minitable --parallel',
            cwd=host_tools_folder,
        )

    def build(self):
        apply_conandata_patches(self)
        if cross_building(self) and str(self.settings_build.os) == "Windows":
            self._build_host_tools()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_tmpdir = os.path.join(self.build_folder, "test-tmp")
            mkdir(self, test_tmpdir)
            test_env = Environment()
            test_env.define("TEST_TMPDIR", test_tmpdir)
            test_env.define("TMPDIR", test_tmpdir)
            test_env.prepend_path("PATH", self.build_folder)
            with test_env.vars(self).apply():
                cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])

    def package(self):
        CMake(self).install()
        package_prefix = self.package_folder.replace("\\", "/")
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        for pc_name in (
            "protobuf-lite.pc",
            "protobuf.pc",
            "upb.pc",
            "utf8_range.pc",
        ):
            pc_path = os.path.join(pkgconfig_dir, pc_name)
            replace_in_file(
                self,
                pc_path,
                f"includedir={package_prefix}/include",
                "includedir=${prefix}/include",
            )
            replace_in_file(
                self,
                pc_path,
                f"libdir={package_prefix}/lib",
                "libdir=${prefix}/lib",
            )
            replace_in_file(
                self,
                pc_path,
                f"exec_prefix={package_prefix}",
                "exec_prefix=${prefix}",
            )
            replace_in_file(
                self,
                pc_path,
                f"prefix={package_prefix}",
                "prefix=${pcfiledir}/../..",
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Preserve Protobuf's component-rich CMake config and utf8_range targets.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["protobuf"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs.append("pthread")
        self.cpp_info.requires.append("abseil-cpp::abseil-cpp")
        if self.options.with_zlib:
            self.cpp_info.requires.append("zlib::zlib")
