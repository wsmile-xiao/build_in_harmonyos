#!/usr/bin/env python3
"""Conan test_package for libtatsu — offline TSS contract verification.

libtatsu talks to Apple's TSS signing server over HTTP(S). The public API
entry point tss_request_send(plist_t request, const char* server_url_string)
takes an explicit server URL, which allows pointing it at a local mock
HTTP server (127.0.0.1) instead of the real gs.apple.com endpoints.

This test package verifies, fully offline (no public network access):
  - C and C++ consumers can include the public headers and link
  - request object creation, parameter/manifest handling and overrides
  - request serialization into the exact XML the TSS protocol expects
  - successful response parsing (MESSAGE=SUCCESS + embedded plist)
  - negative paths: HTTP non-2xx, connection failure, malformed responses,
    missing required fields, NULL/empty inputs
  - response ticket/path/blob accessors
  - memory ownership and cleanup

The mock server fixture is generated programmatically (in-process socket
listener); no real device identity, certificate, or Apple account is used.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtatsuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # explicit dep for CMakeDeps: test code uses libplist API directly
        self.requires("libplist/2.3.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run both consumer binaries directly (CI L1 requires self.run()):
        # the C consumer (full offline + mock-server contract suite) and
        # the C++ consumer (extern "C" ABI verification).
        for binary in ("test_package", "test_cpp"):
            bin_path = os.path.join(self.cpp.build.bindirs[0], binary)
            self.run(bin_path, env="conanrun")
