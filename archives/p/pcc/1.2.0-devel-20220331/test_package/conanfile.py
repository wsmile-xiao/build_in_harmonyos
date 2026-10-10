#!/usr/bin/env python3
"""Conan test_package for pcc -- R34: this really drives the compiler.

The tested package installs a C compiler that runs on HarmonyOS PC (aarch64).
Two layers run here:

1. ``test_pcc_cases.sh`` -- the HarmonyOS-specific end-to-end cases.  Each named
   case (arith / loop / ptr / struct) is compiled by the packaged driver to
   x86-64 assembly, then assembled by a real assembler and linked by ``ld.lld``
   into a real x86-64 ELF executable whose header is read back (ELF64 / X86-64 /
   EXEC).  A wrong or incomplete code generator fails at the assembler or the
   linker, so this is a genuine test rather than a text assertion.
2. ``main.c`` -- the single consumer translation unit, kept as a quick check
   that the packaged driver runs and emits code for a minimal input.

The package is linked statically, so an OHOS/aarch64 compiler can also be
executed on a non-OHOS build host through qemu-user / binfmt_misc.  Where no
such emulator exists the test says so explicitly instead of silently
reporting a pass.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    #: The package ships the compiler under its default target triple, so the
    #: driver is not plain "pcc" but "<target>-pcc".
    _target = "amd64-linux"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _runner(self):
        """argv prefix used to execute the packaged compiler.

        On HarmonyOS itself the compiler runs natively, so the prefix is empty.
        When the compiler is an OHOS binary but the build host is not, it is
        executed through qemu-user/binfmt.  Returns None only when neither is
        possible, in which case the caller reports a skip.
        """
        if can_run(self):
            return ""
        for candidate in ("qemu-aarch64-static", "qemu-aarch64"):
            path = shutil.which(candidate)
            if path:
                return f'"{path}" '
        return None

    def test(self):
        package = self.dependencies[self.tested_reference_str]
        bindir = package.cpp_info.bindirs[0]
        driver = os.path.join(bindir, f"{self._target}-pcc")
        if not os.path.isfile(driver):
            listing = sorted(os.listdir(bindir)) if os.path.isdir(bindir) else []
            raise ConanException(
                f"packaged pcc driver not found: {driver} (bin holds {listing})"
            )

        runner = self._runner()
        if runner is None:
            self.output.warning(
                "cannot execute an OHOS/aarch64 binary here (cross build without "
                "qemu-user); the consumer compile is left to a real device run"
            )
            return

        # A test_package builds in place, so `build_folder` is this directory
        # (the committed one).  Keep every generated file in a scratch subdir
        # that is not part of the source tree -- `build/` is covered by the
        # archive's .gitignore, so nothing the test produces can leak into a PR.
        workdir = os.path.join(self.build_folder, "build")
        os.makedirs(workdir, exist_ok=True)
        # The driver puts its intermediate files in $TMPDIR; HarmonyOS mounts
        # /tmp read-only (erofs), so point it at a directory known to be
        # writable.  Harmless anywhere else.
        tmpdir = os.path.join(workdir, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # ── HarmonyOS-specific end-to-end cases ──
        # Each case is compiled by the packaged driver, assembled by a real
        # assembler and linked by ld.lld into a real x86-64 ELF executable.
        cases_dir = os.path.join(self.recipe_folder, "cases")
        script = os.path.join(self.recipe_folder, "test_pcc_cases.sh")
        if not os.path.isfile(script):
            raise ConanException(f"harmonyos case runner missing: {script}")
        if not os.path.isdir(cases_dir):
            raise ConanException(f"harmonyos case sources missing: {cases_dir}")
        libexec = os.path.join(os.path.dirname(bindir), "libexec")
        self.run(
            f'PCC_BIN="{bindir}" PCC_LIBEXEC="{libexec}" '
            f'PCC_CASES="{cases_dir}" PCC_WORK="{workdir}/cases" '
            f'{runner}sh "{script}"',
            env="conanrun",
            scope="run",
        )

        # ── minimal consumer translation unit (packaged driver runs at all) ──
        source = os.path.join(self.recipe_folder, "main.c")
        if not os.path.isfile(source):
            raise ConanException(f"consumer source missing: {source}")
        assembly = os.path.join(workdir, "consumer.s")

        # env="conanrun" reproduces the environment a consumer gets from
        # `conan install`: the driver locates its back end by name on PATH.
        self.run(
            f'TMPDIR="{tmpdir}" {runner}"{driver}" -S -o "{assembly}" "{source}"',
            env="conanrun",
            scope="run",
        )
        if not os.path.isfile(assembly) or os.path.getsize(assembly) == 0:
            raise ConanException("pcc produced no assembly output")

        # The packaged compiler defaults to amd64-linux, so compiling pcc_add()
        # must emit x86-64 code.  Asserting on the emitted text proves the
        # compiler really did the work rather than exiting 0.
        body = open(assembly, encoding="utf-8", errors="replace").read()
        self.output.info(f"  generated {len(body)} bytes of assembly")
        for expected in ("pcc_add", "pcc_sum", "pushq", "%rbp", "movl"):
            if expected not in body:
                raise ConanException(
                    f"generated assembly is missing expected {expected!r}"
                )
        self.output.info("consumer compile assertions passed")
