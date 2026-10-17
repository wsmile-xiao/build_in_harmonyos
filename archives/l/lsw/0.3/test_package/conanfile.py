#!/usr/bin/env python3
"""Consumer test for lsw 0.3 (tool package).

lsw 交付 bin/lsw（CLI 工具，无链接库）。设备与 CI worker 均无 X server
（headless，无 Xvfb 可发布），XOpenDisplay 失败是确定性的可观察行为：
消费者测试走无 X 环境错误路径断言（clipnotify 1.0.2 test_nox.sh 同款）：
  1. 包内二进制存在且可执行；
  2. 无 DISPLAY 时 lsw 必须以非零码退出且 stderr 含 "cannot open
     display"（lsw.c L19-20：XOpenDisplay 失败分支）——真实执行了
     X11 动态链接链（libX11 -> libxcb/libXau/libXdmcp）的加载。
"""
import os
import tempfile

from conan import ConanFile


def _spool_dir():
    # 测试副产物不得落在归档内（test package 的 build_folder 就是
    # archives/l/lsw/0.3/test_package/ 本身），也不得落在家根：
    # 设备 /tmp 只读、TMPDIR=$HOME ⇒ 裸 mkdtemp() 会把副产物写进 ~（§1 禁止），
    # 故两级择路——优先 ~/tmp（可丢弃产物区），不可写才退到系统临时目录。
    # mkdtemp 唯一，并发跑不互撞；断言逻辑与条数不变。
    for base in (os.path.join(os.path.expanduser("~"), "tmp"), tempfile.gettempdir()):
        try:
            os.makedirs(base, exist_ok=True)
            return tempfile.mkdtemp(prefix="lsw-test-", dir=base)
        except OSError:
            continue
    return tempfile.gettempdir()


class LswTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_lsw_nox.sh")
        spool = _spool_dir()
        self.run(f'sh "{script}" "{bindir}" "{spool}"', env="conanrun")
