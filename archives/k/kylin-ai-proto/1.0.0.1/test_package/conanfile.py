#!/usr/bin/env python3
"""Conan L1 test for kylin-ai-proto 1.0.0.1 (INTERFACE data package).

The package compiles no code, so the test substantively verifies the two things
the package actually delivers:
  1. find_package(KylinAiProto) resolves and the exported INTERFACE target
     KylinAiProto::KylinAiProto links (configure/link would fail otherwise).
  2. The protocol definition files (gdbus XML + grpc proto) are installed under
     share/kylin-ai/protocols/ in the package, present and non-empty.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KylinAiprotoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Expose the installed protocols dir (dependency package folder) to the
        # test binary via a CMake cache variable (KAP_PROTOCOLS_DIR), and the
        # installed CMake package config dir (lib/cmake/KylinAiProto) via
        # KAP_CMAKE_DIR so the test also verifies the package's build-time
        # deliverables (this is what the CI L1e destructive test depends on).
        dep = self.dependencies["kylin-ai-proto"]
        proto_root = os.path.join(dep.package_folder, "share", "kylin-ai", "protocols")
        cmake_root = os.path.join(dep.package_folder, "lib", "cmake", "KylinAiProto")
        tc = CMakeToolchain(self)
        tc.variables["KAP_PROTOCOLS_DIR"] = proto_root
        tc.variables["KAP_CMAKE_DIR"] = cmake_root
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) ctest executes the consumer test binary (links the exported target)
        cmake = CMake(self)
        cmake.test()

        # 2) Run the built test binary directly (CI L0c / preflight PF3 require
        #    self.run(...) to actually execute the artifact).
        exe = os.path.join(self.build_folder, "test_kylin-ai-proto")
        if not os.path.exists(exe):
            raise Exception(f"test binary not found: {exe}")
        self.run(exe, env="conanrun")

        # 3) Python-side assertions: key protocol files exist and are non-empty
        #    in the installed package.
        dep = self.dependencies["kylin-ai-proto"]
        proto_root = os.path.join(dep.package_folder, "share", "kylin-ai", "protocols")
        for rel in ("gdbus/gennlpservice.xml", "grpc/vector-db/milvus.proto"):
            p = os.path.join(proto_root, rel)
            if not (os.path.isfile(p) and os.path.getsize(p) > 0):
                raise Exception(f"kylin-ai-proto protocol file missing or empty: {p}")
        self.output.info(f"kylin-ai-proto protocols verified at {proto_root}")
