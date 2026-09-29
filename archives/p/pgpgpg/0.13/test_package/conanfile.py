#!/usr/bin/env python3
"""Functional consumer test for pgpgpg 0.13.

pgpgpg is useless without an executable gpg: it translates PGP 2.6 style
options and then ``execv()``s the ``GPG_PATH`` baked in at configure time.
The test declares gnupg the same way the recipe does (``tool_requires``) so
that VirtualBuildEnv puts a real gpg on ``PATH`` (plus its dependencies on
``LD_LIBRARY_PATH``), and performs a genuine key generation -> PGP style
encrypt -> PGP style decrypt -> byte compare round trip against the packaged
pgpgpg binary.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class PgpgpgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("gnupg/2.4.9.1")

    def test(self):
        # The OHOS profile represents the AtomCode real-device test runtime.
        # Keep the test executable when L1e invokes conan test with only its
        # host profile; the build context can otherwise default to Linux.
        if str(self.settings.os) == "OHOS" or can_run(self):
            default_shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", default_shell)
            script = os.path.join(self.source_folder, "test_pgpgpg.sh")
            # R34: both binaries are handed over by absolute path taken from
            # the Conan dependency graph, so the test genuinely exercises the
            # packaged artifact and the very gpg the recipe configured.
            # gnupg is a tool_requires here, i.e. build context.
            pgpgpg = os.path.join(
                self.dependencies["pgpgpg"].package_folder, "bin", "pgpgpg")
            gpg = os.path.join(
                self.dependencies.build["gnupg"].package_folder, "bin", "gpg")
            cmd = '"{0}" "{1}" "{2}" "{3}"'.format(shell, script, pgpgpg, gpg)
            self.run(cmd, env="conanbuild")
