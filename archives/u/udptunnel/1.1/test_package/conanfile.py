#!/usr/bin/env python3
"""Conan test_package for udptunnel — CLI contract assertions.

udptunnel is a tunnel tool: its UDP/TCP data plane needs a live network
topology, so headless consumer assertions target the CLI contract layer
(see test.c and the self.run checks below).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UdptunnelTestConan(ConanFile):
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
        # K0: --help prints usage and exits 0
        self.run("udptunnel --help", env="conanrun")
        # usage banner goes to stdout
        self.run("bash -c 'udptunnel --help | grep -q \"Usage:\"'", env="conanrun")
        # upstream error contract preserved: no args exits 2
        self.run("bash -c 'udptunnel > /dev/null 2>&1; test $? -eq 2'", env="conanrun")
