#!/usr/bin/env python3
"""Conan test_package for box64 0.4.4 (HarmonyOS PC / aarch64).

Real consumer-side test (R34): the packaged emulator is run on a genuinely
x86_64 ELF generated from a text asset, and stdout / exit codes are asserted.

  1) box64 --version       -> "Box64 arm64 ... v0.4.4 ... with Dynarec", rc=0
  2) make_x86_64_hello.py  -> 177-byte static x86_64 ET_EXEC from pure python
                              (asserted sha256; no cross toolchain, no binary
                              asset in the repo)
  3) box64 hello_x86_64    -> stdout exactly "hello from x86_64\n", rc=0
  4) --exit-code 7 variant -> rc=7 (guest exit() syscall passthrough)
  5) R53 OHOS-specific suite (ohos_specific_test.py): ET_EXEC/AArch64/musl
     interpreter/.codesign/.dynsym wrapper hiding/$ORIGIN RUNPATH + bundled
     musl-fts and musl-obstack shared objects.

All emulator runs strip LD_LIBRARY_PATH from the environment: the package
must be self-contained through its $ORIGIN/../lib RUNPATH.
"""
import hashlib
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class Box64TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = ("make_x86_64_hello.py", "ohos_specific_test.py")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _run_clean(self, argv):
        """Run a command with LD_LIBRARY_PATH removed (self-containment)."""
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=180, cwd=self.build_folder, env=env)

    def test(self):
        if not can_run(self):
            return

        pkg = self.dependencies[self.tested_reference_str]
        box64 = os.path.join(pkg.package_folder, "bin", "box64")
        if not os.path.isfile(box64):
            raise ConanException("box64 binary not packaged: %s" % box64)
        python = os.environ.get("CONAN_TEST_PYTHON3", "") or "python3"

        # 1) --version through self.run (L0d evidence) ...
        outfile = os.path.join(self.build_folder, "box64-version.out")
        self.run('"%s" --version > "%s" 2>&1' % (box64, outfile),
                 env="conanrun")
        out = open(outfile, encoding="utf-8", errors="replace").read()
        if "Box64 arm64" not in out or "v0.4.4" not in out or "Dynarec" not in out:
            raise ConanException("unexpected --version output: %r" % out)
        # ... and without conanrun env: RUNPATH must resolve the bundled libs.
        proc = self._run_clean([box64, "--version"])
        if proc.returncode != 0:
            raise ConanException("box64 --version rc=%d stderr=%r"
                                 % (proc.returncode, proc.stderr[-400:]))

        # 2) x86_64 fixture generated from a text asset
        gen = os.path.join(self.source_folder, "make_x86_64_hello.py")
        hello = os.path.join(self.build_folder, "hello_x86_64")
        self.run('"%s" "%s" --verify -o "%s"' % (python, gen, hello),
                 env="conanrun")
        digest = hashlib.sha256(open(hello, "rb").read()).hexdigest()
        if digest != "170f6cb94332a64b416b383d274695bb635c462a57e9c138b2348e47637b6934":
            raise ConanException("fixture sha256 mismatch: %s" % digest)

        # 3) real x86_64 execution
        proc = self._run_clean([box64, hello])
        if proc.returncode != 0 or proc.stdout != "hello from x86_64\n":
            raise ConanException(
                "hello x86_64 run failed rc=%d stdout=%r stderr=%r"
                % (proc.returncode, proc.stdout, proc.stderr[-400:]))

        # 4) exit-code passthrough
        hello7 = os.path.join(self.build_folder, "hello_x86_64_exit7")
        self.run('"%s" "%s" --exit-code 7 -o "%s"' % (python, gen, hello7),
                 env="conanrun")
        proc = self._run_clean([box64, hello7])
        if proc.returncode != 7:
            raise ConanException("exit code passthrough failed: rc=%d (want 7)"
                                 % proc.returncode)

        # 5) R53 HarmonyOS-specific structural suite
        script = os.path.join(self.source_folder, "ohos_specific_test.py")
        self.run('"%s" "%s" "%s" "%s"' % (python, script, pkg.package_folder, hello),
                 env="conanrun")
