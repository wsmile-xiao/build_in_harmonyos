#!/usr/bin/env python3
"""joystick (linuxconsoletools) 1.8.1 test_package — 消费者视角真实执行。

无 /dev/input 设备环境下的无设备 CLI 契约（鸿蒙 PC 真机逐个实测）：
  - 八个已声明命令（commands.json）的 `--help` 与 `--version` **一律退出码 0**
    ——上游原本把 --help 当 usage 语义 exit(1)、若干工具不认 --version，
    已按 K0 口径用补丁 0001-k0-help-version-exit0.patch 统一（probcons 先例）；
    退出码恰为 0 仍能证明 ELF 真实执行（无法加载时 shell 返回 126/127）。
  - jscal-restore / jscal-store 两枚随包脚本必须**可执行**（上游 0644，
    配方 package() 补 mode）——直接执行而非经 bash 调用。
任何断言失败即测试失败（R34：禁止空壳测试）。
"""
import os
import subprocess
import sys


def run(binary, *args):
    return subprocess.run(
        [binary, *args], capture_output=True, text=True, timeout=30
    )


def main():
    bindir = sys.argv[1]
    assertions = 0

    declared = ("jstest", "jscal", "evdev-joystick", "inputattach",
                "fftest", "ffset", "ffcfstress", "ffmvforce")

    # 1) 八个已声明命令的 --help 一律 rc=0（K0；126/127 = 未执行）
    for name in declared:
        r = run(os.path.join(bindir, name), "--help")
        assert r.returncode == 0, (
            f"{name} --help rc={r.returncode} "
            f"(期望 0) stderr={r.stderr[:200]}"
        )
        assertions += 1

    # 2) 八个已声明命令的 --version 一律 rc=0（K0）
    for name in declared:
        r = run(os.path.join(bindir, name), "--version")
        assert r.returncode == 0, (
            f"{name} --version rc={r.returncode} "
            f"(期望 0) stderr={r.stderr[:200]}"
        )
        assertions += 1

    # 3) 运维脚本（非 ELF）随包存在且**可直接执行**（上游 0644 → 配方补 0755）
    for name in ("jscal-restore", "jscal-store"):
        path = os.path.join(bindir, name)
        assert os.path.isfile(path), f"缺少 {name}"
        assert os.access(path, os.X_OK), f"{name} 不可执行（mode={oct(os.stat(path).st_mode & 0o777)}）"
        r = run(path, "--help")
        assert r.returncode in (0, 1), (
            f"{name} --help rc={r.returncode}（期望脚本真实执行，126=权限不足未执行）"
        )
        assertions += 1

    print(f"joystick test_package: {assertions} 项断言全部通过")


main()
