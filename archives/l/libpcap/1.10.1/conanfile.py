#!/usr/bin/env python3
"""Conan recipe for libpcap 1.10.1 — Packet capture library.

Build system: cmake (autotools config.status has permission issues on OHOS).
Patches: cmake_minimum_required upgrade, pcap-linux.c sockaddr_storage fix.
"""
from conan import ConanFile
from conan.tools.files import get, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class LibpcapConan(ConanFile):
    name = "libpcap"
    version = "1.10.1"
    description = "Packet capture library"
    license = "BSD-3-Clause"
    homepage = "https://www.tcpdump.org/"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/l/libpcap/1.10.1"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS: CMake 4.x removed < 3.5 compat; force minimum version
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # Fix 1: CMakeLists.txt — cmake_minimum_required < 3.5 removed in CMake 4.x
        replace_in_file(self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 2.8.6)",
            "cmake_minimum_required(VERSION 3.5)")
        replace_in_file(self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "cmake_policy(SET CMP0042 OLD)",
            "cmake_policy(SET CMP0042 NEW)")
        # Fix 2: pcap-linux.c — prevent sockaddr_storage redefinition in linux/socket.h
        replace_in_file(self,
            os.path.join(self.source_folder, "pcap-linux.c"),
            "#include <sys/socket.h>\n#include <sys/ioctl.h>",
            "#include <sys/socket.h>\n/* HarmonyOS: prevent sockaddr_storage redefinition */\n"
            "#define sockaddr_storage sockaddr_storage_linux\n"
            "#include <sys/ioctl.h>\n#include <sys/utsname.h>\n#include <sys/mman.h>\n"
            "#include <linux/if.h>\n#undef sockaddr_storage",
            strict=True)
        # Fix 3: Ensure lld can find libxml2.so.16 (CI environment issue)
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(llvm_lib):
            env_path = os.environ.get("LD_LIBRARY_PATH", "")
            if llvm_lib not in env_path:
                os.environ["LD_LIBRARY_PATH"] = llvm_lib + (":" + env_path if env_path else "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["pcap"]
