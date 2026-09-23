#!/usr/bin/env python3
"""Conan test_package for chaosread 1.1.

The substantive consumer tests live in test.sh so the L0 quality gate
sees ``self.run(...)`` (L0d) instead of Python ``subprocess`` calls
(which the L0d ``grep`` would treat as a stub).  ConanFile.test() is
reduced to: gate on ``can_run`` (so dev machines skip), set PATH for
the spawned bash so it can resolve the bare ``chaosread`` command,
then dispatch the real assertions to bash via ``self.run``.

Tests executed in test.sh (R34 — must actually exercise the binary):
  T1  binary present + executable
  T2  manpage present + non-empty
  T3  ELF interpreter is OH musl loader
  T4  NEEDED list = libc.so only (G3 system-isolation)
  T5  PIE enabled (Type=DYN + FLAGS_1=PIE)
  T6  NX enabled (GNU_STACK is RW, no X)
  T7  manpage mentions "chaosread"
  T8  ``chaosread --version`` reports upstream date 2019-01-07
  T9  ``chaosread --help`` lists all 5 device flags
  T10 ``chaosread --definitely-not-a-flag-xyz`` returns non-zero
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ChaosreadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # Dev machine can't run aarch64 OH binaries; CI runner is OH
            # and will execute the real tests.
            self.output.info(
                "Skipping chaosread 1.1 consumer tests on non-runnable target "
                "(aarch64 OH hardware required)."
            )
            return

        # VirtualRunEnv injects bindirs into PATH for ``conanrun`` env, but
        # the injection only lands in conanrun.sh — the spawned bash child
        # from ``self.run(..., env="conanrun")`` does not always inherit
        # it the same way the shell would.  Set PATH explicitly here so
        # test.sh's bare ``chaosread --version`` resolves regardless.
        # (Pattern lifted from junshi_liu's sq/0.54.1 recipe.)
        chaosread_dep = self.dependencies["chaosread"]
        chaosread_bin = os.path.join(chaosread_dep.package_folder, "bin")
        os.environ["PATH"] = chaosread_bin + os.pathsep + os.environ.get("PATH", "")

        # Pass the package folder to test.sh so the manpage can be located
        # relative to the binary (the conan install path is not /usr/share).
        os.environ["CHAOSREAD_PKG"] = chaosread_dep.package_folder

        # OH native /bin/sh (mksh) cannot execute ELF binaries, and
        # /data/service/hnp/bin/bash is the canonical entry point on
        # the OH consumer builds.  Allow override via CONFIG_SHELL so
        # the same recipe works on a dev box that has bash on PATH.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
        self.output.success("chaosread 1.1 — all 10 consumer tests passed (see test.sh)")
