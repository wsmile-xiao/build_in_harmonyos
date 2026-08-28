#!/usr/bin/env python3
"""Conan recipe for discord-rpc 3.4.0 — CMake-based Discord Rich Presence SDK.

Upstream: https://github.com/discord/discord-rpc (tag v3.4.0)

Adaptation notes:
- The project is a CMake build (root CMakeLists.txt + src/CMakeLists.txt), not
  autotools. We use CMakeToolchain + CMake helpers.
- rapidjson is consumed at configure time by the upstream CMakeLists (it would
  download it from GitHub during configure). We instead declare rapidjson/1.1.0
  as a Conan dependency and pass its package root via the RAPIDJSON_ROOT cache
  variable (see patches/0001). This keeps the build offline and reproducible.
- CMake 4.x removed compatibility for cmake_minimum_required < 3.5; we set
  CMAKE_POLICY_VERSION_MINIMUM=3.5 in the toolchain (no source patch needed).
- OHOS (HarmonyOS) is unknown to CMake, so the upstream `if(UNIX)` branch would
  never run and the discord-rpc target would not be created. We force
  CMAKE_SYSTEM_NAME=Linux so the UNIX branch builds with the clang/libc++
  OHOS toolchain (same pattern as other recipes in this repo).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class DiscordRpcConan(ConanFile):
    name = "discord-rpc"
    version = "3.4.0"
    description = "Official Discord Rich Presence SDK (C/C++)"
    license = "MIT"
    homepage = "https://github.com/discord/discord-rpc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("rapidjson/1.1.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        rj = self.dependencies["rapidjson"]
        tc.cache_variables["RAPIDJSON_ROOT"] = rj.package_folder
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        if not self.options.shared:
            tc.variables["BUILD_SHARED_LIBS"] = "OFF"
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
        self.cpp_info.libs = ["discord-rpc"]
