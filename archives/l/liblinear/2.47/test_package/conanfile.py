#!/usr/bin/env python3
"""Conan consumer tests for liblinear 2.47."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import save


class LiblinearTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dependency = self.dependencies["liblinear"]
        libdir = os.path.join(dependency.package_folder, "lib")
        if libdir not in os.environ.get("LD_LIBRARY_PATH", ""):
            os.environ["LD_LIBRARY_PATH"] = (
                libdir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
            )

        # 1. API smoke test (library link + train + predict round-trip)
        self.run(
            f'"{os.path.join(self.build_folder, "test_liblinear")}"',
            env="conanrun",
        )

        # 2. Upstream CLI workflow: train heart_scale-style data, then predict
        dataset = os.path.join(self.build_folder, "heart_scale")
        model = os.path.join(self.build_folder, "heart_scale.model")
        predictions = os.path.join(self.build_folder, "output")
        save(
            self,
            dataset,
            "+1 1:0.708333 2:1 3:1 4:-0.320755 5:-0.105023 6:-1 7:1 8:-0.419847 9:-1 10:-0.225806 12:1 13:-1\n"
            "-1 1:0.583333 2:-1 3:0.333333 4:-0.603774 5:1 6:-1 7:1 8:0.358779 9:-1 10:-0.483871 12:-1 13:1\n"
            "+1 1:0.333333 2:1 3:-1 4:0.117647 5:-0.384615 6:-1 7:-1 8:0.283019 9:-1 10:0.193548 12:1 13:-1\n"
            "-1 1:0.375 2:-1 3:0 4:-0.264151 5:-0.215054 6:1 7:-1 8:0.0841126 9:-1 10:0.129032 12:1 13:-1\n"
            "+1 1:0.916667 2:1 3:1 4:-0.0754717 5:0.052356 6:1 7:1 8:0.451087 9:1 10:0.0 12:-1 13:1\n"
            "-1 1:0.166667 2:-1 3:-1 4:0.0566038 5:-0.41899 6:1 7:-1 8:0.0373832 9:1 10:0.0 12:1 13:-1\n"
            "+1 1:0.5 2:1 3:1 4:-0.132075 5:0.199441 6:1 7:-1 8:0.157327 9:-1 10:0.0967742 12:1 13:1\n"
            "-1 1:0.166667 2:-1 3:-1 4:0.0566038 5:0.199441 6:1 7:-1 8:0.1 9:-1 10:0.0 12:1 13:-1\n",
        )

        bindir = os.path.join(dependency.package_folder, "bin")
        self.run(
            f'"{os.path.join(bindir, "train")}" "{dataset}" "{model}"',
            env="conanrun",
        )
        self.run(
            f'"{os.path.join(bindir, "predict")}" "{dataset}" "{model}" "{predictions}"',
            env="conanrun",
        )
        with open(predictions, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if len(lines) != 8:
            raise Exception(
                f"predict output should contain 8 lines, got {len(lines)}"
            )
        expected = ["1", "-1", "1", "-1", "1", "-1", "1", "-1"]
        if lines != expected:
            raise Exception(
                f"predict labels mismatch: expected {expected}, got {lines}"
            )
        print("liblinear train/predict workflow OK: accuracy 8/8")
