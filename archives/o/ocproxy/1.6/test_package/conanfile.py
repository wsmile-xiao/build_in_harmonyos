#!/usr/bin/env python3
"""Consumer test for the packaged ocproxy 1.6 executables.

The actual gate lives in run_test.py: it starts the packaged ocproxy on a real
SOCKS5 port and a real local-forward port, negotiates SOCKS5 over the socket
and checks that the request is handed to the VPNFD tunnel.  Python is used
because the OHOS targets have no `socat`/`nc` and because a real protocol
handshake (not a print-only assertion) is required.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class OcproxyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "run_test.py"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies["ocproxy"].package_folder, "bin")
        script = os.path.join(self.source_folder, "run_test.py")
        self.run('"%s" "%s" "%s"' % (self._python(), script, bindir), env="conanrun")

    def _python(self):
        import shutil

        found = shutil.which("python3") or shutil.which("python")
        if not found:
            raise ConanInvalidConfiguration(
                "the ocproxy integration test needs a python3 interpreter"
            )
        return found
