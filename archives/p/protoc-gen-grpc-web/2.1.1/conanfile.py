#!/usr/bin/env python3
"""Conan recipe for protoc-gen-grpc-web 2.1.1 (gRPC-Web protoc plugin)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ProtocGenGrpcWebConan(ConanFile):
    name = "protoc-gen-grpc-web"
    version = "2.1.1"
    description = "gRPC for Web Clients: protoc plugin that generates JavaScript gRPC-Web client stubs"
    license = "Apache-2.0"
    homepage = "https://github.com/grpc/grpc-web"
    url = "https://github.com/grpc/grpc-web"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "protoc-gen-grpc-web supports Linux and OHOS targets only"
            )

    def validate(self):
        check_min_cppstd(self, "17")

    def requirements(self):
        # grpc-web 2.1.1 pins protobuf 29.x upstream; we build against the
        # ohpcd-published protobuf 33.6.1 with the compatibility patch
        # declared in conandata.yml (see notes.md).
        self.requires("protobuf/33.6.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["source"], strip_root=True)

    def generate(self):
        # protobuf/33.6.1 keeps its upstream component-rich CMake config
        # (cmake_find_mode=none), so point CMake at the package-owned
        # config dirs directly, mirroring the protobuf/33.6.1 recipe.
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        tc = CMakeToolchain(self)
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        # protobuf 33 string_view compatibility patch: descriptor accessors
        # migrated to absl::string_view and utf8 validation split into
        # libutf8_range/libutf8_validity (details in notes.md).
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
