#!/usr/bin/env python3
"""Conan recipe for Fast-DDS v2.1.0

Based on ConanCenter recipe, adapted for OHOS (OpenHarmony) platform.
Dependencies use  format (R27).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    rename,
    rm,
    rmdir,
)
from conan.tools.microsoft import check_min_vs


class FastDDSConan(ConanFile):
    name = "fastdds"
    version = "2.1.0"
    license = "Apache-2.0"
    homepage = "https://fast-dds.docs.eprosima.com/"
    url = ""  # CI fills this
    description = "The most complete OSS DDS implementation for embedded systems."
    topics = ("dds", "middleware", "ipc", "rtps")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # R27: All dependencies MUST use  format
        self.requires("tinyxml2/8.0.0")
        self.requires("asio/1.18.0")
        self.requires("fast-cdr/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("foonathan-memory/0.6-2")
        if self.options.with_ssl:
            self.requires("openssl/1.1.1w")

    def validate(self):
        check_min_cppstd(self, 11)
        check_min_vs(self, "192")
        if self.options.shared != self.dependencies["fast-cdr"].options.shared:
            raise ConanInvalidConfiguration(
                f"{self.name} and fast-cdr should be compiled with same 'shared' option."
            )

    def build_requirements(self):
        self.tool_requires("cmake/3.16.3")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Fast-DDS is a library, not a terminal tool, but on OHOS static linking
        # is preferred for DevBox deployment (R26 adapted for libraries)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.variables["BUILD_MEMORY_TOOLS"] = False
        tc.variables["NO_TLS"] = not self.options.with_ssl
        tc.variables["SECURITY"] = self.options.with_ssl
        tc.variables["EPROSIMA_INSTALLER_MINION"] = False
        tc.variables["THIRDPARTY"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("asio", "cmake_file_name", "Asio")
        deps.set_property("asio", "cmake_target_name", "Asio")
        deps.set_property("tinyxml2", "cmake_file_name", "TinyXML2")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fastdds")

        # v2.1.0 uses old component name "fastrtps"
        self.cpp_info.components["fastrtps"].set_property("cmake_target_name", "fastrtps")
        self.cpp_info.components["fastrtps"].set_property("cmake_target_aliases", ["fastdds::fastrtps"])
        self.cpp_info.components["fastrtps"].libs = collect_libs(self)
        self.cpp_info.components["fastrtps"].requires = [
            "fast-cdr::fast-cdr",
            "asio::asio",
            "tinyxml2::tinyxml2",
            "foonathan-memory::foonathan-memory",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["fastrtps"].system_libs.extend(["pthread", "rt", "dl", "atomic", "m"])
        if self.options.with_ssl:
            self.cpp_info.components["fastrtps"].requires.append("openssl::openssl")

        # fast-discovery-server executable component
        self.cpp_info.components["fast-discovery-server"].set_property("cmake_target_name", "fastdds::fast-discovery-server")
        self.cpp_info.components["fast-discovery-server"].bindirs = ["bin"]
