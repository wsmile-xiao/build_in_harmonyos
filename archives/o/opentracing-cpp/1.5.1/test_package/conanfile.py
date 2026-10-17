#!/usr/bin/env python3
"""Conan test_package for opentracing-cpp 1.5.1.

Consumer test (R34): builds a small C++ program that includes only the
installed public headers (<opentracing/tracer.h> etc.), links the exported
target OpenTracing::opentracing, calls MakeNoopTracer()/StartSpan()/Finish()
and asserts observable results (span non-null, operation-name round-trip).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpentracingCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Run the consumer binary directly as well (observable output).
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "consumer_opentracing"),
            env="conanrun",
        )