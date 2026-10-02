#!/usr/bin/env python3
"""Conan test_package for ydpdict 1.0.5-1.1 (consumer-side validation).

ydpdict 是应用型包：消费者面 = 已安装程序 bin/ydpdict（全屏 ncurses TUI）及其
词典引擎 libydpdict。上游发布包不含任何测试（清点证据见 MANIFEST.yml），
本 test_package 以消费者视角补全三组实测：

1. test_consumer.c —— 编译并运行 C 消费者，真实调用 libydpdict 公开 API
   （版本契约 / 打开失败路径 / 空指针守护 / cp1250 与音标编码转换，16 断言）；
2. test_app.sh —— 鸿蒙产物契约 + TUI 端到端（共 7 条断言）：OHOS-1..4 校验已
   安装程序（AArch64 ELF、DT_NEEDED 无共享 curses 库、无绝对路径条目）、
   TUI-1..2 在伪终端下真实运行程序、CONSUMER-C 汇总消费者程序结果。
   上游 main() 解析参数后无条件 initscr()，没有 --version/--help 非交互分支，
   故不设 CLI 断言（断言数 7 = 平台 6 + 消费者 1）；
3. pty_drive.py —— 伪终端端到端：自动挑选本机真实存在的 TERM、按
   TERMINFO_DIRS 多目录发现 terminfo，干净 HOME 下启动 TUI，首屏渲染出界面
   文案后以退出键或 SIGTERM 兜底终止（TUI 无法用管道/重定向验证）。

交叉编译：消费者程序由本配方 build() 调用 profile 声明的交叉 C 编译器
（tools.build:compiler_executables → AutotoolsToolchain 导出的 $CC）编译，
依赖路径（-I/-L/-l）全部来自依赖包 cpp_info，未注入任何共享前缀（R49）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.gnu import AutotoolsToolchain

# 被测包依赖链中的词典引擎版本（test_package 的消费者直接调用其 API）。
LIBYDPDICT_REF = "libydpdict/1.0.4"


class YdpdictTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 消费者用例直接链接词典引擎：显式声明为直接依赖，保证 API 可用。
        self.requires(LIBYDPDICT_REF)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # tc.generate() 已把 profile 的交叉编译器与依赖 cpp_info 路径写入构建
        # 环境（$CC/$CPPFLAGS/$CFLAGS/$LDFLAGS），build() 直接复用。

    def build(self):
        deps = self.dependencies[LIBYDPDICT_REF]
        incs = " ".join("-I" + d for d in deps.cpp_info.includedirs)
        libdirs = " ".join("-L" + d for d in deps.cpp_info.libdirs)
        libs = " ".join("-l" + lib for lib in deps.cpp_info.libs)
        # profile [buildenv] 的 CPPFLAGS/LDFLAGS 会覆盖 conan 注入的依赖路径
        # （与主配方同一个坑：实测 $CPPFLAGS 里只有 /usr/local/include，
        # 消费者直接 fatal error: 'ydpdict/ydpdict.h' file not found），
        # 因此这里以命令前缀强制补上 libydpdict 的 -I/-L。
        # 注意：不能用 `CPPFLAGS="..." "$CC" ... $CPPFLAGS` 这种前缀赋值写法——
        # POSIX shell 先展开同行参数再应用前缀赋值，$CPPFLAGS 拿到的仍是旧值
        # （实测编译行里看得见 -I，头文件却依然 not found）。这里直接拼进命令行。
        # 输出路径写绝对路径（build_folder），不依赖 cwd——用相对的 -o test_consumer
        # 曾把编译产物落到配方目录里并被误提交（archives/ 污染，JC 拦截）。
        self.run(
            '"$CC" -std=c99 -Wall -Wextra $CPPFLAGS {incs} $CFLAGS '
            '"{src}" -o "{out}" $LDFLAGS {libdirs} {libs}'.format(
                incs=incs, libdirs=libdirs, libs=libs,
                src=os.path.join(self.source_folder, "test_consumer.c"),
                out=os.path.join(self.build_folder, "test_consumer")),
            cwd=self.build_folder,
        )

    def _terminfo_dirs(self):
        """依赖包自带的 terminfo 数据库目录（TUI 用例需要 vt100 条目）。

        返回以 os.pathsep 分隔的候选列表，供 pty_drive.py 注入 TERMINFO_DIRS。
        注意 ncurses 包的 terminfo 既可能在 share/terminfo，也可能在 lib/terminfo
        （实测下载到的包两者都有），只看其中一个会得到空串导致 TUI 断言失败。
        """
        cands = []
        for dep in self.dependencies.values():
            folder = dep.package_folder
            if not folder:
                continue
            for sub in ("share/terminfo", "lib/terminfo"):
                path = os.path.join(folder, sub)
                if os.path.isdir(path) and path not in cands:
                    cands.append(path)
        # 本平台系统 terminfo 作为兜底（通常不完整，故置于依赖之后）。
        for path in ("/system/usr/share/terminfo", "/usr/share/terminfo"):
            if os.path.isdir(path) and path not in cands:
                cands.append(path)
        self.output.info("terminfo 候选: %s" % (os.pathsep.join(cands) or "<无>"))
        return os.pathsep.join(cands)

    def test(self):
        if not can_run(self):
            self.output.warning("cross-building environment: 跳过运行时消费者用例")
            return
        tested = self.dependencies[self.tested_reference_str]
        package_folder = tested.package_folder
        binary = os.path.join(package_folder, "bin", "ydpdict")
        consumer = os.path.join(self.build_folder, "test_consumer")
        script = os.path.join(self.source_folder, "test_app.sh")
        self.run(
            'sh "{script}" "{pkg}" "{binary}" "{consumer}" "{terminfo}"'.format(
                script=script,
                pkg=package_folder,
                binary=binary,
                consumer=consumer,
                terminfo=self._terminfo_dirs(),
            ),
            cwd=self.build_folder,
            # conanrun 环境由依赖包的 runenv_info 组成——ncurses 配方在其中
            # 声明 TERMINFO=<pkg>/share/terminfo，TUI 用例才能初始化终端
            # （缺该变量时 ncurses 报 cannot initialize terminal type 并退出）。
            env="conanrun",
        )
