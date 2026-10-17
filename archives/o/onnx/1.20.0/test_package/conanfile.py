#!/usr/bin/env python3
"""Conan test_package for onnx/1.20.0 — real C++ consumer (R34).

Builds against the installed ONNX C++ API (onnx/onnx_pb.h), does a ModelProto
serialize/parse round-trip and asserts IR version / node / opset, so the test
actually exercises the package rather than printing a banner.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class OnnxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("protobuf/33.6.1")
        self.requires("abseil-cpp/20260107.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        onnx = self.dependencies["onnx"]
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        tc = CMakeToolchain(self)
        # protobuf registry package: cmake_find_mode=none -> explicit config dirs
        # ONNXConfig.cmake (CMakeDeps wrapper) calls find_dependency(protobuf) lowercase,
        # so both spellings of the DIR variable are needed.
        protobuf_cmake = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
        tc.variables["Protobuf_DIR"] = protobuf_cmake
        tc.variables["protobuf_DIR"] = protobuf_cmake
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range").replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")
        # ONNX ships its own ONNXConfig.cmake (cmake_find_mode=none in the recipe)
        tc.variables["ONNX_DIR"] = os.path.join(
            onnx.package_folder, "lib", "cmake", "ONNX").replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Execute the installed-package consumer on the build machine when possible.
        # Cross builds (aarch64 target on x86_64 host) cannot run the binary, and the
        # WSL profile marks tools.build:skip_test=True for exactly that reason.
        if not can_run(self) or self.conf.get("tools.build:skip_test", default=False):
            self.output.info("skip consumer run: cross build / tools.build:skip_test")
            return
        self.run(os.path.join(self.build_folder, "test_onnx"), env="conanrun")
