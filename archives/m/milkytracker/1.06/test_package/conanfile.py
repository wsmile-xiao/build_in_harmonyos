#!/usr/bin/env python3
"""Conan test_package for milkytracker 1.06 (application).

milkytracker 是 SDL2 图形应用（tracker 主程序） + 命令行工具 milkycli。
图形程序在无显示环境无法直接跑，因此用 milkycli 做功能验证：
将包内自带的示例曲目 milky.xm 导出为 WAV，校验退出码与产物。
具体断言逻辑在 test.sh（CI L0c 门禁要求 test_package 下有测试源文件）。
"""
import os
import glob

from conan import ConanFile


class MilkytrackerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["milkytracker"].package_folder
        milkycli = os.path.join(pkg, "bin", "milkycli")
        tracker = os.path.join(pkg, "bin", "milkytracker")
        assert os.path.isfile(milkycli), f"milkycli not found at {milkycli}"
        assert os.path.isfile(tracker), f"milkytracker not found at {tracker}"

        # 找包内示例曲目（安装到 share/milkytracker/songs/）
        songs_dir = os.path.join(pkg, "share", "milkytracker", "songs")
        xms = glob.glob(os.path.join(songs_dir, "*.xm"))
        assert xms, f"no example .xm songs in {songs_dir}"

        # 调用测试脚本执行 milkycli 导出并校验产物
        test_script = os.path.join(self.source_folder, "test.sh")
        out_dir = self.build_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} "{test_script}" "{milkycli}" "{songs_dir}" "{out_dir}"', env="conanrun")
        out = os.path.join(out_dir, "export.wav")
        assert os.path.isfile(out), f"milkycli did not produce {out}"
        print(f"milkycli export verification: OK ({os.path.getsize(out)} bytes)")
