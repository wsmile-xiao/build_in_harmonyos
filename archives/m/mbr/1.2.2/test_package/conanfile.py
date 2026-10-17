#!/usr/bin/env python3
"""Conan test_package for mbr 1.2.2 — HarmonyOS PC (aarch64).

R34: the test must substantially exercise the installed package. mbr ships the
`install-mbr` command line tool, so every check below runs that binary and
verifies the effect it has on a real 512 byte disk image.

A freshly prepared target must already carry the 0x55AA boot signature,
otherwise install-mbr refuses it unless --force is given.

Checks:
   1. install-mbr --version            binary installed and runnable
   2. install-mbr --help               usage/options listing
   3. install onto a signature-valid target                  -> exit 0
   4. installed image is still 512 bytes, signature 0x55AA kept
   5. MBR code written into 0..439                           (target changed)
   6. partition table + disk signature area 440..509 preserved
   7. install-mbr -l <img>             reads the parameters back
   8. install-mbr -n <img>             no-op leaves the image byte-identical
   9. install-mbr --force <zero img>   sanity-check override works
  10. install-mbr <short target>       refused with a non-zero exit code
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import load


class MbrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        work = self.build_folder
        target = os.path.join(work, "test-mbr.img")

        # A target install-mbr accepts: 510 zero bytes + the boot signature
        with open(target, "wb") as fh:
            fh.write(b"\x00" * 510 + b"\x55\xaa")
        original = open(target, "rb").read()

        # 1./2. binary is installed and runnable, options are listed
        self.run("install-mbr --version", env="conanrun")
        self.run("install-mbr --help", env="conanrun")

        # 3. install the boot record
        self.run('install-mbr "%s"' % target, env="conanrun")

        # 4./5./6. the install must rewrite the code but keep the table area
        installed = open(target, "rb").read()
        assert len(installed) == 512, "image size changed: %d bytes" % len(installed)
        assert installed[510:512] == b"\x55\xaa", "boot signature was lost"
        assert installed[:440] != original[:440], "no MBR code was written"
        assert installed[440:510] == original[440:510], \
            "partition table / disk signature area was modified"

        # 7. read the parameters back out of the installed image
        listing = os.path.join(work, "params.txt")
        self.run('install-mbr -l "%s" > "%s"' % (target, listing), env="conanrun")
        params = load(self, listing)
        for field in ("Version:", "Compatible:", "Drive:", "Timeout:"):
            assert field in params, "field %s missing from the -l output" % field

        # 8. -n (no-op) must not touch the image
        noop = os.path.join(work, "test-noop.img")
        with open(noop, "wb") as fh:
            fh.write(installed)
        self.run('install-mbr -n "%s"' % noop, env="conanrun")
        assert open(noop, "rb").read() == installed, "-n modified the image"

        # 9. --force installs onto an image without a boot signature
        forced = os.path.join(work, "test-force.img")
        with open(forced, "wb") as fh:
            fh.write(b"\x00" * 512)
        self.run('install-mbr --force "%s"' % forced, env="conanrun")
        assert open(forced, "rb").read()[510:512] == b"\x55\xaa", \
            "--force did not install the boot record"

        # 10. a target that is too short must be refused
        short = os.path.join(work, "test-short.img")
        with open(short, "wb"):
            pass
        try:
            self.run('install-mbr "%s"' % short, env="conanrun")
        except ConanException:
            pass
        else:
            raise ConanException("install-mbr accepted a 0 byte target")
