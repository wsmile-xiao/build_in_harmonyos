#!/usr/bin/env python3
"""Conan test_package for tmatrix 1.4 (HarmonyOS PC / OHOS aarch64).

tmatrix ships a CLI executable, not a library, so the tests execute the
packaged binary and assert on its real behaviour (see test_tmatrix.sh):

  - argument parsing: --version, --help, rejection of an unknown option and of
    an out-of-range --steps-per-sec value;
  - the ncurses render loop: launched under a pseudo-terminal with a fractional
    --fall-speed range (the 1.4 feature), the process must reach the curses
    code, and a painted frame must reach the pty when a terminfo database is
    reachable.

Cross builds execute the OHOS aarch64 ELF through qemu-aarch64 so the tests
are real runs rather than a compile-only gate. A native OHOS run executes the
packaged binary where it sits.

The binary is executed in place, straight out of the package folder. Two
earlier revisions instead copied it to another filesystem and chmod'ed it,
chasing an "HMDFS does not honour the executable bit" theory; CI disproved
that (build #64894 still returned 126 from /data/storage/el2/base/cache). The
real gate is E077: the OHOS kernel only loads an ELF carrying a *valid*
`.codesign` section, and chmod or relocating the file cannot substitute for
one. The recipe now self-signs in package(), which is what makes the exec
succeed from the package folder (qastools/1.4.0 precedent).
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class TmatrixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Direct requirement so the ncurses runenv (TERMINFO / TERMINFO_DIRS)
        # is aggregated into the conanrun environment the tests execute in.
        self.requires("ncurses/6.6")

    def _runner_prefix(self):
        """Return the command prefix needed to execute the packaged binary.

        An OHOS aarch64 ELF cannot run on an x86_64 build host, so fall back to
        qemu-aarch64. The OHOS dynamic loader is provided by the sysroot passed
        with -L when one is available; a fully static binary needs no -L.
        """
        if platform.machine() in ("aarch64", "arm64"):
            return []
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise ConanInvalidConfiguration(
                "qemu-aarch64 is required to run the tmatrix test package on "
                f"{platform.machine()}"
            )
        prefix = [qemu]
        for candidate in ("/root/ohos-run-prefix", "/data/service/hnp"):
            if os.path.isfile(os.path.join(candidate, "lib", "ld-musl-aarch64.so.1")):
                prefix.extend(["-L", candidate])
                break
        return prefix

    def test(self):
        dep = self.dependencies["tmatrix"]
        exe = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "tmatrix")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration(f"packaged tmatrix not found: {exe}")
        if not os.access(exe, os.X_OK):
            raise ConanInvalidConfiguration(
                f"packaged tmatrix is not executable (mode {oct(os.stat(exe).st_mode)}): {exe}"
            )

        runner = self._runner_prefix()
        script = os.path.join(self.source_folder, "test_tmatrix.sh")
        self.run('sh "{}" "{}" {}'.format(script, exe, " ".join(runner)).strip(),
                 env="conanrun")
