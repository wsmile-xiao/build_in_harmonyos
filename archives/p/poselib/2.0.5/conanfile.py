#!/usr/bin/env python3
"""Conan recipe for poselib 2.0.5 — HarmonyOS PC (aarch64) adaptation.

PoseLib is a library for solving minimal problems in computer vision
(camera pose estimation): 30+ minimal solvers (P3P, GP3P, relpose, homography,
...) plus robust estimators (RANSAC, bundle adjustment).

Adaptation notes (see notes.md):
  - patch removes -Werror from non-MSVC compile flags (clang 15 + Eigen 3.4
    headers warn, -Werror makes them fatal) — portability patch
  - upstream tag is v2.0.5 but project(PoseLib VERSION 2.0.4); upstream's own
    inconsistency, left untouched (R1 minimal-change); conan version follows
    the tag (R37): 2.0.5
  - upstream options kept at defaults (R1): WITH_BENCHMARK=OFF,
    MARCH_NATIVE=OFF (never enable under cross-compilation), PYTHON_PACKAGE=OFF
  - upstream builds a STATIC library by default (BUILD_SHARED_LIBS=OFF)
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PoselibConan(ConanFile):
    name = "poselib"
    version = "2.0.5"
    description = "Minimal solvers for camera pose estimation (P3P, GP3P, relative pose, homography) plus robust RANSAC/bundle estimators"
    license = "BSD-3-Clause"
    homepage = "https://github.com/PoseLib/PoseLib"
    url = "https://github.com/PoseLib/PoseLib"

    package_type = "library"
    languages = "C++"
    topics = ("computer-vision", "camera-pose", "minimal-solver", "p3p", "slam")

    # CMakeDeps generates Eigen3-config.cmake so the upstream
    # find_package(Eigen3 REQUIRED) resolves to the conan dependency
    generators = "CMakeDeps"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Eigen is a PUBLIC dependency: installed headers (alignment.h,
        # types.h, all solvers/*.h) directly #include <Eigen/...>, so
        # consumers need eigen's include dirs too (Conan 2 propagates
        # headers of visible requires to consumers).
        self.requires("eigen/3.4.0", visible=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R1: minimal parameters — only BUILD_SHARED_LIBS mapped to the conan
        # option; upstream options stay at their defaults
        # (WITH_BENCHMARK=OFF / MARCH_NATIVE=OFF / PYTHON_PACKAGE=OFF).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # upstream CMake installs: lib/libPoseLib.a, include/PoseLib/*.h
        # (incl. generated poselib.h / version.h) and cmake export configs
        # into lib/cmake/PoseLib — nothing extra to copy.

    def package_info(self):
        # actual build product: libPoseLib.a (upstream default STATIC)
        self.cpp_info.libs = ["PoseLib"]
        # upstream exports PoseLibConfig.cmake with target PoseLib::PoseLib
        self.cpp_info.set_property("cmake_file_name", "PoseLib")
        self.cpp_info.set_property("cmake_target_name", "PoseLib::PoseLib")
