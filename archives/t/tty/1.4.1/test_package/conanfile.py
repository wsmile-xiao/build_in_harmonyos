#!/usr/bin/env python3
"""test_package for tty 1.4.1 — 编译运行消费者测试验证 CLI 可执行。

三层验证：
1. test.c 消费者程序 — 实际执行包内 ttysolitaire 二进制（R34 实质依赖）
2. 直接运行 ttysolitaire -v
3. test.sh 鸿蒙端到端消费者用例（HC-1..HC-3，含 pty 内真实启动游戏）
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TtySolitaireTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式直接依赖 ncurses：作为 tty 的传递依赖时，test_package 上下文
        # 中其 package_folder 为 None（cpp_info 仅相对路径），无法定位
        # terminfo 数据库；声明为直接依赖后 package_folder 恒有效。
        self.requires("ncurses/6.5")

    def build(self):
        self.run("clang test.c -o test_tty_solitaire")

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        # Use the full path to the ttysolitaire binary from THIS package
        pkg = self.dependencies["tty"].package_folder
        if not pkg:
            raise ConanException("tested package has no package_folder")
        bin_path = os.path.join(pkg, "bin", "ttysolitaire")
        if not os.path.isfile(bin_path):
            raise ConanException(f"ttysolitaire binary missing: {bin_path}")
        # 鸿蒙端到端用例需要 terminfo：静态 ncurses 内置 stale staging 路径。
        # 优先级：运行环境 TERMINFO → ncurses 包内 share/terminfo（直接依赖
        # 后 package_folder 恒有效）→ CONAN_HOME 缓存扫描兜底。
        terminfo = os.environ.get("TERMINFO", "")
        if not terminfo:
            cands = []
            for dep in self.dependencies.values():
                if dep.ref.name == "ncurses":
                    pkg = getattr(dep, "package_folder", None)
                    if pkg:
                        cands.append(os.path.join(pkg, "share", "terminfo"))
                    for inc in (dep.cpp_info.includedirs or []):
                        if os.path.isabs(inc):
                            cands.append(
                                os.path.join(
                                    os.path.dirname(inc), "share", "terminfo"
                                )
                            )
                    break
            import glob

            for home in (
                os.environ.get("CONAN_HOME", ""),
                os.path.expanduser("~/.cache/conan2"),
                os.path.expanduser("~/.conan2"),
            ):
                if home:
                    cands.extend(
                        sorted(
                            glob.glob(
                                os.path.join(
                                    home, "p", "ncurs*", "p", "share", "terminfo"
                                )
                            )
                        )
                    )
            for cand in cands:
                if cand and os.path.isdir(cand):
                    terminfo = cand
                    break
        terminfo_env = f'TERMINFO="{terminfo}"' if terminfo else ""
        self.run(f'"{bin_path}" -v')
        self.run(f'./test_tty_solitaire "{bin_path}"')
        self.run(f'TERM=xterm {terminfo_env} bash test.sh "{bin_path}"')
