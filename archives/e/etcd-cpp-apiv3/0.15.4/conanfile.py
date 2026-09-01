#!/usr/bin/env python3
"""Conan recipe for etcd-cpp-apiv3 0.15.4 (CMake).

etcd-cpp-apiv3 is the C++ client library for etcd's v3 gRPC API.

Adaptation notes (HarmonyOS PC / aarch64):
- Built with BUILD_ETCD_CORE_ONLY=ON (the synchronous runtime). The full
  build additionally needs cpprestsdk for the async client, which is not
  published in the registry; the core-only mode is an upstream-supported
  configuration and yields the real library target etcd-cpp-api-core
  plus an INTERFACE alias etcd-cpp-api.
- grpc/1.70.0 pins protobuf/33.6, so this recipe requires the same
  version to avoid a version conflict in the dependency graph
  (grpc 1.49.2 is API-incompatible with protobuf 33.x, see grpc notes).
- protobuf's registry package exports cmake_find_mode=none, so
  find_package(Protobuf CONFIG) is pointed at the installed config files
  directly (mirrors the grpc recipe wiring).
- The proto codegen runs protoc and grpc_cpp_plugin from the registry
  packages; this machine is a native arm64 OHOS host, so both binaries
  run natively. Their locations are pinned via cache variables because
  CMAKE_CROSSCOMPILING is set by the OHOS toolchain (CMAKE_SYSTEM_NAME=
  HarmonyOS vs. a Linux host), which would otherwise force a PATH search.
- ETCD_W_STRICT is disabled: -Werror is fragile across clang versions
  and adds no value for the adaptation.
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


class EtcdCppApiv3Conan(ConanFile):
    name = "etcd-cpp-apiv3"
    version = "0.15.4"
    description = "C++ client library for etcd's v3 API (synchronous core)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3"
    url = "https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3"
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
        # R32: platform checks use `in`, not `==`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "etcd-cpp-apiv3 supports Linux and OHOS targets"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # grpc/1.70.0 (abseil lts_20260107) requires C++17.
        check_min_cppstd(self, 17)
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "etcd-cpp-apiv3 supports OHOS armv8 only"
            )

    def requirements(self):
        # grpc/1.70.0 pins protobuf/33.6: use the same reference so the
        # dependency graph resolves without a version conflict.
        self.requires("grpc/1.70.0")
        self.requires("protobuf/33.6")
        # etcd-cpp-apiv3's CMakeLists calls find_package(OpenSSL REQUIRED)
        # directly (used by the gRPC security config path), and libgrpc.a
        # references zlib symbols that gRPCConfig.cmake does not propagate.
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # etcd 0.15.4 declares cmake_minimum_required(3.3), but CMake >= 4
        # removed compatibility with < 3.5. Lift the policy floor instead
        # of patching the upstream CMakeLists. Must be a cache variable:
        # CMake only honors CMAKE_POLICY_VERSION_MINIMUM from the command
        # line (-D), not from a plain set() inside the toolchain file.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Core-only (synchronous client) build: the async client needs
        # cpprestsdk, which is not available in the registry.
        tc.variables["BUILD_ETCD_CORE_ONLY"] = True
        tc.variables["BUILD_ETCD_TESTS"] = False
        # -Werror is fragile across clang versions; disable it.
        tc.variables["ETCD_W_STRICT"] = False

        grpc = self.dependencies["grpc"]
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        openssl = self.dependencies["openssl"]

        # Point find_package(gRPC CONFIG) at the installed config files
        # (grpc's package_info sets cmake_find_mode=none, so CMakeDeps
        # does not generate one). Mirrors the grpc recipe/test wiring.
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc.package_folder, "lib", "cmake", "grpc"
        ).replace("\\", "/")
        # protobuf's registry package also exports cmake_find_mode=none:
        # locate its config files explicitly.
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        # grpc's ssl.cmake locates OpenSSL through the built-in FindOpenSSL
        # module, which needs the registry package root.
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        # Pin the codegen binaries. The OHOS toolchain sets
        # CMAKE_SYSTEM_NAME=HarmonyOS on a Linux host, so CMake considers
        # the build cross-compiled and etcd's CMakeLists would otherwise
        # REQUIRED-find_program() them on a PATH that does not carry the
        # registry package bins.
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = os.path.join(
            protobuf.package_folder, "bin", "protoc"
        ).replace("\\", "/")
        tc.variables["GRPC_CPP_PLUGIN"] = os.path.join(
            grpc.package_folder, "bin", "grpc_cpp_plugin"
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
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # The core-only build installs the real library etcd-cpp-api-core
        # plus an INTERFACE target etcd-cpp-api that points at it. Consumers
        # use find_package(etcd-cpp-apiv3 CONFIG) and link
        # etcd-cpp-apiv3::etcd-cpp-apiv3 (default CMakeDeps naming).
        self.cpp_info.libs = ["etcd-cpp-api-core"]
