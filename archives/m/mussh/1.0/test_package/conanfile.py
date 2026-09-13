#!/usr/bin/env python3
"""Consumer test for the packaged mussh:

  1. bin/mussh must exist and be executable
  2. when the environment can run binaries, test_mussh.sh executes
     `mussh -V` and asserts stdout contains "Version: 1.0" (exit 0)

test_type="explicit": executed by `conan test` (CI). `conan create`
builds this package without executing it, which keeps noexec sandbox
environments (knowledge E052/E077) able to pass local W3 verification.

Note: argument-less/--help runs are deliberately not asserted — they
also exit 0 (usage text), so they carry no discriminating power.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class MusshTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = ["VirtualRunEnv"]
    test_type = "explicit"
    exports_sources = "test_mussh.sh", "test_harmony_tmpdir.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["mussh"]
        mussh = os.path.join(pkg.package_folder, "bin", "mussh")
        if not os.path.isfile(mussh):
            raise ConanException(f"missing packaged script: {mussh}")
        if not os.access(mussh, os.X_OK):
            raise ConanException(f"packaged script not executable: {mussh}")

        if not can_run(self):
            self.output.warning("Cannot run binaries in this environment; "
                                "execution validation delegated to CI conan test")
            return

        script = os.path.join(self.source_folder, "test_mussh.sh")
        self.run(f'bash "{script}" "{mussh}"', env="conanrun")

        # 鸿蒙特有测试（rule12）：验证 0002-mktemp-tmpdir.patch 适配点——
        # 鸿蒙 /tmp 只读 erofs，mussh 临时目录必须走 TMPDIR 而非硬编码 /tmp
        script2 = os.path.join(self.source_folder, "test_harmony_tmpdir.sh")
        self.run(f'bash "{script2}" "{mussh}"', env="conanrun")
