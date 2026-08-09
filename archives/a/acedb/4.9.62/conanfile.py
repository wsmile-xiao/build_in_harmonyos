#!/usr/bin/env python3
"""Conan recipe — acedb 4.9.62 (ACeDB genome database, Sanger 归档分支，HarmonyOS PC aarch64 适配).

- 上游：https://github.com/richarddurbin/acedb（Sanger Institute 归档，4.9.62）
- 构建：自定义 wmake 系统（ACEDB_MACHINE=OHOS_4，顶层 makefile 驱动 truemake）
- 鸿蒙适配：
  1. 新增 wmake/OHOS_4_DEF：clang15/aarch64/OHOS 构建定义（无 GTK2，仅 glib 命令行工具）
  2. graph.h/gex.h/genebuilder.h/smapmethods.h 的 GTK 包含条件化（ACEDB_NO_GTK）
  3. mystdlib.h/mydirent.h 适配 OHOS sysroot（qsort 原型、dirent.h）
  4. truemake SHELL 与 perl shebang 改为 OHOS 实际路径
- 依赖：glib-2.0 / readline / ncurses / flex(libfl) 由 cmd-pkgs 预编译包提供（非 conan 依赖）
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    get, copy, apply_conandata_patches, export_conandata_patches, chmod,
)
from conan.tools.layout import basic_layout


def _get_prefix():
    """Get the prefix for installing/finding system dependencies.

    Always returns a user-writable path (never /usr/local).
    Uses DEFAULT_PREFIX env var (set by CI/HNP environment) or ~/usr/local.
    """
    prefix = os.environ.get("DEFAULT_PREFIX")
    if prefix:
        return prefix
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _lib_exists(prefix, libnames):
    for lib in libnames:
        if os.path.exists(os.path.join(prefix, "lib", lib)):
            return True
    return False


def _install_cmd_pkg(name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package (pure Python).

    CI worker 环境无 curl（PATH 中不存在），install.sh 内部也依赖 curl
    下载包体，因此这里直接用 Python urllib 下载 tar.gz、tarfile 解压，
    完全不依赖 curl / install.sh。
    包结构为扁平布局（bin/ lib/ share/ 顶层），解压到 prefix 即可。
    """
    import tarfile
    import urllib.request

    url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/"
           f"{name}-{version}-ohos-aarch64.tar.gz")
    os.makedirs(prefix, exist_ok=True)
    tarball = os.path.join(prefix, f".install-{name}-{version}.tar.gz")
    try:
        urllib.request.urlretrieve(url, tarball)
        with tarfile.open(tarball, "r:gz") as tar:
            # HMDFS 上覆盖已有文件会失败（Operation not permitted），
            # 先删除将被覆盖的目标文件（与 install.sh 的 rm-then-copy 策略一致）
            for m in tar.getmembers():
                target = os.path.join(prefix, m.name)
                if os.path.isfile(target):
                    try:
                        os.remove(target)
                    except OSError:
                        pass
            tar.extractall(prefix)
    finally:
        try:
            os.remove(tarball)
        except OSError:
            pass


class AcedbConan(ConanFile):
    name = "acedb"
    version = "4.9.62"
    description = "ACeDB — genome database system (Sanger 归档分支, OHOS adapted)"
    license = "GPL-2.0"
    homepage = "https://github.com/richarddurbin/acedb"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib/readline/ncurses 由 cmd-pkgs 预编译包提供（系统依赖，非 conan 包）
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "acedb is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()

        # 系统依赖：pcre2（glib 的 Requires 依赖，必须先装）/ glib / readline / ncurses（含 flex 的 libfl）由 cmd-pkgs 提供
        if not _lib_exists(prefix, ["libpcre2-8.a", "libpcre2-8.so"]):
            _install_cmd_pkg("pcre2", "10.40", prefix)
        if not _lib_exists(prefix, ["libglib-2.0.a", "libglib-2.0.so"]):
            _install_cmd_pkg("glib", "2.88.0", prefix)
        if not _lib_exists(prefix, ["libreadline.a", "libreadline.so"]):
            _install_cmd_pkg("readline", "8.2", prefix)
        if not _lib_exists(prefix, ["libncursesw.a", "libcurses.a"]):
            _install_cmd_pkg("ncurses", "6.4", prefix)
        # cmd-pkgs ncurses 只提供 libncursesw，补充 libcurses 符号链接（truemake 用 -lcurses）
        if not _lib_exists(prefix, ["libcurses.a"]):
            src = os.path.join(prefix, "lib", "libncursesw.a")
            if os.path.exists(src):
                os.symlink("libncursesw.a", os.path.join(prefix, "lib", "libcurses.a"))
        # flex 的 libfl.a 提供 -lfl（truemake LEX_LIBS）
        if not _lib_exists(prefix, ["libfl.a"]):
            flex_lib = "/data/service/hnp/flex.org/flex_2.6.4/lib/libfl.a"
            if os.path.exists(flex_lib):
                copy(self, "libfl.a", os.path.dirname(flex_lib),
                     os.path.join(prefix, "lib"))

    def build(self):
        # R33: 从 conan conf 取编译器，禁止 ${CC}/${CFLAGS} 裸用。
        # profile 中 tools.build:compiler_executables 是 {"c": ..., "cpp": ...} 字典。
        cc_map = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = cc_map.get("c", "clang")
        del cc  # wmake 的 OHOS_4_DEF 内部已固定 clang，无需传入

        # 构建环境变量（wmake 需要 ACEDB_MACHINE；pkg-config/ld 需要 cmd-pkgs 前缀）
        prefix = _get_prefix()
        os.environ["ACEDB_MACHINE"] = "OHOS_4"
        os.environ.setdefault("SHELL", "/data/service/hnp/bin/bash")
        os.environ.setdefault("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pkgcfg = os.path.join(prefix, "lib", "pkgconfig")
        os.environ["PKG_CONFIG_PATH"] = pkgcfg + os.pathsep + os.environ.get("PKG_CONFIG_PATH", "")
        libdir = os.path.join(prefix, "lib")
        os.environ["LD_LIBRARY_PATH"] = libdir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")

        # 顶层 makefile 是 wmake/makefile 的入口
        if not os.path.exists(os.path.join(self.source_folder, "Makefile")):
            os.symlink("wmake/makefile", os.path.join(self.source_folder, "Makefile"))
        # 核心命令行/服务端工具 + 上游 MD5 测试程序（不依赖 GTK2）
        self.run("make -j1 libfree.a libace.a tace taql saceserver saceclient "
                 "acediff acediffsorted makeUserPasswd tagcount md5test",
                 cwd=self.source_folder)

    def package(self):
        import shutil
        # OHOS 限制：strip 后的 ELF 在 hmdfs 上无法执行，直接复制未 strip 二进制
        bin_src = os.path.join(self.source_folder, "bin.OHOS_4")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for exe in ["tace", "taql", "saceserver", "saceclient",
                    "acediff", "acediffsorted", "makeUserPasswd", "tagcount",
                    "mddriver", "digtest"]:
            src = os.path.join(bin_src, exe)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(bin_dir, exe))
                chmod(self, os.path.join(bin_dir, exe), 0o755)

    def package_info(self):
        # 可执行程序包，无库供下游链接；bin 目录注入运行环境 PATH
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
