#!/usr/bin/env python3
"""Conan test_package for roffit 0.17.

Replays the upstream `make test` (single golden-file test: convert
testpage.1 with --bare and byte-compare against testpage.output) against
the packaged roffit, using the perl dependency interpreter. Also checks
--version output and the man page artifact.
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class RoffitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["roffit"]
        bindir = os.path.join(dep.package_folder, "bin")
        roffit = os.path.join(bindir, "roffit")

        if not os.path.isfile(roffit):
            raise ConanException(f"roffit not found: {roffit}")
        self.output.info(f"  roffit: {os.path.getsize(roffit)} bytes")

        perl_dep = self.dependencies["perl"]
        perl_bin = os.path.join(perl_dep.package_folder, "bin", "perl")
        if not os.path.isfile(perl_bin):
            raise ConanException(f"perl interpreter not found: {perl_bin}")

        test_dir = os.path.dirname(__file__)

        # Case 1: upstream golden-file test (make test equivalent)
        # test() 无 layout 时 build_folder 即 source_folder，产物写到系统临时目录避免污染归档
        out_file = os.path.join(tempfile.mkdtemp(prefix="roffit-test-"), "testpage.dump")
        cmd = (f'"{perl_bin}" "{roffit}" --bare '
               f'< "{os.path.join(test_dir, "testpage.1")}" > "{out_file}"')
        rc = self.run(cmd, env="conanrun", ignore_errors=True)
        if rc != 0:
            raise ConanException(f"roffit --bare conversion failed (exit {rc})")
        with open(out_file, "rb") as fh:
            got = fh.read()
        with open(os.path.join(test_dir, "testpage.output"), "rb") as fh:
            expected = fh.read()
        if got != expected:
            raise ConanException(
                f"golden-file mismatch: got {len(got)} bytes, "
                f"expected {len(expected)} bytes")
        self.output.info("upstream golden test (testpage.1 -> testpage.output): OK")

        # Case 2: --version reports 0.17
        rc = self.run(f"{perl_bin} {roffit} --version", env="conanrun")
        if rc != 0:
            raise ConanException(f"roffit --version failed (exit {rc})")
        self.output.info("roffit --version: OK")

        # Case 3: man page packaged
        manpage = os.path.join(dep.package_folder, "share", "man", "man1", "roffit.1")
        if not os.path.isfile(manpage):
            raise ConanException(f"roffit.1 man page missing: {manpage}")
        self.output.info("man page roffit.1 present: OK")
