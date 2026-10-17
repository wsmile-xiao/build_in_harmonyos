#!/usr/bin/env python3
"""Conan recipe for ccze 0.2.1 — 日志着色器（CCZE, log colorizer）。

ccze（cornet/ccze）是 C 语言日志着色工具（syslog/dpkg/httpd 等
日志高亮），autotools 构建。上游无 tag（GitHub tags 为空），
NEWS/ChangeLog 确认最新发布版 0.2.1（2003-05-13 Fireflower）——
清单 1.0.0 与上游不符，按用户指示用真实版本 0.2.1。

Upstream: cornet/ccze master（无 tag——用 master tarball 作源）。

Build:   autotools（configure + make）。依赖 ncurses（制品仓
         6.4/6.5/6.6 可用——AC_CHECK_LIB(ncurses, initscr)）。
Install: bin/ccze + man。
Type:   application（CLI 工具——commands.json 软件级声明）

Deps:   ncurses（必需）；dl/PCRE 可选（configure 检测到才用）。

上游测试: testsuite/（bug-*.test + .in 输入 + .ok 期望）——
         make check 实跑验证。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CczeConan(ConanFile):
    name = "ccze"
    version = "0.2.1"
    description = "CCZE - A fast log colorizer"
    license = "GPL-2.0"
    homepage = "https://github.com/cornet/ccze"
    url = "https://github.com/cornet/ccze"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # ncurses/6.4 有 cppstd=17 匹配二进制（6.5 制品仓无对应二进制）；
    # pcre/8.45 制品仓有完整包（pcre-config + pcre.h + libpcre.a）
    requires = "ncurses/6.4", "pcre/8.45"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判 zip（同款），
        # 显式 filename
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ccze-master.tar.gz")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 老 config.guess 不识 HarmonyOS——显式 build 三元组
        # （catdoc/boa 同款）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.extra_defines.append("PACKAGE_VERSION=\"0.2.1\"")
        tc.generate()
        # ncurses/pcre include/lib 路径经环境变量注入（AutotoolsToolchain
        # 无 cppflags 属性——用 CPATH/LIBRARY_PATH，ccbuild 同款）；
        # pcre-config 脚本路径注入 PATH（configure AC_PATH_PROG 检测）
        nc = self.dependencies["ncurses"].package_folder
        pc = self.dependencies["pcre"].package_folder
        env = Environment()
        env.append_path("CPATH", os.path.join(nc, "include"))
        env.append_path("LIBRARY_PATH", os.path.join(nc, "lib"))
        env.append_path("CPATH", os.path.join(pc, "include"))
        env.append_path("LIBRARY_PATH", os.path.join(pc, "lib"))
        env.append_path("PATH", os.path.join(pc, "bin"))
        env.vars(self).save_script("conanbuild_dep_env")

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # ncurses 制品仓包只有 wide 版（libncursesw.a，无 libncurses.a）
        # ——configure 脚本的 AC_CHECK_LIB(ncurses, initscr) 检测
        # -lncurses 失败，改为 -lncursesw（initscr 等基础 API 同源，
        # ccze 仅 include <ncurses.h> + initscr 等宽字符兼容）
        cf = os.path.join(self.source_folder, "configure")
        with open(cf, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        # 全量替换 -lncurses → -lncursesw（检测消息 + LIBS 赋值 +
        # conftest 测试链接行——ccze 仅依赖 ncurses，无冲突）
        s = s.replace("-lncurses", "-lncursesw")
        # confstat 机制用 `umask 077 && mktemp -d ./confXXXXXX` 创建
        # 0700 临时目录做 config 文件生成——OHOS HMDFS 上 0700 目录
        # 对构建进程不可写（catdoc/boa 同款）——patch umask 077→000
        s = s.replace("(umask 077 && mktemp -d \"./confXXXXXX\")",
                      "(umask 000 && mktemp -d \"./confXXXXXX\")")
        s = s.replace("(umask 077 && mkdir \"$tmp\")",
                      "(umask 000 && mkdir \"$tmp\")")
        with open(cf, "w", encoding="utf-8") as f:
            f.write(s)
        # src/ccze-compat.h 模拟 argp（configure 检测无 argp.h 走兼容
        # 路径）但缺少 glibc argp.h 的 `typedef int error_t;`——clang
        # 报 function cannot return function type（error_t 未定义）。
        # 补 typedef（仅兼容路径生效——HAVE_ARGP_PARSE 定义时不编译）
        ch = os.path.join(self.source_folder, "src", "ccze-compat.h")
        with open(ch, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("#ifndef HAVE_ARGP_PARSE",
                      "#ifndef HAVE_ARGP_PARSE\ntypedef int error_t;")
        with open(ch, "w", encoding="utf-8") as f:
            f.write(s)
        autotools = Autotools(self)
        autotools.configure()
        # configure 在 build_folder 生成 Makefile——make 默认 cwd 即
        # build_folder（勿用 source_folder）；-j1 绕 OHOS 禁 mkfifo
        # jobserver（catdoc/boa 同款）。必须用 conanbuild 环境——
        # CPATH/LIBRARY_PATH 依赖注入（pcre/ncurses）在 conanbuild_dep_env
        # 中，conanrun 环境不含
        self.run("make -j1", env="conanbuild")

    def package(self):
        # make install 已装 bin/ccze + man + lib/ccze 插件
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.output.info("ccze 0.2.1: bin/ccze")
        # R38 — CLI 工具
        self.conf_info.define("user.tools.ccze:exe", "ccze")
