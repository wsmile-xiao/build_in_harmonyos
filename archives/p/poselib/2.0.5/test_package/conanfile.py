#!/usr/bin/env python3
"""Conan test_package for poselib 2.0.5 (R34: substantive tests).

L1 consumer test, run by `conan create`:
  1. C++ consumer links PoseLib, includes the umbrella header and calls
     poselib_info() (version string assertion)
  2. P3P synthetic pose recovery: known rotation+translation, 3 camera-frame
     points back-projected to the world frame; p3p() must return a solution
     matching ground truth to <1e-6 (translation) / <1e-6 deg (rotation)
  3. homography_4pt synthetic recovery: 4 planar correspondences generated
     from a known H; solver must recover H (up to scale) to <1e-9
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PoselibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # poselib public headers directly #include <Eigen/...> (alignment.h,
        # solvers/*.h, ...), so the consumer declares eigen explicitly —
        # CMakeDeps then generates Eigen3's full config (include dirs).
        self.requires("eigen/3.4.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ── 1. C++ consumer test via ctest (asserts inside test_package.cpp) ──
        cmake = CMake(self)
        cmake.test()

        # ── 2. run the consumer binary directly and verify the result line ──
        exe = os.path.join(self.cpp.build.bindirs[0], "test_package")
        out_path = os.path.join(self.build_folder, "test_poselib.out")
        self.run(f'"{exe}" > "{out_path}"', env="conanrun")
        with open(out_path, encoding="utf-8") as f:
            out = f.read()

        assert "HMBS_TEST_PACKAGE_RESULT: PASS" in out, (
            f"test_package result line missing PASS: {out!r}"
        )
        assert "[FAIL]" not in out, f"test_package reported failures: {out!r}"
        assert "poselib_info(): PoseLib library version" in out, (
            f"poselib_info() assertion missing from output: {out!r}"
        )
        assert "p3p recovered ground-truth pose" in out, (
            f"P3P pose-recovery assertion missing from output: {out!r}"
        )
        assert "homography_4pt recovered H" in out, (
            f"homography_4pt assertion missing from output: {out!r}"
        )
        print("[PASS] poselib consumer verified: poselib_info() + P3P pose recovery + homography_4pt")
