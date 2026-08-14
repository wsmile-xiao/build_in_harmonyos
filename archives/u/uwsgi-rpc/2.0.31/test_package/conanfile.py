#!/usr/bin/env python3
"""Conan test package for the uWSGI rpc plugin."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class UwsgiRpcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["uwsgi-rpc"]
        plugin = os.path.join(dep.package_folder, "lib", "uwsgi", "rpc_plugin.so")
        assert os.path.isfile(plugin), f"missing packaged plugin: {plugin}"
        if not can_run(self):
            self.output.info(
                "Cross-build context: packaged rpc plugin verified; runtime probe skipped"
            )
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_uwsgi_rpc")
        self.run(f'"{exe}" "{plugin}"', env="conanrun")
