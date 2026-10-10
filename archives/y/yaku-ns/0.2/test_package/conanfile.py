#!/usr/bin/env python3
"""test_package for yaku-ns 0.2 — consumer tests against the packaged binaries.

Nothing here is a stub: every check runs the *packaged* ``bin/yaku-ns`` and
``bin/yaku-getzone``.  Three test programs, 15 assertions total:

  test_cli.py        5 assertions — --version / --help / bad-option / usage text
                               for both commands (runs everywhere, including a
                               plain Linux build host).
  test_dns_service.py 7 assertions — starts the packaged daemon on a loopback
                               high port with a generated zone and checks real DNS
                               traffic: A / NXDOMAIN / MX / TXT / NS over UDP plus
                               a TCP SOA query.
  test_elf_abi.py    3 assertions — the packaged ELFs are 64-bit little-endian
                               AArch64, i.e. the OHOS target really was produced.

``test_dns_service.py`` needs a runnable target, so ``test()`` fails loudly
instead of skipping when the build is cross-only: the whole point of this
package is a working DNS server, and a silently skipped runtime test would hide
exactly the regressions that matter here.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run


class YakunsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _python(self):
        """Interpreter used to run the three test programs.

        The CI worker exposes its HNP python at a fixed path and also on PATH;
        sys.executable is the interpreter running Conan itself, which is by
        construction the one whose site-packages can import what these tests
        need (they only use the standard library, but keeping a single
        interpreter avoids mixing a host python with an OHOS one).
        """
        return sys.executable or "python3"

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        daemon = os.path.join(bindir, "yaku-ns")
        getzone = os.path.join(bindir, "yaku-getzone")

        for path in (daemon, getzone):
            if not os.path.isfile(path):
                raise RuntimeError(f"packaged command missing: {path}")

        python = self._python()
        tests = os.path.join(self.source_folder, "test_cli.py")
        self.run(f'"{python}" "{tests}" "{daemon}" "{getzone}"')

        # The ELF header check only reads bytes off disk, so it needs no
        # runnable target and runs before the can_run() gate below.
        elf_test = os.path.join(self.source_folder, "test_elf_abi.py")
        self.run(f'"{python}" "{elf_test}" "{daemon}" "{getzone}" '
                 f'"{self.settings.arch}"')

        if not can_run(self):
            raise RuntimeError(
                "yaku-ns test_package requires a runnable target: the DNS "
                "service test starts the packaged daemon and exchanges real DNS "
                "packets with it. Skipping it on a cross-only host would hide "
                "the regressions this package exists to catch."
            )

        dns_test = os.path.join(self.source_folder, "test_dns_service.py")
        # Conan's default test_package build folder *is* this directory, so the
        # generated zone and daemon log would otherwise be left behind as
        # untracked files inside the package tree.  Both are removed again below.
        workdir = os.path.join(self.build_folder, "dns-test")
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)
        try:
            self.run(f'"{python}" "{dns_test}" "{daemon}" "{workdir}"')
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
