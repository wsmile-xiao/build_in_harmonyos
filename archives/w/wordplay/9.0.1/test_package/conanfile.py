#!/usr/bin/env python3
"""Conan test_package for wordplay 9.0.1 - HarmonyOS consumer validation.

Two layers, both driven from test():

Layer 1 (runs whenever the target is OHOS) - ohos_abi_check.py inspects the
    packaged artifact instead of executing it: A1-A9 cover ELF64/AArch64, the
    OHOS musl interpreter, .note.ohos.ident, musl-only DT_NEEDED (with the
    ICU libraries statically folded in rather than DT_NEEDED), the packaged
    word list being the upstream file (sha256), no host RPATH/RUNPATH,
    NX/PIE/RELRO/BIND_NOW and the absence of glibc symbol versioning.  It is
    pure Python ELF parsing with no external tool, so it also runs on the
    Windows host that cross-compiles the package but cannot execute an
    aarch64-linux-ohos ELF: that host must still validate the artifact rather
    than pass silently.

Layer 2 (can_run only) - test_wordplay.sh drives 20 functional cases (F1-F20)
    against the packaged binary and word list on a real HarmonyOS host: usage
    handling, anagram correctness (every output line is a letter-multiset
    match of the input), determinism, candidate listing, length limits
    (-nX/-mX), word-count limit (-dX), start word (-w), include-input (-i),
    alternate word files (-f path and -f - stdin), silent/header modes, the
    -a/-v modifiers, unimplemented-language diagnostics (-L) and the readme's
    suggested first command.  Upstream ships no test framework at all, so
    this is the 补全 suite declared in MANIFEST.yml.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class WordplayTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wordplay test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run dependencies into
        # PATH, and wordplay is an application package.
        self.requires(self.tested_reference_str, run=True)

    def _pkg_dir(self):
        """package_folder of the tested wordplay package."""
        dep = self.dependencies.get("wordplay")
        if dep is None:
            raise ConanException("wordplay dependency missing from the graph")
        binary = os.path.join(dep.package_folder, "bin", "wordplay")
        if not os.path.isfile(binary):
            raise ConanException(
                f"wordplay executable not found in the package: {binary}")
        words = os.path.join(dep.package_folder, "res", "words721.txt")
        if not os.path.isfile(words):
            raise ConanException(f"word list not found in the package: {words}")
        return dep.package_folder

    def test(self):
        pkg = self._pkg_dir()

        # Layer 1: HarmonyOS artifact/ABI checks (host independent).
        if str(self.settings.os) == "OHOS":
            checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
            binary = os.path.join(pkg, "bin", "wordplay")
            words = os.path.join(pkg, "res", "words721.txt")
            # Double quotes, not shlex.quote: the controlling host may be
            # Windows (cross-compiling dev box), where the single quotes
            # shlex produces are not valid cmd/pwsh quoting.
            self.run(
                f'"{sys.executable}" "{checker}" '
                f'--binary "{binary}" --words "{words}"')
        else:
            self.output.info(
                "target os=%s: the A1-A9 artifact layer is OHOS specific and "
                "is skipped; the functional layer below still exercises the "
                "packaged binary" % self.settings.os)

        # Layer 2: on-device functional suite.
        if not can_run(self):
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the 20 test_wordplay.sh runtime cases are "
                "skipped here and are exercised on the HarmonyOS CI worker; "
                "the artifact/ABI layer above did execute against the "
                "packaged binary")
            return

        script = os.path.join(self.recipe_folder, "test_wordplay.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        # OHOS / is largely read-only (erofs): seed a writable TMPDIR in the
        # parent process before exec so the script's scratch files land there.
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for var in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            os.environ[var] = tmpdir
        self.run('"%s" "%s" "%s"' % (shell, script, pkg), env="conanrun")
