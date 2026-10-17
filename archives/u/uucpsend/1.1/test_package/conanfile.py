#!/usr/bin/env python3
"""Conan test_package for uucpsend 1.1.

R34: this test substantially depends on the tested package -- it locates the
packaged ``bin/uucpsend`` through the Conan dependency graph and executes it.
There is no way to satisfy the assertions below without a working binary.

The assertions target the parts of uucpsend that are observable without an
INN/UUCP deployment, which is all a standalone package can honestly claim:

  * control-file parsing (the per-site line format and the field order),
  * the site-selection / ``-f`` appendix code paths,
  * the log writer's stderr fallback when the compiled-in log directory is
    absent,
  * the exit statuses the control-file failure paths produce.

The batch-driving path (ctlinnd flush -> batcher -> uux) is what the runtime
prerequisites in manifest.yaml cover; it needs a live INN spool, so it is not
asserted here.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class UucpsendTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bindir = os.path.join(self.dependencies["uucpsend"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_uucpsend.sh")
        self.run(
            'sh "{}" "{}"'.format(script, os.path.join(bindir, "uucpsend")),
            env="conanrun",
        )
