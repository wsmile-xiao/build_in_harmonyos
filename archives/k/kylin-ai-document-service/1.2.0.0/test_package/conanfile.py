#!/usr/bin/env python3
"""Conan consumer test for kylin-ai-document-service 1.2.0.0.

The test program links the installed shared library, constructs
document::DocumentChunkClient (this really calls sd_bus_open_user() through
startUserService()) and drives both SyncChunkDocument() overloads, which go
through protobuf serialisation and a real gRPC channel + client stub.  No
document service listens on the unix socket, so the RPC must come back as a
non-OK grpc::Status carrying a non-empty error message — verifying the client
actually performs a call instead of returning a canned value.

grpc and protobuf export cmake_find_mode=none, so CMakeDeps generates no
config files for them; gRPC_DIR / Protobuf_DIR / absl_DIR / utf8_range_DIR are
pinned at the registry configs (mirrors the grpc recipe's own test wiring).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class KylinAiDocumentServiceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Declared directly (not only transitively) so their package_folder is
        # available in generate(): the tested package's own config
        # find_dependency()s grpc/protobuf (CONFIG mode), and both ship
        # cmake_find_mode=none, so their configs must be located explicitly.
        self.requires("grpc/1.84.0")
        self.requires("protobuf/33.6")
        self.requires("abseil-cpp/20260107.1")
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()
        # Generates kylin-ai-document-service-config.cmake (plus the transitive
        # configs) so find_package(kylin-ai-document-service CONFIG) resolves.
        CMakeDeps(self).generate()

        grpc = self.dependencies["grpc"]
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        openssl = self.dependencies["openssl"]

        tc = CMakeToolchain(self)
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc.package_folder, "lib", "cmake", "grpc"
        ).replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.build_folder, "test_document_service")
        if not os.path.isfile(exe):
            raise Exception("consumer test binary not built: {0}".format(exe))

        # Runs the linked client against the (absent) document service and
        # asserts on the real RPC result.
        if can_run(self):
            self.run(exe, env="conanrun")
        else:
            # Cross-build: the binary cannot run here, but it must still have
            # been linked against the package (checked below).
            self.output.info("cannot run test_document_service on this host")

        # Package payload must be complete and relocatable.
        dep = self.dependencies["kylin-ai-document-service"]
        checks = {
            "public header": os.path.join(
                dep.package_folder, "include", "kylin-ai-document-service",
                "client.h"),
            "shared library": os.path.join(
                dep.package_folder, "lib", "libkylin-ai-document-service.so"),
            "pkg-config file": os.path.join(
                dep.package_folder, "share", "pkgconfig",
                "kylin-ai-document-service.pc"),
        }
        for label, path in checks.items():
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                raise Exception(
                    "kylin-ai-document-service {0} missing or empty: {1}".format(
                        label, path))
        self.output.info("kylin-ai-document-service payload verified in {0}".format(
            dep.package_folder))
