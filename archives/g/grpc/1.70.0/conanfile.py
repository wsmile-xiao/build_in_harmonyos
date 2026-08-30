#!/usr/bin/env python3
"""Conan recipe for grpc 1.70.0 (CMake).

gRPC is a hard dependency of recc (BuildGrid/buildbox 1.4.13), which
requires gRPC >= 1.30 via buildbox-common's `find_package(gRPC 1.30)`.

Adaptation notes (HarmonyOS PC / aarch64):
- All external deps (absl, protobuf, c-ares, re2, openssl, zlib) come
  from the registry (gRPC_*_PROVIDER=package). protobuf/33.6 (registry)
  is API-incompatible with grpc 1.49.2 (util::Status / csharp_names.h
  were removed), so 1.70.0 is used instead.
- absl ABI must match protobuf: abseil-cpp/20260107.1 (lts_20260107).
- OHOS lacks `pthread_cancel` (thd.cc Thread::Kill), and CMakeDeps
  exports `c-ares::c-ares` / `openssl::openssl` while grpc expects
  `c-ares::cares` / `OpenSSL::SSL`; see patches below.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class GrpcConan(ConanFile):
    name = "grpc"
    version = "1.70.0"
    description = "High performance, open source universal RPC framework"
    license = "Apache-2.0"
    homepage = "https://github.com/grpc/grpc"
    url = "https://github.com/grpc/grpc"
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

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("grpc supports Linux and OHOS targets")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("grpc supports OHOS armv8 only")

    def requirements(self):
        # absl ABI must be identical to protobuf/33.6's (lts_20260107).
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("protobuf/33.6")
        self.requires("c-ares/1.34.6")
        self.requires("re2/2024-04-01")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        # grpc's source tree contains a file literally named `build` (a Bazel
        # BUILD file), which collides with cmake_layout's default `build/`
        # folder. Use a distinct build folder name.
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"]["grpc"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Keep all heavy deps from the registry (never build from module
        # submodules on OHOS).
        for provider in ("ABSL", "CARES", "PROTOBUF", "RE2", "SSL", "ZLIB"):
            tc.variables[f"gRPC_{provider}_PROVIDER"] = "package"
        tc.variables["gRPC_BUILD_CODEGEN"] = True
        tc.variables["gRPC_BUILD_TESTS"] = False
        tc.variables["gRPC_BUILD_CSHARP_EXT"] = False
        tc.variables["gRPC_INSTALL"] = True
        tc.variables["gRPC_BUILD_GRPCPP_OTEL_PLUGIN"] = False
        # recc/buildbox-common only need the C++ codegen plugin. The other
        # language plugins (node/csharp/python/ruby/...) fail to build against
        # the newer registry absl (e.g. node_plugin.cc: GetJSServiceFilename
        # absl::string_view -> std::string), so build only the C++ plugin.
        for plugin in ("CSHARP", "NODE", "OBJECTIVE_C", "PHP", "PYTHON", "RUBY"):
            tc.variables[f"gRPC_BUILD_GRPC_{plugin}_PLUGIN"] = False
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        # OHOS lacks pthread_cancel, so Thread::Kill cannot cancel threads.
        # The platform decision lives in the build system (feature macro),
        # not in source, per the project rule against platform macros in
        # patches (see patches/0001-thd-pthread-cancel.patch).
        tc.preprocessor_definitions["GPR_NO_PTHREAD_CANCEL"] = True
        # grpc's ssl.cmake locates OpenSSL through the built-in FindOpenSSL
        # module, which needs the registry package root.
        tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder.replace("\\", "/")
        # protobuf's registry package exports cmake_find_mode=none, so point
        # grpc's find_package(Protobuf CONFIG) at the installed config files
        # directly (mirrors protobuf's own test_package wiring).
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        # abseil is shipped as abseil-cpp; protobuf's config also looks up
        # absl via abslConfig.cmake.
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Preserve grpc's component-rich CMake config (gRPC::grpc++ etc.)
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["grpc++", "grpc", "gpr"]
        self.cpp_info.bindirs = ["bin"]
