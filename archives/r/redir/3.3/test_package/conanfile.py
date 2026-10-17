#!/usr/bin/env python3
"""Conan test_package — redir 3.3.

redir is a CLI-only tool (TCP port redirector).  There is no library
artifact to link against, so instead of the default CMake find_package
consumer, this test_package validates the packaged `redir` binary from a
consumer perspective:

  L1 (consumer smoke): `redir -h` exits 0 and prints usage.
  R34 (consumer E2E):  start a local echo listener, run the installed
  `redir` binary in foreground (-n) forwarding a source port to the echo
  port, push a payload through the tunnel and assert the exact echo
  comes back — proving a real application can compile/run and use the
  installed tool's public CLI without any private headers or internals.
"""
import os

from conan import ConanFile


class RedirTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the packaged CLI via the declared bindir
        redir = os.path.join(self.dependencies["redir"].package_folder,
                             "bin", "redir")
        if not os.path.isfile(redir):
            raise RuntimeError(f"redir binary not found at {redir}")
        self.run(f"/bin/sh test_redir.sh {redir}", env="conanrun")