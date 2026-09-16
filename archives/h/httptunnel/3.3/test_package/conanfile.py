#!/usr/bin/env python3
"""Conan test_package for httptunnel — CLI tools (hts/htc) verification.

Verifies that the installed httptunnel binaries work by:
1. Running hts/htc --version (real execution, version output asserted)
2. Starting a real hts server with a real destination (python echo server)
3. Starting a real htc client with a local forward port
4. Connecting to htc's forward port to trigger the tunnel, then asserting
   that the connection was accepted and that hts established the forwarded
   connection to the destination (marker file written by the echo server)

Known OHOS limitation (documented in notes.md): the tunnel DATA return
path (htc reading the GET leg via poll) reports a bogus revents bitmap on
OHOS and the tunnel tears down; this test asserts the parts that work
(listening, accepting, tunnel handshake, destination forwarding) and not
the data return path.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class HttptunnelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Fixtures are plain python3 scripts shipped alongside; nothing to compile.
        pass

    def test(self):
        if can_run(self):
            dep = self.dependencies["httptunnel"]
            bindir = dep.cpp_info.bindirs[0]
            hts = os.path.join(bindir, "hts")
            htc = os.path.join(bindir, "htc")
            script = os.path.join(self.source_folder, "test_httptunnel.sh")
            self.run(f'sh "{script}" "{hts}" "{htc}" "{self.source_folder}"',
                     env="conanrun")
