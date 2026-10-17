#!/usr/bin/env python3
"""test_package — tina 0.1.14（验证打包的 tina 二进制可执行、ncurses 链接正确）.

tina 是全屏 curses TUI，headless CI 无法运行 initscr()。main.c 在
initscr() 之前处理 --version 并 return 0——test_tina.sh 通过
`tina --version` 真实执行被测包二进制（ELF 加载 + 动态链接 +
ncurses 链接全链路），并断言输出含 "Tina 0.1.14"（sl 同款 headless 策略）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class TinaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ncurses 是 tina 的运行期依赖；直接 requires 使其 runenv
        # （TERMINFO/LD_LIBRARY_PATH）进入 conanrun 环境。
        self.requires("ncurses/6.5")

    def test(self):
        tina = self.dependencies["tina"]
        tina_bin = os.path.join(tina.package_folder, "bin", "tina")
        if not os.path.exists(tina_bin):
            raise ConanException(f"tina binary not found: {tina_bin}")
        self.output.info(f"Testing packaged binary: {tina_bin}")
        script = os.path.join(self.source_folder, "test_tina.sh")
        self.run(f'sh "{script}" "{tina_bin}"', env="conanrun")
