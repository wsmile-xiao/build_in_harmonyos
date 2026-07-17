#!/usr/bin/env python3
"""Conan test_package — tmux-mem-cpu-load 3.8.3 (command-line tool)."""
from pathlib import Path

from conan import ConanFile
from conan.tools.build import cross_building


class TmuxMemCpuLoadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the binary exists in the package
        bindir = Path(self.dependencies["tmux-mem-cpu-load"].cpp_info.bindirs[0])
        binary = bindir / "tmux-mem-cpu-load"
        if not binary.is_file():
            raise RuntimeError(f"missing tmux-mem-cpu-load executable: {binary}")

        if cross_building(self):
            self.output.info("cross-building: verified package executable exists")
            return

        test_script = Path(self.recipe_folder) / "test_cli.py"
        self.run(f"python3 {test_script} {binary}", env="conanrun")