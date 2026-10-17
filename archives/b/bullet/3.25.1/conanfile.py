#!/usr/bin/env python3
"""Conan recipe — bullet 3.25.1 (CMake)

Bullet Physics SDK: Real-time collision detection and physics simulation.
Adapted for HarmonyOS PC (aarch64) with CMake system name workaround (E092).
3.25.1 adds a `precision` option:
  * single (default): btScalar = float, matches upstream ohpcd bullet/3.25
  * double: builds with the upstream CMake gate USE_DOUBLE_PRECISION=ON, which
    applies -DBT_USE_DOUBLE_PRECISION (btScalar = double) to all targets and
    propagates it to consumers via cpp_info.defines (ABI must match).
Needed by OpenMW 0.51.0, whose CMakeLists.txt:445 requires a double-precision
Bullet (HAS_DOUBLE_PRECISION_BULLET).

Upstream tests: BUILD_UNIT_TESTS=ON, run via ctest at the end of build()
(CMake ENABLE_TESTING + test/ subdirs). BUILD_BULLET3 stays OFF so the
OpenCL(RBullet3OpenCL/clew), InverseDynamics(RBdl) and SharedMemory(enet)
groups are not pulled in; the gtest + collision + BulletDynamics groups are
still built and run.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BulletConan(ConanFile):
    name = "bullet"
    version = "3.25.1"
    description = "Bullet Physics SDK: Real-time collision detection and physics simulation"
    license = "Zlib"
    homepage = "https://github.com/bulletphysics/bullet3"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "precision": ["single", "double"]}
    default_options = {"shared": False, "precision": "single"}

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
        # Demos / feature gates that need extra deps or a graphical/headful
        # environment — intentionally OFF on OHOS.
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
        # Upstream tests ON (gtest + collision + BulletDynamics groups).
        # BUILD_BULLET3=OFF keeps OpenCL/RBdl/enet test groups out.
        tc.variables["BUILD_UNIT_TESTS"] = "ON"
        tc.variables["INSTALL_LIBS"] = "ON"
        # Upstream CMake gate for btScalar = double (ADD_DEFINITIONS
        # -DBT_USE_DOUBLE_PRECISION to all targets + feeds BulletConfig).
        tc.variables["USE_DOUBLE_PRECISION"] = "ON" if self.options.precision == "double" else "OFF"
        # E092: CMake doesn't recognize HarmonyOS platform; use Linux for compatibility
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试 (BUILD_UNIT_TESTS=ON) ──
        cmake.test()

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
        # Propagate the macro to consumers so their btScalar matches the library
        # (essential for ABI when precision=double).
        if self.options.precision == "double":
            self.cpp_info.defines = ["BT_USE_DOUBLE_PRECISION"]
