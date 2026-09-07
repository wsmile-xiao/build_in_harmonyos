#!/usr/bin/env python3
"""Conan recipe for protobuf 3.17.3 (CMake).

protobuf 3.17.3 is an older (2021-05) release whose build entry point lives in
the top-level `cmake/` subdirectory (no root CMakeLists.txt), uses C++11 and does
NOT depend on abseil-cpp (that was only introduced in protobuf >= 23.x). Its only
optional external dependency is zlib (protobuf_WITH_ZLIB, ON by default).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


class ProtobufConan(ConanFile):
    name = "protobuf"
    version = "3.17.3"
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
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("protobuf supports OHOS armv8 only")

    def requirements(self):
        if self.options.with_zlib:
            self.requires("zlib/1.3.1", transitive_headers=True)

    def layout(self):
        # The conan cache build root ('b' folder) already holds a 'build' path,
        # so avoid cmake_layout's build/<build_type> nesting which collides with it.
        self.folders.source = "."
        self.folders.build = "bld"
        self.folders.generators = os.path.join("bld", "generators")

    def source(self):
        get(
            self,
            **self.conan_data["sources"]["protobuf"],
            strip_root=True,
            destination=self.source_folder,
        )
        get(
            self,
            **self.conan_data["sources"]["googletest"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "third_party", "googletest"),
        )

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # OHOS env has no usable /bin/sh for CMake's Unix Makefiles generator, so use Ninja.
        tc.generator = "Ninja"
        # protobuf 3.17.3's CMakeLists lives in the `cmake/` subdir.
        tc.cache_variables["protobuf_BUILD_TESTS"] = True
        tc.cache_variables["protobuf_BUILD_CONFORMANCE"] = False
        tc.cache_variables["protobuf_BUILD_EXAMPLES"] = False
        tc.cache_variables["protobuf_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Building the protoc binary forces libprotoc ON (cmake/CMakeLists.txt:67-69).
        tc.cache_variables["protobuf_BUILD_PROTOC_BINARIES"] = True
        tc.cache_variables["protobuf_BUILD_LIBPROTOC"] = True
        tc.cache_variables["protobuf_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        # protobuf 3.17.3 declares cmake_minimum_required(3.1.3); newer CMake removed
        # support for <3.5, so tell it to allow configuring with old CMP policies.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.options.with_zlib:
            tc.cache_variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder.replace(
                "\\", "/"
            )
            # CMake resolves the Conan zlib as the imported target 'zlib::zlib' (not
            # 'ZLIB::ZLIB'), so ZLIB_LIBRARIES is otherwise empty and the upstream gtest
            # targets fail to link `deflate`. Point it at the real Conan target.
            tc.cache_variables["ZLIB_LIBRARIES"] = "zlib::zlib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="cmake")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Make installed pkg-config metadata relocatable (prefix relative to pcfiledir).
        package_prefix = self.package_folder.replace("\\", "/")
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        for pc_name in ("protobuf-lite.pc", "protobuf.pc"):
            pc_path = os.path.join(pkgconfig_dir, pc_name)
            if os.path.exists(pc_path):
                replace_in_file(
                    self, pc_path, f"prefix={package_prefix}", "prefix=${pcfiledir}/../.."
                )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Preserve Protobuf's component-rich CMake config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["protobuf", "protoc", "protobuf-lite"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs.append("pthread")
        if self.options.with_zlib:
            self.cpp_info.requires.append("zlib::zlib")
