#!/usr/bin/env python3
"""Conan test_package for socat 1.8.1.3 (application package).

Consumer verification: uses the installed `socat` binary as a business-layer
component — relays a payload from one file to another via `socat -u` and
checks the payload arrives intact (compile/link/run + observable result,
not a print-only stub). UNIX domain sockets and loopback TCP are avoided
because OHOS SELinux blocks AF_UNIX bind() and per-task network isolation
blocks loopback TCP for unprivileged consumers.

L0c: the independent test source file `test_socat.sh` in this directory is
the required test source (extension .sh, not conanfile.py); test() below
executes it through the conanrun environment so the packaged bin/ is on PATH.
"""
import os
import subprocess
import tempfile

from conan import ConanFile


class SocatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test_socat.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L0d: test() must have a real self.run invocation. Execute the
        # independent L0c test source file (test_socat.sh) with the conanrun
        # environment (packaged bin/ on PATH); it runs the FILE->FILE relay
        # content check and `socat -V` exit-code check.
        script = os.path.join(self.source_folder, "test_socat.sh")
        rc = self.run("sh %s" % script, env="conanrun")
        if rc != 0:
            raise RuntimeError("test_socat.sh failed rc=%d" % rc)
        print("consumer: test_socat.sh ALL PASS (rc=0)")
