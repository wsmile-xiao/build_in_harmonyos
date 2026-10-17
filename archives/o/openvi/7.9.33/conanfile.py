#!/usr/bin/env python3
"""Conan 2 recipe — openvi 7.9.33 (Jeffrey H. Johnson, C, BSD vi/ex 编辑器).

OpenVi 是 OpenBSD vi/ex（nvi 血统）的独立可移植重打包：支持 ex 批处理与
可视化两套模式、多窗口、回溯撤销、行编辑，并自带 BSD db（btree/hash/mpool）、
regex、openbsd/ 与 xinstall/ 兼容层。产物: bin/{vi,ex,view,xinstall} +
libexec/vi.recover + man 页。

OHOS 适配要点：
- 纯手写 GNUmakefile（非 autotools）：无 configure/config.h/codegen，
  用命令行变量覆盖即可交叉编译（CC / INCLDS / CURSESLIB / LINKLIBS）。
- 上游 `PAWK = command -p env PATH="$(command -p getconf PATH)" awk`：
  依赖 getconf + 标准 PATH 探测 awk，在 OHOS 上探测链不可靠；两个 .h 生成
  规则（ex/ex_def.h、common/options_def.h）只是跑 POSIX awk 脚本，故命令行
  覆盖 PAWK=awk 直接走 PATH 里的 awk（语义等价，不改源码）。
- 默认 LINKLIBS = -lutil -lncurses：musl 把 openpty(3) 放进 libc（非
  glibc 的 libutil），故去掉 -lutil，只链 Conan ncurses。
- ncurses 用 Conan ncurses/6.6（shared=False 静态，R26：系统同名库不产 .so），
  头文件/静态库路径由 cpp_info 计算后注入 INCLDS/CURSESLIB/LINKLIBS。
- ex 批处理模式不初始化屏幕（不需要 tty），可在无头 CI worker 上实跑，因此
  层1 smoke 与 test_package 的功能验证都走 bin/ex（vi 模式 getopt 串不含 -s）。
  但注意：「无 tty」不等于「无 terminfo」——openvi 的程序入口是
  cl/cl_main.c 的 main()，它在 editor() 之前无条件 term_init()→setupterm()，
  所以 ex 模式也必须能定位 terminfo 数据库（否则
  `ex: No terminal database found` + exit 1）。数据库取自 Conan ncurses/6.6
  自带的 share/terminfo（见 build() 内注释）。
- 上游把备份临时文件写死 "/tmp/vi.XXXXXX"、恢复目录写死 "/var/tmp/vi.recover"，
  HarmonyOS HMFS 的 /tmp 只读 → 打一枚 $TMPDIR 补丁
  （patches/0001-honor-tmpdir.patch，无 $TMPDIR 时回退原路径）。

层1 上游测试：上游无测试套件（无 test/ 目录、无 check/test 目标、
.github/workflows 也不存在）——build() 内做 smoke 自证（ex 批处理往返，
见 build() 注释）；规则 12 的鸿蒙特有功能性测试在 test_package 以断言补齐。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class OpenViConan(ConanFile):
    name = "openvi"
    version = "7.9.33"
    description = "可移植的 OpenBSD vi/ex 编辑器（nvi 血统，支持 ex 批处理与可视化模式）"
    license = "BSD-3-Clause"
    homepage = "https://github.com/johnsonjh/OpenVi"
    url = ""  # CI fills this
    topics = ("editor", "vi", "ex", "nvi", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def validate(self):
        # R32: settings.os 判定
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"openvi supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # 终端 UI：静态 ncurses（wide-char）。R26：不产生系统同名 .so。
        self.requires("ncurses/6.6")

    def layout(self):
        pass

    def export_sources(self):
        # conandata.yml 声明的补丁必须被 export 进 source folder，否则
        # build() 里的 apply_conandata_patches 报 FileNotFoundError
        # （CI #44857: .../s/patches/0001-honor-tmpdir.patch 不存在）。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # 补丁：让 openvi 的备份临时文件 / 恢复目录跟随 $TMPDIR。
        # 上游写死 "/tmp/vi.XXXXXX"（common/exf.c、ex/ex_filter.c）与
        # _PATH_PRESERVE "/var/tmp/vi.recover"（common/options.c 的 recdir）；
        # HarmonyOS HMFS 的 /tmp 只读，运行期报
        # `Error: Unable to create temporary file: Read-only file system`。
        apply_conandata_patches(self)

        # R33: 编译器必须从 conan conf 取（CI worker 上 $CC 为空）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"

        nc = self.dependencies["ncurses"]
        pf = str(nc.package_folder).replace("\\", "/")
        ci = nc.cpp_info.aggregated_components()

        # cpp_info 里的 includedirs/libdirs 可能是相对（"include"）也可能已是绝对
        # 路径（不同修订的 ncurses 包两种都有）——一律先绝对化再拼，否则会拼出
        # `<pf>/<pf>/include` 这种重复前缀，clang 报 'curses.h' file not found。
        # 同 repo 先例：ncdc 1.25 的 _host_libdirs()。
        def _abs(d):
            d = str(d).replace("\\", "/")
            return d if os.path.isabs(d) else f"{pf}/{d}"

        nc_incs = " ".join(f"-I{_abs(d)}" for d in ci.includedirs)
        nc_libs = " ".join(f"-L{_abs(d)}" for d in ci.libdirs)
        nc_libs += " " + " ".join(f"-l{lib}" for lib in ci.libs)

        src = str(self.source_folder)

        # INCLDS 覆盖必须保留上游的 4 个 -I（include/common/regex/openbsd），
        # 再追加 ncurses 头目录；CURSESLIB/LINKLIBS 同值传入（LINKLIBS 覆盖
        # 掉上游的 `-lutil $(CURSESLIB)`，去掉 musl 上不存在的 libutil）。
        self.run(
            f'make -C "{src}" -j1 '
            f'CC="{cc}" '
            f'PAWK=awk '
            f'INCLDS="-Iinclude -Icommon -Iregex -Iopenbsd {nc_incs}" '
            f'CURSESLIB="{nc_libs}" '
            f'LINKLIBS="{nc_libs}"',
            env="conanbuild",
        )

        # 层1 smoke：上游无测试套件，用 ex 批处理模式自证二进制可运行
        # （写入 → 回读）。ex 模式不碰屏幕，但**仍需要 terminfo 数据库**：
        # openvi 的真正入口是 cl/cl_main.c 的 main()（不是 common/main.c 的
        # editor()），它在调 editor() 之前无条件执行 term_init()→setupterm()，
        # 失败即 `ex: No terminal database found` + exit(1)（cl_main.c:228-244，
        # err=-1 分支）。数据库来自 Conan ncurses/6.6 的 share/terminfo——该
        # 包的 runenv_info 已定义 TERMINFO/TERMINFO_DIRS，但 build() 的
        # conanbuild 环境不含依赖 runenv，故这里按依赖包目录显式指过去。
        # 功能性断言在 test_package（那里走 conanrun，runenv 自带 TERMINFO）。
        # 用 bin/ex 而非 `vi -e -s`：上游 vi 模式的 getopt 串不含 -s
        # （optstr[1]="c:C:eFlRrSt:w:"），只有 ex 模式串含 s。
        # TMPDIR 指向可写的 build_folder：openvi 的备份临时文件走 $TMPDIR
        # （由本配方 0001-honor-tmpdir.patch 引入），HMFS 的 /tmp 只读，
        # 不指过去会在运行期报 Read-only file system。
        terminfo = f"{pf}/share/terminfo"
        self.run(
            f'export TERM=vt100 TMPDIR="{self.build_folder}" '
            f'TERMINFO="{terminfo}" TERMINFO_DIRS="{terminfo}"; '
            'printf \'a\\nOPENVI_BUILD_SMOKE_OK\\n.\\nwq\\n\' | '
            f'"{src}/bin/ex" -s "{self.build_folder}/smoke.txt"',
            env="conanbuild",
        )
        self.run(f'grep -qx OPENVI_BUILD_SMOKE_OK "{self.build_folder}/smoke.txt"')

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        bindir = os.path.join(pkg, "bin")
        os.makedirs(bindir, exist_ok=True)

        # 上游 install 用 ln -s 生成 ex/view 别名（argv[0] 决定模式）；
        # 制品里改用同内容副本，避免 Conan 打包 symlink 的解析差异。
        vi_bin = os.path.join(src, "bin", "vi")
        for name in ("vi", "ex", "view"):
            target = os.path.join(bindir, name)
            shutil.copyfile(vi_bin, target)
            os.chmod(target, 0o755)
        xinstall = os.path.join(src, "bin", "xinstall")
        shutil.copyfile(xinstall, os.path.join(bindir, "xinstall"))
        os.chmod(os.path.join(bindir, "xinstall"), 0o755)

        copy(self, "vi.1", src=os.path.join(src, "docs", "USD.doc", "vi.man"),
             dst=os.path.join(pkg, "share", "man", "man1"))
        copy(self, "virecover.8", src=os.path.join(src, "scripts"),
             dst=os.path.join(pkg, "share", "man", "man8"))
        copy(self, "virecover", src=os.path.join(src, "scripts"),
             dst=os.path.join(pkg, "libexec"))
        copy(self, "README*.md", src=src,
             dst=os.path.join(pkg, "share", "doc", "openvi"))
        copy(self, "LICENSE.md", src=src, dst=os.path.join(pkg, "licenses"))
        copy(self, "LICENSES/*", src=src, dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
