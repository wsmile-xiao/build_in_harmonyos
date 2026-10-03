#!/usr/bin/env python3
"""Conan recipe for worklog 2.1 — ncurses 记时/工时表 TUI 程序（纯 Makefile 构建）。

上游事实
--------
* 源码    : https://github.com/atsb/worklog （tag Worklog-2.1）
* 许可证  : public domain（作者 Truxton King Fulton II 声明）
* 构建    : 单一 worklog.c + 手写 Makefile，无 configure/autotools、无 `make check`
* 依赖    : ncurses（OHOS 侧必须静态；本仓 ncurses/6.6 只产出 libncursesw.a）
* 产物    : bin/worklog（可执行 CLI → 软件级 commands.json，R38）+ man1/worklog.1.gz

OHOS 适配要点
------------
* 交叉编译器从 self.conf 取（R33：不裸用 ${CC}），不依赖 shell 环境变量。
* 上游 Makefile 硬编码 gcc → 补丁改为 $(CC)，见 patches/0001-*.patch。
* -lncurses 在 OHOS 依赖下无库可链（ncurses/6.6 只提供 libncursesw.a），
  因此 LIBS 由命令行覆盖为 -lncursesw。
* ncurses 头文件路径通过 EXTRA_CFLAGS 追加，避免覆盖上游 CFLAGS 中
  需要 shell 二次引号处理的 -DVERSIONS=\"2.1\"。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class WorklogConan(ConanFile):
    name = "worklog"
    version = "2.1"
    description = "ncurses program for keeping track of time spent on different projects"
    license = "Unlicense"
    homepage = "https://github.com/atsb/worklog"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses/6.6 在 OHOS 上拒绝 shared（R26：避免遮蔽系统
        # libncursesw.so.6），静态库经 transitive_* 传递给下游链接。
        self.requires("ncurses/6.6", transitive_headers=True, transitive_libs=True)

    def validate(self):
        # R32：settings.os 判断必须兼容 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"worklog supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        """交叉编译器路径：取自 Conan toolchain conf，不读 shell 环境（R33）。

        OHOS 目标下若 conf 缺 compiler_executables，直接失败而不是回退到裸
        "clang"：裸 clang 会按宿主架构编译，产出一个「看似成功、实则不是
        OHOS 二进制」的包（静默降级比报错更危险）。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") if compilers else None
        if not cc:
            if str(self.settings.os) == "OHOS":
                raise ConanInvalidConfiguration(
                    "tools.build:compiler_executables['c'] is required for OHOS "
                    "cross builds; refusing to fall back to a host-arch compiler"
                )
            return "clang"
        return cc

    def _make_flags(self):
        """构造 make 命令行变量覆盖（CC / EXTRA_CFLAGS / EXTRA_LDFLAGS / LIBS）。"""
        ncurses = self.dependencies["ncurses"].cpp_info
        # -U_FORTIFY_SOURCE 必须排在 EXTRA_CFLAGS（追加在上游 CFLAGS 之后），
        # 才能抵消上游硬写的 -D_FORTIFY_SOURCE=2。OHOS 的 libc 是 musl 系，
        # 不提供 glibc 专有的 __vsprintf_chk / __strcat_chk / __strlen_chk；
        # 保留 _FORTIFY_SOURCE 会让二进制在 OHOS 上直接装载失败：
        #   "Error relocating .../worklog: __vsprintf_chk: symbol not found"
        # 去掉 fortify 后改用 -fstack-protector-strong 保留栈保护加固。
        extra_cflags = " ".join(
            ["-U_FORTIFY_SOURCE", "-fstack-protector-strong"]
            + [f"-I{d}" for d in ncurses.includedirs]
        )
        # -L 必须显式给出：依赖库在 conan cache 内，不在系统默认搜索路径。
        extra_ldflags = " ".join(f"-L{d}" for d in ncurses.libdirs)
        # 上游默认 -lncurses；OHOS 依赖只提供宽字符静态库 libncursesw.a。
        # -z now 保留上游的全 RELRO 链接加固。
        libs = "-lncursesw -lm -z now"
        return (
            f"CC={self._cc()} "
            f"EXTRA_CFLAGS='{extra_cflags}' "
            f"EXTRA_LDFLAGS='{extra_ldflags}' "
            f"LIBS='{libs}'"
        )

    def build(self):
        apply_conandata_patches(self)
        self.run(f"make -j1 {self._make_flags()}")

    def package(self):
        # 上游 Makefile 的 BIN/MAN 变量默认值已内嵌 $(DESTDIR)
        # （BIN=$(DESTDIR)/usr/bin、MAN=$(DESTDIR)/usr/share/man/man1），
        # 在命令行覆盖它们即可精确控制安装位置：W3 实测若只传 DESTDIR，
        # 产物会落在 usr/bin/ 而非本仓约定的顶层 bin/。
        # 用绝对路径覆盖可完全绕开 make 变量展开的引号歧义。
        # 补丁已修掉上游 install 规则里 MAN 重复拼接 man1 的 bug。
        pkg = self.package_folder
        self.run(
            f"make install {self._make_flags()} "
            f"PREFIX= DESTDIR= "
            f"BIN='{os.path.join(pkg, 'bin')}' "
            f"MAN='{os.path.join(pkg, 'share', 'man', 'man1')}'"
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "worklog"),
        )
        copy(
            self,
            "worklog.lsm",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "worklog"),
        )

    def package_info(self):
        # 纯 CLI 工具：无库、无头文件，只贡献可执行文件目录。
        self.cpp_info.bindirs = ["bin"]
