#!/usr/bin/env python3
"""Conan recipe for aws-crt-cpp — AWS C Runtime C++ library.

aws-crt-cpp bundles all AWS C runtime dependencies as git submodules
(aws-c-common, aws-c-io, aws-c-cal, etc.) and builds them with BUILD_DEPS=ON.
This recipe downloads the main release tarball plus each submodule archive
separately, since the GitHub release tarball does not include submodule content.

Platform adaptation: On OHOS (HarmonyOS), CMAKE_SYSTEM_NAME is detected as
"HarmonyOS" but the aws-c-io CMakeLists.txt only recognizes "Linux" and
"Android" for epoll event loop setup. We set CMAKE_SYSTEM_NAME=Linux to
treat OHOS as Linux-compatible (which it is, being musl/glibc based).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwscrtcppConan(ConanFile):
    name = "aws-crt-cpp"
    version = "0.38.5"
    description = "AWS C Runtime C++ wrapper with RAII memory management and coroutine support"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-crt-cpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download main release tarball (does not include git submodule content)
        sources = self.conan_data["sources"]
        get(self, **{k: v for k, v in sources.items()
                      if k not in ("submodules",)},
            strip_root=True)

        # Download and extract each submodule into the crt/ directory
        for sub in sources.get("submodules", []):
            sub_path = os.path.join(self.source_folder, sub["path"])
            os.makedirs(sub_path, exist_ok=True)
            get(self, url=sub["url"], sha256=sub["sha256"],
                strip_root=True, destination=sub_path)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS adaptation: CMake detects CMAKE_SYSTEM_NAME as "HarmonyOS",
        # but aws-c-io only checks for "Linux" or "Android" for epoll setup.
        # OHOS is Linux-compatible, so we force CMAKE_SYSTEM_NAME=Linux.
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            # Set CMAKE_SYSTEM_PROCESSOR from Conan arch setting
            arch = str(self.settings.arch)
            if arch == "armv8":
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            else:
                tc.variables["CMAKE_SYSTEM_PROCESSOR"] = arch
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["ENFORCE_SUBMODULE_VERSIONS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # aws-crt-cpp bundles all AWS C runtime libraries (BUILD_DEPS=ON).
        # The main lib is linked normally; bundled deps use --whole-archive
        # because aws-lc's libcrypto.a has internal C/assembly object
        # dependencies that the linker won't resolve otherwise.
        self.cpp_info.libs = ["aws-crt-cpp"]
        if self.settings.os in ("Linux", "OHOS"):
            bundled_libs = [
                "-laws-c-auth", "-laws-c-http", "-laws-c-mqtt", "-laws-c-s3",
                "-laws-c-event-stream", "-laws-checksums", "-laws-c-sdkutils",
                "-laws-c-cal", "-laws-c-io", "-laws-c-compression",
                "-laws-c-common", "-ls2n", "-lcrypto",
            ]
            self.cpp_info.exelinkflags = [
                "-Wl,--whole-archive"
            ] + bundled_libs + [
                "-Wl,--no-whole-archive",
            ]
            self.cpp_info.sharedlinkflags = [
                "-Wl,--whole-archive"
            ] + bundled_libs + [
                "-Wl,--no-whole-archive",
            ]
            self.cpp_info.system_libs = ["pthread", "dl", "rt", "m"]
