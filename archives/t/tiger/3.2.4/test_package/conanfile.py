#!/usr/bin/env python3
"""Conan test_package for tiger 3.2.4.

The test runs ``test_tiger.sh`` against the package folder.  It exercises the
real artifacts of the package instead of just printing something:

* the three installed commands ``bin/tiger``, ``bin/tigexp``, ``bin/tigercron``
  and their shebang interpreters,
* the five helper binaries built from ``c/`` (``md5``, ``snefru``, ``realpath``,
  ``getpermit``, ``testsuid``),
* both patched hot spots: the 32-bit hash word types of ``md5``/``snefru``
  (RFC 1321 and upstream Snefru vectors) and the ``/system/bin`` command search
  path of ``tigexp`` (message explanation lookup through ``doc/explain.idx``).
"""
import os
import shutil

from conan import ConanFile


class TigerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _shell():
        """Pick a POSIX shell that exists and is executable on this machine."""
        candidates = [
            "/system/bin/sh",                       # HarmonyOS toybox shell
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/bin/sh",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) \
                    and os.access(candidate, os.X_OK):
                return candidate
        return "sh"

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_tiger.sh")
        self.run(f'"{self._shell()}" "{script}" "{package_folder}"', env="conanrun")
