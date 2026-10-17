#!/usr/bin/env python3
"""Conan recipe for mmh 0.4 — 现代化 MH 邮件系统 / MIME 命令行邮件客户端。

mmh（meillo's mail handler）是经典 MH 系统的现代化重写：消息以
「一条消息一个文件」的模块化方式存储（文件夹即目录），提供完整的
MIME 支持（mhbuild 构建、mhlist/mhshow 浏览、mhstore 提取附件）、
gpg 集成（mhsign/mhpgp）、模板/别名/分发列表与 pick 条件检索等。
许可证为 BSD 三条款式（上游 COPYRIGHT）。

上游: https://marmaro.de/prog/mmh/  （v0.4，2019-01-06）

构建:  autotools（手写 Makefile.in，无 automake）。唯一外部依赖 ncurses。
产物:  bin/ 40 个命令（34 个 C 程序 + 6 个脚本）与 8 个命令链接、
       lib/ 辅助二进制；package_type=application。

R3: 十三条补丁均由 `refresh-patch --auto` 生成（per-file-difflib），
    不手工落盘：
    - 0001-config.guess.patch        2005 年版 config.guess 增加 HarmonyOS 分支
    - 0002-config.sub.patch          补 aarch64 CPU 与 linux-ohos 内核-OS（4 处）
    - 0003-configure.patch           tgetent 探测顺序补 ncursesw；放宽
                                     config.status 临时目录 umask（HMDFS）
    - 0004-configure.ac.patch        同步 configure.ac 的 ncursesw 顺序
    - 0005-man-Makefile.in.patch     man 目录构建脚本（version.sh/gettitles.sh/
                                     mh-chart-gen.sh）改 sh 前缀驱动
    - 0006-sbr-Makefile.in.patch     version.o 的 -DVERSION 同因改 sh 前缀
    - 0007-sbr-folder_addmsg.c.patch 入箱复制回退从 EXDEV 扩展到
                                     EPERM/EOPNOTSUPP（HMDFS 无硬链接）
    - 0008-sbr-path.c.patch          etcpath() 支持 MMHETC 环境变量覆写
                                     etc 目录（conan 包布局：format/
                                     component 文件随包装在包内 etc/，
                                     编译期 NMHETCDIR 无从指向）
    - 0009-test-setup-test.patch     测试套件临时目录改用 ${TMPDIR:-/tmp}
    - 0010-uip-Makefile.in.patch     各命令编译期版本串同因改 sh 前缀
    - 0011-uip-mhpgp.sh.patch        mhpgp 临时目录改用 ${TMPDIR:-/tmp}
    - 0012-uip-mhsign.sh.patch       mhsign 临时目录改用 ${TMPDIR:-/tmp}
    - 0013-uip-sendfiles.sh.patch    sendfiles 草稿临时文件改用 ${TMPDIR:-/tmp}
    （0009/0011-0013：OHOS 根文件系统只读、/tmp 不可写；
      0005/0006/0010：OHOS 内核拒 shebang 脚本 execve；
      0008：包管理/cache 布局定位，非 OHOS 特有）
R26: ncurses 静态链接（shared=False）。
R1: 依赖 ncurses/6.6 + 一个业务开关 --with-locking=fcntl（mmh 默认
    dot-lock 依赖 link(2) 创建锁文件，HMDFS 拒绝硬链接返回 EPERM），
    不加 --build/--host；CFLAGS 仅追加 -fcommon（2019 年版 C 代码的
    `char *tmp;` 暂定定义依赖 GCC<10 合并语义，clang≥11 默认
    -fno-common 会链接期 duplicate symbol），不做其他 CFLAGS/LIBS hack。
    install 以 LN=cp 替代 uip/Makefile 的 8 个硬链接命令链接
    （HMDFS link(2) EPERM；命令本体为 argv[0] 分派，副本语义等价）。
"""

import os
import time

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 发行包预生成产物（2019 年 autoconf/flex 产物，与宿主工具不同代）：
# 冻结时间戳，禁止 make 从 configure.ac / dtimep.lex 重新生成
# （根 Makefile 有 configure/stamp-h.in 规则，sbr/Makefile 有 dtimep 规则）。
_GENERATED = (
    "configure", "config.h.in", "stamp-h.in", "sbr/dtimep.c",
)


class MmhConan(ConanFile):
    name = "mmh"
    version = "0.4"
    description = (
        "mmh — modern MH mail system: scriptable MIME email client "
        "(message-per-file storage, mhbuild/mhlist/mhstore, gpg support)"
    )
    license = "BSD-3-Clause"
    homepage = "https://marmaro.de/prog/mmh/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        # mmh 只产出可执行文件，不需要共享库
        self.options.rm_safe("shared")
        self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # termcap 接口由 ncurses 提供；制品仓 ncurses/6.6 只有宽字符库
        # libncursesw.a（见 0003 补丁）
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # mmh 用标准 AC_CHECK_LIB 探测 termcap 接口；依赖包的 -I/-L/-l
        # 由 AutotoolsDeps 注入 CPPFLAGS/LDFLAGS/LIBS（conan 2 起依赖旗标
        # 与 AutotoolsToolchain 分离，后者只出工具链与构建型旗标），
        # ncurses 探测由 0003 补丁补上 ncursesw 后即可命中。
        tc = AutotoolsToolchain(self)
        # 锁机制：mmh 默认 dot-lock（configure.ac: --with-locking 默认
        # dot），其锁文件创建依赖 link(2) 的原子性；HMDFS 拒绝硬链接
        # （EPERM），dot-lock 会等待 5 次后失败。改用内核锁
        # （FCNTL_LOCKING -> lkopen_kernel，F_SETLK 建议锁）。
        tc.configure_args.append("--with-locking=fcntl")
        # 2019 年版 C 代码依赖 GCC<10 的暂定定义合并（char *tmp; 在
        # mhbuild.c/mhparse.c 各定义一次、另四处 extern 共享），clang≥11
        # 默认 -fno-common 会链接期 duplicate symbol；-fcommon 复现上游
        # 构建语义（非源码缺陷，不落补丁）。
        tc.extra_cflags.append("-fcommon")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def _freeze_generated(self):
        """把预生成产物时间戳统一压到“现在”，使其不早于补丁后的
        configure.ac / dtimep.lex，避免 make 触发 autoconf/autoheader/
        flex 重新生成（宿主工具版本与 2019 年产物不兼容）。"""
        now = time.time()
        for rel in _GENERATED:
            path = os.path.join(self.source_folder, rel)
            if os.path.exists(path):
                os.utime(path, (now, now))

    def build(self):
        apply_conandata_patches(self)
        self._freeze_generated()
        autotools = Autotools(self)
        autotools.configure()
        # -j1：OHOS 上 make jobserver 依赖 mkfifo，HMDFS 不支持，禁用并行更稳
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # -j1：同 build()，HMDFS 上 make jobserver 依赖 mkfifo
        # LN=cp：install-lcmds 用 8 个硬链接造命令别名（flists/folders/...），
        # HMDFS 拒绝 link(2)（EPERM，真机探针实测），复制语义等价
        autotools.install(args=["-j1", "LN=cp"])
        copy(self, "COPYRIGHT",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 工具类包：暴露 bin/ 供下游消费（辅助二进制安装在 lib/）
        self.cpp_info.bindirs = ["bin"]
        self.output.info("mmh 0.4: bin/ 命令与链接（MIME 邮件客户端）")
        # R38 — CLI 工具声明
        self.conf_info.define("user.tools.mmh:exe", "mmh")
        # 运行期数据目录（0013 补丁 + VirtualRunEnv）：conan 以
        # --prefix=/ + DESTDIR 打包，编译期 NMHETCDIR 固定为 /etc，
        # 而 format/component 文件（scan.default、pick.default、
        # mhn.defaults、components 等）随包装在 <pkg>/etc/；MMHETC
        # 让 etcpath() 在编译期路径之前定位到包内文件。
        self.runenv_info.define_path(
            "MMHETC", os.path.join(self.package_folder, "etc"))
