import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ncurses 是 openvi 的传递依赖；显式声明后 (a) 才能读到它的
        # package_folder 拼出 TERMINFO，(b) VirtualRunEnv 才会把它的
        # runenv（TERMINFO/TERMINFO_DIRS/LD_LIBRARY_PATH）并进 conanrun。
        # 不声明时 self.dependencies["ncurses"].package_folder 为 None，
        # 会拼出 TERMINFO="None/share/terminfo"（CI #44863 全部 ex 用例失败）。
        self.requires("ncurses/6.6")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包存在")
            return
        dep = self.dependencies["openvi"]
        work = os.path.join(self.build_folder, "viwork")
        os.makedirs(work, exist_ok=True)
        # openvi 的入口是 cl/cl_main.c 的 main()，它在 editor() 前无条件
        # term_init()→setupterm()，所以 ex 批处理模式也必须有 terminfo 数据库；
        # 否则报 `ex: No terminal database found` 并 exit 1。数据库随 Conan
        # ncurses/6.6 发布在 share/terminfo（其 runenv_info 定义了 TERMINFO/
        # TERMINFO_DIRS，conanrun 环境已带）；这里再显式注入一层，避免依赖
        # 传递 runenv 的行为。TERM=vt100 避开 term_init 的 unknown 回退（含 5s sleep）。
        terminfo = ""
        try:
            nc = self.dependencies["ncurses"]
            candidate = f"{nc.package_folder}/share/terminfo".replace("\\", "/")
            if nc.package_folder and os.path.isdir(candidate):
                terminfo = candidate
        except Exception:  # 取不到时退回 conanrun 自带（ncurses runenv）的 TERMINFO
            pass
        env_prefix = "export TERM=vt100;"
        if terminfo:
            env_prefix += (
                f' export TERMINFO="{terminfo}" TERMINFO_DIRS="{terminfo}";'
            )
        # OHOS /system/bin/sh(mksh) 不能执行 ELF → 用 hnp bash 包裹；
        # TMPDIR 指向可写构建目录（HMFS /tmp 只读）。
        self.run(
            f'{env_prefix} TMPDIR="{work}" /data/service/hnp/bin/bash '
            f'"{os.path.join(self.source_folder, "test.sh")}" '
            f'"{dep.package_folder}" "{work}"',
            env="conanrun",
        )
