#!/usr/bin/env python3
"""Conan test_package for socket — runs the packaged binary (R34).

The upstream tarball ships no test suite at all and the Debian packaging has
no autopkgtest either, so this test_package drives the packaged `socket`
executable over a loopback TCP connection: client mode, server mode, `-c`
CRLF translation, `-p` program plumbing and the patched SIGTERM handler.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SocketTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bindirs = self.dependencies[self.tested_reference_str].cpp_info.bindirs
        bindir = bindirs[0] if bindirs else ""
        script = os.path.join(self.source_folder, "test_socket.py")
        self.run(f'python3 "{script}" "{bindir}"', env="conanrun")
