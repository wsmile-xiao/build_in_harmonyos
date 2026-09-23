#!/usr/bin/env python3
"""Conan test_package — ncrack 0.7 consumer run of the installed tool.

R34/PF3: the test really EXECUTES the packaged `ncrack` binary, it does not
merely print.  Two deterministic, platform-independent assertions:

1. `ncrack --version` — identity check (version string + module table, which
   is only printed by a build that linked OpenSSL).
2. a real scan of a closed local port (`127.0.0.1:9`) — the scan engine,
   nsock event loop and output layer actually run end to end, and no
   credentials can be discovered on a closed port.

The data directory (share/ncrack: ncrack-services + lists/) is passed
explicitly with --datadir because the binary's compiled-in NCRACKDATADIR is
an absolute path ("/share/ncrack" under the recipe's --prefix=/).
"""

import os

from conan import ConanFile


class NcrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        ncrack = None
        datadir = None
        for dependency in self.dependencies.host.values():
            if dependency.ref.name != "ncrack":
                continue
            bindirs = dependency.cpp_info.bindirs or ["bin"]
            bindir = bindirs[0]
            if not os.path.isabs(bindir):
                bindir = os.path.join(dependency.package_folder, bindir)
            ncrack = os.path.join(bindir, "ncrack")
            datadir = os.path.join(dependency.package_folder, "share", "ncrack")
        if not ncrack or not os.path.isfile(ncrack):
            raise Exception("ncrack binary not found in package bindirs")
        if not os.path.isdir(datadir):
            raise Exception("ncrack data directory missing: %s" % datadir)

        script = os.path.join(os.path.dirname(__file__), "test_ncrack.sh")
        self.run('sh "%s" "%s" "%s"' % (script, ncrack, datadir),
                 env="conanrun")
