#!/usr/bin/env python3
"""Conan test_package — gamenetworkingsockets 1.6.0 consumer test.

Consumer view: GameNetworkingSockets_Init → real ISteamNetworkingSockets
API surface (CreateListenSocketIP / ConnectByIPAddress / AcceptConnection /
SendMessageToConnection / ReceiveMessagesOnPollGroup) over loopback UDP →
Kill. Exercises the musl pthread service thread + epoll backend + OpenSSL
crypto (cert generation via keypair) end to end. The __OHOS__ block prints
the harmony-specific verification line required by rule12.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class GamenetworkingsocketsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Static GNS archive references protobuf + openssl symbols; the
        # tested package's cpp_info deliberately carries no cmake requires
        # (protobuf registry package is cmake_find_mode=none), so pull the
        # link closure here.
        self.requires("protobuf/33.6.1")
        self.requires("openssl/3.5.8.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Point the upstream protobuf config at the registry package (the
        # registry protobuf package ships a full protobuf-config.cmake with
        # absl transitive deps).
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]

        tc = CMakeToolchain(self)
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        # CMakeDeps' generated FIND_DEPENDENCY_NAMES uses the lowercase
        # "protobuf"; find_dependency(protobuf) reads the cache variable
        # protobuf_DIR (case-sensitive) — inject both spellings (brpc recipe
        # pattern).
        tc.variables["protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        # openssl resolves through CMakeDeps' own generated config
        # (openssl::openssl aggregate target); no native-config override
        # needed here since the test does not call OpenSSL APIs directly.
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

        # The OHOS-native test binary needs the SDK libc++ dir on
        # LD_LIBRARY_PATH to run (musl loader). Save under the build scope
        # (self.run below uses env="conanbuild").
        env = Environment()
        conf = self.conf.get("tools.build:compiler_executables")
        if conf and str(self.settings.os) == "OHOS":
            cc = os.path.realpath(str(conf.get("cpp", "")))
            cand = os.path.join(
                os.path.dirname(os.path.dirname(cc)),
                "lib", "aarch64-linux-ohos", "c++",
            )
            if os.path.isdir(cand):
                env.prepend_path("LD_LIBRARY_PATH", cand)
        env.vars(self, scope="build").save_script("gns_test_libcpp_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def test(self):
        # L0d/R34: execute the test binary explicitly and check its exit
        # code. Environment: the OHOS-native binary needs the toolchain
        # libc++ dir (prepended in generate() with scope="run") plus the
        # dependency libs from the conan build env.
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_gns").replace("\\", "/")
        self.run(cmd, env="conanbuild")
        self.output.info("gamenetworkingsockets loopback lifecycle test passed")
