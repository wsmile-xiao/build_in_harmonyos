#!/usr/bin/env python3
"""Consumer test for shmux 1.0.3 (tool package).

shmux 交付 bin/shmux（CLI 工具，无链接库），消费者测试以工具使用者身份
执行包内二进制并断言可观察行为（test_shmux.sh）：
  1. 并行分发往返：sh: 方法向 3 个本地目标执行 echo，断言各目标输出；
  2. Summary 计数：断言 2 目标会话输出 "2 targets processed"；
  3. 退出码传播：目标 exit 7 时断言 "exited with status 7" 报告。

term.c 运行时调 tgetent：TERM=xterm + TERMINFO 指向 ncurses 包内数据库
（设备无系统 terminfo；ncurses 为被测包的依赖，随 conanrun 环境可用）。
"""
import os

from conan import ConanFile


class ShmuxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # shmux 为终端程序：tgetent 需要 terminfo 数据库，
        # 设备无系统 terminfo，由 ncurses 包（被测包依赖）提供。
        self.requires("ncurses/6.4")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_shmux.sh")
        term_root = self.dependencies["ncurses"].package_folder
        # 输出文件落 TMPDIR（HMDFS 上 = ~/tmp）：spool 指 build_folder 时本目录就是
        # 源码树内的 test_package/，消费者输出会脏化工作区、可能被误扫进 PR（JC4）；
        # CI 无 TMPDIR 时回退 build_folder（CI 工作区不入 PR，无碍）。
        spool = os.environ.get("TMPDIR") or self.build_folder
        self.run(f'sh "{script}" "{bindir}" "{term_root}" "{spool}"', env="conanrun")
