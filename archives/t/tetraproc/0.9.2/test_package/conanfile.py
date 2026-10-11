#!/usr/bin/env python3
"""test_package for tetraproc 0.9.2 — verifies the installed programs.

tetraproc itself is an X11/JACK GUI application: it cannot be launched in a
headless CI session, so the consumer test exercises tetrafile, the
command-line converter built from the same source tree, the way a real user
would (`tetrafile --help`), and asserts the GUI's runtime image assets are
packaged.
"""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv

ASSERTIONS = 0


class TetraprocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_runtime()

    def test(self):
        global ASSERTIONS
        tested = self.dependencies[self.tested_reference_str]
        bindir = Path(tested.cpp_info.bindirs[0])
        if not bindir.is_absolute():
            bindir = Path(tested.package_folder) / bindir
        tetrafile = bindir / "tetrafile"
        tetraproc = bindir / "tetraproc"

        # 1-2: both programs are packaged as regular executables
        ASSERTIONS += 1
        assert tetrafile.is_file(), f"missing {tetrafile}"
        ASSERTIONS += 1
        assert tetraproc.is_file(), f"missing {tetraproc}"

        if str(self.settings.os) == "OHOS":
            runtime_root = Path(self.build_folder, "runtime-libs")
            # NOTE: plain concatenation — str.format would choke on the
            # shell's ${CONFIG_SHELL:-...} default-value syntax.
            self.run(
                'CONFIG_SHELL="${CONFIG_SHELL:-/data/service/hnp/bin/bash}" '
                'TETRAFILE="' + str(tetrafile) + '" '
                'RUNTIME_LIBS="' + str(runtime_root) + '" '
                'bash "' + os.path.join(self.source_folder, "test.sh") + '"',
                env="conanrun",
            )
        else:
            self.run(
                'TETRAFILE="{tf}" bash "{sh}"'.format(
                    tf=tetrafile,
                    sh=os.path.join(self.source_folder, "test.sh"),
                ),
                env="conanrun",
            )
        ASSERTIONS += 1

        # 4: the GUI's runtime image assets are packaged (tetraproc loads
        # them from its compiled-in SHARED directory at startup)
        resdirs = tested.cpp_info.resdirs or ["share/tetraproc"]
        sharedir = Path(resdirs[0])
        if not sharedir.is_absolute():
            sharedir = Path(tested.package_folder) / sharedir
        images = sorted(p.name for p in sharedir.glob("*.png"))
        ASSERTIONS += 1
        assert len(images) == 3, f"expected 3 meter images, got {images}"

        self.output.info(f"TETRAPROC_TEST_ASSERTIONS={ASSERTIONS}")

    # ── OHOS runtime closure (same pattern as the clxclient test package) ──

    def _prepare_ohos_runtime(self):
        runtime_root = Path(self.build_folder, "runtime-libs")
        # a previous test_package run may have left a stale closure behind
        if runtime_root.exists():
            shutil.rmtree(runtime_root)
        runtime_root.mkdir(parents=False, exist_ok=False)
        copied = 0
        for _, dependency in self.dependencies.items():
            if getattr(dependency, "build", False) or getattr(
                dependency, "test", False
            ):
                continue
            if not dependency.package_folder:
                continue
            package_root = Path(dependency.package_folder).resolve(strict=True)
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for entry in sorted(
                    source_dir.iterdir(), key=lambda item: item.name
                ):
                    if not (
                        entry.name.endswith(".so") or ".so." in entry.name
                    ):
                        continue
                    destination = runtime_root / entry.name
                    if destination.exists():
                        continue
                    shutil.copy2(entry.resolve(strict=True), destination)
                    shutil.copymode(entry, destination)
                    copied += 1
        self.output.info(f"runtime closure: {copied} shared libraries")
        if copied == 0:
            raise ConanException("OHOS runtime library closure is empty")
        for library in sorted(runtime_root.iterdir(), key=lambda item: item.name):
            self._sign_ohos_elf(str(library))
        return runtime_root

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            raise ConanException("required OHOS signing tool is missing")
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
            check=True,
            stdout=sys.stderr,
            timeout=60,
        )
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o755)
