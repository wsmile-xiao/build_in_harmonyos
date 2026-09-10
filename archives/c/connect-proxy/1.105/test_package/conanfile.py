#!/usr/bin/env python3
"""Conan test_package — connect-proxy 1.105 CLI tool verification.

connect-proxy is a CLI relay tool, not a library, so the test binary receives
the path of the installed `connect-proxy` executable and drives it end-to-end
against in-process TCP/HTTP-proxy/SOCKS5 servers (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ConnectProxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        connect_bin = os.path.join(
            self.dependencies["connect-proxy"].package_folder, "bin", "connect-proxy"
        )
        test_bin = os.path.join(self.build_folder, "test_connect")
        self.run(f'"{test_bin}" "{connect_bin}"', env="conanrun")
