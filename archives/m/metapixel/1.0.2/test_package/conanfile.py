#!/usr/bin/env python3
"""test_package for metapixel 1.0.2 - real consumer test of the packaged binaries.

R34: this test really executes the delivered executables and asserts on real
artifacts.  test.sh drives the public two-phase metapixel workflow

    metapixel --prepare <tile> <thumb> <libdir>/tables.mxt
    metapixel --library <libdir> --metapixel <source> <out>

against PNG/JPEG/GIF inputs materialised at run time by gen_images.py, and
checks the produced mosaics with the delivered metapixel-imagesize helper plus
file-magic checks.  A package that shipped no binary, or whose format
backends were broken, cannot pass: the artifact checks live in this
conanfile, the image decoding assertions live in test.sh.

The fixtures are generated rather than committed because the CI worker
checks a PR out as a text .diff and GitCode's diff endpoint carries no binary
payload - a committed .png fails the whole checkout with "missing binary
patch data".  gen_images.py writes PNG and GIF from scratch with the standard
library only; the one JPEG fixture is an embedded base64 constant with a
pinned SHA256.

No CMakeToolchain on purpose: this toolchain has no HarmonyOS platform
module, so even a trivial project() fails compiler identification
(smemstat / dhcpoptinj precedent).  Nothing needs to be compiled here anyway
- the thing under test is the packaged executable.

Runner selection: on a native OHOS aarch64 worker the binaries are executed
directly.  Where aarch64 binfmt_misc is wired up (the local WSL cross-build
host) the OHOS loader hands them to qemu-aarch64.  If neither is possible the
run fails loudly rather than reporting a silent pass.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class MetapixelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bin(self, name):
        dep_pkg = self.dependencies[self.tested_reference_str].package_folder
        return os.path.join(dep_pkg, "bin", name)

    def _assert_artifacts(self):
        """Every claim below depends on these exact files existing."""
        for name in ("metapixel", "metapixel-imagesize", "convert",
                     "metapixel-prepare", "metapixel-sizesort"):
            path = self._bin(name)
            if not os.path.isfile(path):
                raise ConanException(f"packaged artifact missing: {path}")
            if not os.access(path, os.X_OK):
                raise ConanException(f"packaged artifact not executable: {path}")
        man = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                           "share", "man", "man1", "metapixel.1")
        if not os.path.isfile(man):
            raise ConanException(f"packaged man page missing: {man}")
        licence = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                               "licenses", "COPYING")
        if not os.path.isfile(licence):
            raise ConanException(f"packaged licence missing: {licence}")

    def _shell(self):
        """Shell able to exec a native ELF on this host.

        On the OHOS aarch64 worker /system/bin/sh is mksh, which cannot exec
        ELF binaries at all, so the profile exports CONFIG_SHELL pointing at
        the HNP bash - every merged executable recipe in this repo relies on
        that.  Elsewhere (and on an x86_64 host that has binfmt_misc wired up
        for aarch64) a plain /bin/sh runs the script and the loader hands the
        OHOS binaries to the emulator.
        """
        candidates = [os.environ.get("CONFIG_SHELL"), "/bin/bash", "/bin/sh"]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return "sh"

    def test(self):
        # Assert the real deliverables before running anything, so a package
        # that shipped nothing fails here instead of looking like a pass.
        self._assert_artifacts()

        script = os.path.join(self.source_folder, "test.sh")
        generator = os.path.join(self.source_folder, "gen_images.py")
        if not os.path.isfile(script):
            raise ConanException(f"test source missing: {script}")
        if not os.path.isfile(generator):
            raise ConanException(f"fixture generator missing: {generator}")

        # env="conanrun" carries the dependency runenv (libpng / libjpeg /
        # giflib shared objects).  Each binary is addressed by the absolute
        # path conan resolved for this package, so the test can never pick up
        # a same-named system executable from PATH.
        self.run(
            f'"{self._shell()}" "{script}"'
            f' "{self._bin("metapixel")}"'
            f' "{self._bin("metapixel-imagesize")}"'
            f' "{self._bin("convert")}"'
            f' "{generator}"',
            env="conanrun")
