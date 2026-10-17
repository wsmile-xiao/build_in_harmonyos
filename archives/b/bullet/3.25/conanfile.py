#!/usr/bin/env python3
"""Conan recipe — bullet 3.25 (CMake)

Bullet Physics SDK: Real-time collision detection and physics simulation.
Adapted for HarmonyOS PC (aarch64) with CMake system name workaround (E092).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BulletConan(ConanFile):
    name = "bullet"
    version = "3.25"
    description = "Bullet Physics SDK: Real-time collision detection and physics simulation"
    license = "Zlib"
    homepage = "https://github.com/bulletphysics/bullet3"
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
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["USE_GRAPHICAL_BENCHMARK"] = "OFF"
        tc.variables["USE_OPENVR"] = "OFF"
        tc.variables["ENABLE_VHACD"] = "OFF"
        tc.variables["BUILD_PYBULLET"] = "OFF"
        tc.variables["BUILD_ENET"] = "OFF"
        tc.variables["BUILD_CLSOCKET"] = "OFF"
        tc.variables["BUILD_CPU_DEMOS"] = "OFF"
        tc.variables["BUILD_BULLET3"] = "OFF"
        tc.variables["BUILD_BULLET2_DEMOS"] = "OFF"
        tc.variables["BUILD_EXTRAS"] = "OFF"
        tc.variables["BUILD_UNIT_TESTS"] = "OFF"
        tc.variables["INSTALL_LIBS"] = "ON"
        # E092: CMake doesn't recognize HarmonyOS platform; use Linux for compatibility
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        self.cpp_info.libs = [
            "BulletDynamics",
            "BulletCollision",
            "BulletSoftBody",
            "BulletInverseDynamics",
            "LinearMath",
            "Bullet3Common",
        ]
        self.cpp_info.includedirs = ["include/bullet"]
