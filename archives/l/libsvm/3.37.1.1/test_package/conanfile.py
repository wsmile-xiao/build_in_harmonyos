#!/usr/bin/env python3
"""Conan consumer tests for libsvm 3.37.1.1."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import save


class LibsvmTestConan(ConanFile):
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
        dependency = self.dependencies["libsvm"]
        libdir = os.path.join(dependency.package_folder, "lib")
        if libdir not in os.environ.get("LD_LIBRARY_PATH", ""):
            os.environ["LD_LIBRARY_PATH"] = (
                libdir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
            )

        self.run(os.path.join(self.build_folder, "test_libsvm"), env="conanrun")

        dataset = os.path.join(self.build_folder, "sample.libsvm")
        scaled = os.path.join(self.build_folder, "sample.scaled")
        model = os.path.join(self.build_folder, "sample.model")
        predictions = os.path.join(self.build_folder, "sample.predictions")
        save(
            self,
            dataset,
            "-1 1:-2 2:-1\n-1 1:-1 2:-2\n1 1:1 2:2\n1 1:2 2:1\n",
        )

        bindir = os.path.join(dependency.package_folder, "bin")
        self.run(
            f'"{os.path.join(bindir, "svm-scale")}" "{dataset}" > "{scaled}"',
            env="conanrun",
        )
        self.run(
            f'"{os.path.join(bindir, "svm-train")}" -t 0 "{scaled}" "{model}"',
            env="conanrun",
        )
        self.run(
            f'"{os.path.join(bindir, "svm-predict")}" "{scaled}" "{model}" "{predictions}"',
            env="conanrun",
        )
