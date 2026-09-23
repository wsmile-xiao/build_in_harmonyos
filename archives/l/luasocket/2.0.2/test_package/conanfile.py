#!/usr/bin/env python3
"""Consumer test for luasocket 2.0.2.

Builds a small C program that embeds a Lua 5.1 interpreter, sets
package.path/package.cpath to point at the installed luasocket package, then
runs a Lua script that requires "socket", "mime", "socket.url", "ltn12" and
"socket.http" and exercises their APIs (TCP socket creation, DNS lookup,
MIME base64 round-trip, URL parse/build).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LuasocketTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CMakeDeps needs the lua target for linking the embedded interpreter.
        self.requires("lua/5.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["luasocket"].package_folder
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_luasocket")
        self.run(f'"{test_bin}" "{package}"', env="conanrun")
