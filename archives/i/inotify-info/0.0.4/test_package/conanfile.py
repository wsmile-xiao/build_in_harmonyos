import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # L0d: test() 必须有 self.run()；CI #15438: 二进制不在 PATH → 用完整路径
        dep = self.dependencies["inotify-info"]
        bin_dir = dep.cpp_info.bindirs[0]
        bin_path = os.path.join(dep.package_folder, bin_dir, "inotify-info")
        if not os.path.exists(bin_path):
            raise ConanException(f"inotify-info binary not found at {bin_path}")

        script = os.path.join(self.source_folder, "run_smoke_tests.sh")
        if not os.path.exists(script):
            raise ConanException(f"smoke test script not found at {script}")

        # 断言本体在 run_smoke_tests.sh（8 项诚实断言，非零退出即失败）：
        # 可执行文件存在且可运行；--version 退出 0 且含 0.0.4；
        # 裸跑退出 0 且输出含 INotify Limits 三项限额数值。
        # 不断言 watch/instance 计数（依赖环境状态，非软件行为）。
        self.run(f'sh "{script}" "{bin_path}"', env="conanrun")
