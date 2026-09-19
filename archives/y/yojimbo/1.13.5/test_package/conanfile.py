#!/usr/bin/env python3
"""Conan test_package — yojimbo 1.13.5 consumer test.

Consumer view: a real loopback Client/Server session over the installed
libyojimbo.a — InsecureConnect handshake (netcode connect token + libsodium
AEAD over 127.0.0.1 UDP), bidirectional reliable-ordered message exchange
(TestMessage + TestBlockMessage, mirrors upstream test_client_server_messages),
then clean disconnect. Exercises the vendored sodium/netcode/reliable/tlsf
objects folded into the archive end to end. The environment probe calls
uname() (pure POSIX) and prints the rule12 verification line
unconditionally (no platform-conditional macros, per R8).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class YojimboTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["-j1"])

    def test(self):
        # L0d/R34: execute the test binary explicitly and check its exit
        # code. Environment: the OHOS-native binary needs the toolchain
        # libc++ (system /system/lib64 provides libc++_shared.so) plus the
        # dependency libs from the conan build env.
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_yojimbo").replace("\\", "/")
        self.run(cmd, env="conanbuild")
        self.output.info("yojimbo loopback client/server session test passed")
