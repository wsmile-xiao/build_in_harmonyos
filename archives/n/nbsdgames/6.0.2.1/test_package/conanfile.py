#!/usr/bin/env python3
"""Conan test_package — nbsdgames 6.0.2.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class NbsdgamesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bin_path(self, dep, game):
        # bindirs[0] 为相对值 "bin"，须拼接 package_folder 得到绝对路径
        return os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], game)

    def test(self):
        if can_run(self):
            dep = self.dependencies["nbsdgames"]
            # 可非交互验证的游戏子集（设备实测：sudoku -h 退出码 1，reversi/checkers/sos -h 退出码 0）
            # sudoku: -h 输出 Usage，上游约定退出码 1
            self.run(
                f'output=$("{self._bin_path(dep, "sudoku")}" -h 2>&1); status=$?; '
                f'test "$status" -eq 1 && printf "%s\\n" "$output" | grep -q "^Usage:"',
                env="conanrun",
            )
            # reversi/checkers/sos: -h 输出 Usage，退出码 0
            for game in ("reversi", "checkers", "sos"):
                self.run(
                    f'output=$("{self._bin_path(dep, game)}" -h 2>&1); status=$?; '
                    f'test "$status" -eq 0 && printf "%s\\n" "$output" | grep -q "^Usage:"',
                    env="conanrun",
                )
