#!/usr/bin/env python3
"""Conan test_package for d-shlibs — real execution of both shipped tools (R34).

d-shlibs ships no library; it is a pair of bash scripts. A meaningful consumer
test therefore *runs* them instead of linking against them:

  * `bash -n'      -> upstream `make check' step 1 (syntax gate)
  * d-shlibmove    -> the exact scenario of upstream's autopkgtest
                      (debian/tests/uppercase.d): a compiled
                      libUppercase.so -> libUppercase.so.1.0.0 chain plus a
                      debian/control, then the installed d-shlibmove is run and
                      its dry-run exit code (2) and computed move plan are
                      asserted. d-shlibmove internally calls d-devlibdeps, so
                      the emitted debian/libuppercase1-dev.substvars is
                      asserted as well.
  * d-devlibdeps   -> standalone run asserting the emitted
                      `devlibs:Depends=' substvar file

The harness bridges two OHOS platform gaps (documented in notes.md):
  * there is no /bin/bash (only /bin/sh) while both upstream scripts start with
    `#!/bin/bash' -> every script is started through the resolved absolute bash
    and a `d-devlibdeps' wrapper is placed on PATH for the internal call that
    d-shlibmove makes;
  * there is no GNU-triplet-prefixed binutils -> `$DEB_HOST_GNU_TYPE-objdump' is
    shimmed to the binutils package objdump; the triplet is queried from
    dpkg-architecture at runtime (aarch64-linux-gnu), never hardcoded.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DshlibsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep_folder(self, name):
        """Package folder of a (transitive) dependency, or '' if unknown."""
        try:
            for _ref, dep in self.dependencies.items():
                if dep.ref.name == name:
                    return dep.package_folder or ""
        except Exception:  # noqa: BLE001 - graph probing is best effort
            pass
        return ""

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: not runnable on this host, "
                             "skipping the runtime consumer test")
            return
        pkg = self.dependencies["d-shlibs"].package_folder
        dpkg = self._dep_folder("dpkg")
        binutils = self._dep_folder("binutils")
        script = os.path.join(os.path.dirname(__file__), "test_dshlibs.py")
        # L0d / PF3: the consumer test must be driven through self.run().
        self.run(f'python3 "{script}" "{pkg}" "{dpkg}" "{binutils}"',
                 env="conanrun")
