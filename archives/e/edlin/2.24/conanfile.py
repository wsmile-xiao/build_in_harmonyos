#!/usr/bin/env python3
"""Conan recipe — FreeDOS edlin 2.24, a functional clone of the MS-DOS EDLIN
line editor, portable to POSIX systems (Linux/FreeBSD/etc.).

Autotools project, pure C, no third-party dependencies.
Upstream ships no test suite (no tests/ dir, no TESTS in Makefile.am);
`make check` is a no-op target — verified in notes.md.

Source tarball quirks handled by this recipe:
- config.guess/config.sub are from 2002 and cannot recognize modern
  kernels; configure is invoked with an explicit --build triplet
  (same approach as acct/6.6.4).
- Makefile.in defines `edlin_MANS = edlin.1.gz` but the man page is NOT
  shipped in the tarball. Because `edlin_MANS` is not a standard automake
  primary (that would be `man_MANS`/`man1_MANS`), no install rule is
  generated for it, so `make install` never touches the missing file.
  No patch needed; documented here for reviewers.
- DOS/Windows-only headers (process.h, io.h, conio.h, dos.h, jctype.h)
  and the kitten/catgets message-catalog fallback are all guarded by
  config.h / USE_* macros and are not compiled on Linux/OHOS.

License: GPL-2.0-or-later (COPYING is GPLv2; upstream header says
"version 2 or any later version").
Homepage: https://sourceforge.net/projects/freedos-edlin/
"""
import os
import shlex
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class EdlinConan(ConanFile):
    name = "edlin"
    version = "2.24"
    description = "FreeDOS edlin — line editor, functional clone of MS-DOS EDLIN"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/freedos-edlin/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # No third-party dependencies (leaf package, libc only)
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS"), never == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"edlin only supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group
        # perms), causing config.status to fail writing subs*.awk. Create a
        # mktemp wrapper that returns failure to force autoconf AS_TMPDIR to
        # use its mkdir fallback (same fix as acct/6.6.4 and bash 5.3).
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # Upstream config.guess is from 2002 and cannot guess modern systems;
        # force the build triplet explicitly (cross-safe, no patch needed).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def _workdir(self):
        # The deep conan-home cache path (HMDFS) denies writes into freshly
        # created config.status temp dirs (subs1.awk Permission denied, tried
        # with both /system/bin/sh and the hnp bash). Copy the (tiny) source
        # tree to a shallow $HOME/tmp scratch dir and build there — the
        # approach proven by dominion/2.8.2 on the same device class.
        work = os.path.join(os.path.expanduser("~"), "tmp",
                            f"edlin-build-{self.version}")
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".git"))
        return work

    def build(self):
        work = self._workdir()
        configure = os.path.join(work, "configure")
        args = [
            "--build=aarch64-unknown-linux-gnu",
            "--prefix=" + self.package_folder,
        ]
        # E011/E112: keep the failing-mktemp wrapper ahead of the real GNU
        # mktemp in ~/usr/local/bin so autoconf AS_TMPDIR uses its plain
        # mkdir fallback (whose dirs are writable in the scratch area).
        wrapper_dir = os.path.join(self.build_folder, ".hmos_fix")
        # E087: never exec the configure script (HMDFS blocks exec of cached
        # script files); run it through a shell, which only reads it.
        shell = "/data/service/hnp/bin/bash"
        if not Path(shell).exists():
            shell = shutil.which("bash") or "/system/bin/sh"
        cmd = " ".join(
            [f'PATH="{wrapper_dir}:$PATH"',
             f"CONFIG_SHELL={shell}", f"SHELL={shell}",
             shlex.quote(shell), shlex.quote(configure)]
            + [shlex.quote(a) for a in args]
        )
        self.run(cmd, cwd=work, env="conanbuild")

        # make itself is a PATH binary (not on HMDFS), plain exec works.
        self.run("make -j1", cwd=work, env="conanbuild")
        # L1: upstream official test target. edlin ships no test suite:
        # `make check` is a no-op target that exits 0 (see notes.md).
        self.run("make check", cwd=work, env="conanbuild")

        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(work, "edlin"))

    def _sign_elf(self, path):
        """Sign the ELF binary so it is executable on HarmonyOS (E077).

        binary-sign-tool only exists on OHOS; on Linux build hosts this is
        a no-op, leaving CI's release sign.sh to do the final signing.
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f"{objcopy} --remove-section .codesign {path} || true")
            self.run(
                f"{sign_tool} sign -inFile {path} -outFile {path}.signed -selfSign 1"
            )
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def package(self):
        work = os.path.join(os.path.expanduser("~"), "tmp",
                            f"edlin-build-{self.version}")
        self.run("make install", cwd=work, env="conanbuild")
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "edlin.html", self.source_folder,
             os.path.join(self.package_folder, "share", "edlin", "doc"))
        copy(self, "README", self.source_folder,
             os.path.join(self.package_folder, "share", "edlin", "doc"))

    def package_info(self):
        # CLI tool — no public library interface.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
