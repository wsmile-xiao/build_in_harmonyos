#!/usr/bin/env python3
"""Conan recipe for reflect-cpp 0.17.0 (CMake).

reflect-cpp (rfl) is a C++20 library for fast serialization,
deserialization and validation using reflection.
Homepage: https://github.com/getml/reflect-cpp
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ReflectCppConan(ConanFile):
    name = "reflect-cpp"
    version = "0.17.0"
    description = (
        "C++20 library for fast serialization, deserialization and "
        "validation using reflection"
    )
    license = "MIT"
    homepage = "https://github.com/getml/reflect-cpp"
    url = "https://github.com/getml/reflect-cpp"
    topics = (
        "reflection",
        "serialization",
        "json",
        "header-heavy",
        "deserialization",
    )
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

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os checks must use `in ("Linux", "OHOS")`,
        # not `== "Linux"`, so OHOS targets are accepted.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is validated only for Linux and OHOS, "
                f"not {self.settings.os}"
            )
        # C++20 is enforced by the project itself (set(CMAKE_CXX_STANDARD 20))
        # and pinned via CMAKE_CXX_STANDARD in generate(); the shared
        # ohos-aarch64 profile declares cppstd=17 (and build contexts may
        # declare gnuXX), so no profile-level cppstd rejection here — the
        # compiler will hard-fail if C++20 is unavailable.

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The library is C++20-only; pin the standard explicitly so the build
        # is correct even when the profile declares an older cppstd (17).
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        # Build only the library; the JSON backend uses the ctre + yyjson
        # copies bundled with the source tree, so no external Conan
        # dependencies are required (keeps the package self-contained and
        # avoids the registry-only-newer-versions problem for ctre/yyjson).
        tc.variables["REFLECTCPP_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["REFLECTCPP_USE_BUNDLED_DEPENDENCIES"] = True
        tc.variables["REFLECTCPP_USE_VCPKG"] = False
        tc.variables["REFLECTCPP_BUILD_TESTS"] = False
        tc.variables["REFLECTCPP_BUILD_BENCHMARKS"] = False
        tc.variables["REFLECTCPP_AVRO"] = False
        tc.variables["REFLECTCPP_BSON"] = False
        tc.variables["REFLECTCPP_CAPNPROTO"] = False
        tc.variables["REFLECTCPP_CBOR"] = False
        tc.variables["REFLECTCPP_FLEXBUFFERS"] = False
        tc.variables["REFLECTCPP_MSGPACK"] = False
        tc.variables["REFLECTCPP_TOML"] = False
        tc.variables["REFLECTCPP_UBJSON"] = False
        tc.variables["REFLECTCPP_XML"] = False
        tc.variables["REFLECTCPP_YAML"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            pattern="LICENSE",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["reflectcpp"]
        # CMake integration: the library installs reflectcpp-config.cmake
        self.cpp_info.set_property(
            "cmake_file_name", "reflectcpp"
        )
        self.cpp_info.set_property("cmake_target_name", "reflectcpp::reflectcpp")

    @property
    def _min_cppstd(self):
        return 20
