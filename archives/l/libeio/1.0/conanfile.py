#!/usr/bin/env python3
"""Conan recipe — libeio 1.0 (Autotools).

libeio: 异步 I/O 系统调用封装库（libev 作者 Marc Lehmann 出品），公开
eio_init/eio_wd_open/eio_readdir 等异步文件 I/O API。纯 C，无第三方依赖。

OHOS adaptation:
  * 官方 master tarball 不含预生成 configure（仅 configure.ac/Makefile.am），
    build() 先跑 autoreconf（autogen.sh 等价命令）生成 configure。
  * CI 沙箱(USER=100)对 $HOME/.local 手工安装的 automake/libtool 不可见，
    故将 automake + libtool 作为 tool_requires 拉入（制品仓已发布 1.18/2.5.4，
    同 abiword-plugin-* 先例）。
  * OHOS 的 config.guess 无法识别 HarmonyOS kernel，configure 报
    "cannot guess build type"；与 libstatgrab 同策略，显式传
    --build/--host=aarch64-unknown-linux-gnu（ABI 层面等价 Linux-ELF；
    libeio.m4 无 AC_RUN_IFELSE，不会跳过运行时检测）。
  * patches/0001-ecb.h.patch：C11 下 ecb_noreturn 原展开为 _Noreturn，
    旧版 ecb 将其放在函数声明尾部，现代 clang 要求 _Noreturn 前置；
    改为 ecb_attribute((__noreturn__))。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibeioConan(ConanFile):
    name = "libeio"
    version = "1.0"
    description = "libeio 1.0"
    license = "MIT"
    homepage = "https://github.com/scunningham/libeio"
    url = "https://github.com/scunningham/libeio"  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # tarball 无 configure，需 autoreconf；CI 沙箱无系统 automake/libtool
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS: config.guess 无法识别 HarmonyOS kernel，显式指定 build/host
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 官方 tarball 无 configure：先 autoreconf 生成（对应 autogen.sh）
        autotools.autoreconf(args=["--install", "--symlink", "--force"])
        if self.settings.os == "OHOS":
            # E011/E114: autoconf configure/config.status 用
            # `umask 077 && mktemp -d ./confXXXXXX` 在构建目录建 0700/setgid
            # 临时目录写 subs1.awk；CI worker UID(20020102, 解析 unknown) 与
            # 目录属主不一致且 HMDFS 不保留 POSIX 权限位 → Permission denied、
            # "could not setup config files machinery"。修法同 libdap/
            # abiword-plugin-docbook 先例：预建可写目录并把 configure 内嵌
            # config.status 模板的 ac_tmp 改指该目录，同时去掉退出 trap 的
            # rm -fr（防删掉预建目录）。
            _fixed_tmp = os.path.join(
                os.path.expanduser("~"), "tmp", "libeio-ac-tmp"
            )
            os.makedirs(_fixed_tmp, exist_ok=True)
            # TMPDIR 不能指向 HMDFS：make jobserver 用 mkfifo 建 GMfifo*，
            # HMDFS 不支持 FIFO（E074）→ 递归 make 崩；指向 el2 缓存可写区。
            for _cand in ("/data/storage/el2/base/cache",
                          "/data/storage/el2/base/temp"):
                if os.path.isdir(_cand):
                    os.environ["TMPDIR"] = _cand
                    os.environ["TMP"] = _cand
                    os.environ["TEMP"] = _cand
                    break
            _cfg_path = os.path.join(self.source_folder, "configure")
            with open(_cfg_path, "r", encoding="utf-8", errors="ignore") as _f:
                _cfg = _f.read()
            if "ac_tmp=$tmp" in _cfg:
                _cfg = _cfg.replace("ac_tmp=$tmp",
                                    "ac_tmp={}".format(_fixed_tmp))
                _old_trap = ('{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } '
                             '&& exit $exit_status')
                _new_trap = "exit $exit_status"
                if _old_trap in _cfg:
                    _cfg = _cfg.replace(_old_trap, _new_trap)
                with open(_cfg_path, "w", encoding="utf-8") as _f:
                    _f.write(_cfg)
                os.chmod(_cfg_path, 0o755)
                self.output.info(
                    "  [ohos] E011/E114 fix: ac_tmp -> {}".format(_fixed_tmp))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 产物为 libeio.a / libeio.so（libtool 命名 libeio.la），链接标志 -leio
        self.cpp_info.libs = ["eio"]