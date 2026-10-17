#!/usr/bin/env python3
"""Conan test_package — L1 consumer test for libkml.

Builds a C++ consumer that actually calls the installed libkml API
(R34: no print-only shell). It links libkml::libkml and:
  - reads kmlbase::Version::GetString()
  - parses a small KML document via kmlengine::KmlFile::CreateFromParse
    (exercises expat + zlib + uriparser consumer path).
Runs under an environment whose LD_LIBRARY_PATH covers every dependency's
libdirs (the Conan-generated conanrun env alone does not always include all
transitive shared libs, e.g. minizip).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibkmlTestConan(ConanFile):
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
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        envvars = env.vars(self, scope="run")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libkml")
        with envvars.apply():
            self.run(bin_path)
