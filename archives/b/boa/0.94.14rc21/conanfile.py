#!/usr/bin/env python3
"""Conan recipe for boa 0.94.14rc21 — classic embedded Web server (C, autoconf).

boa 是经典嵌入式 Web 服务器（单进程 HTTP daemon，C 语言，autoconf 2.59
构建）。上游 boa.org 官方站点已下线——源码取自 Debian snapshot 官方归档的
boa_0.94.14rc21.orig.tar.gz（boa.org 官方 tarball 的 Debian 归档镜像，
sha256 固定校验一致）。

依赖：仅 libc（configure.in 中 dmalloc/efence 为可选检测——OHOS 无则
跳过，不阻塞构建）。无 Conan 前置依赖。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BoaConan(ConanFile):
    name = "boa"
    version = "0.94.14rc21"
    description = "Classic single-process embedded Web server (HTTP daemon)"
    license = "GPL-2.0-or-later"
    homepage = "http://www.boa.org/"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("boa is supported only on Linux/OHOS")

    def requirements(self):
        # 仅 libc（系统自带）；dmalloc/efence 为 configure 可选检测，OHOS
        # 无则自动跳过——无 Conan 前置依赖
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess 为 2004 年老版本（autoconf 2.59）——不认识
        # HarmonyOS/aarch64，configure 报 "cannot guess build type"——
        # 显式指定 build 三元组绕过（ncurses/groonga 同款教训）
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
        ])
        # OHOS musl libc 无 glibc 的 MAXNAMLEN 宏（index_dir.c 用它）——
        # 用 POSIX NAME_MAX 替代（<limits.h> 定义，musl 有）
        tc.cflags.append("-DMAXNAMLEN=NAME_MAX")
        # sendfile 为可选 Linux 系统调用检测（configure 自带 --disable-sendfile）；
        # 无额外 configure 参数——保持上游默认（OHOS 无则自动关闭）
        tc.generate()

    def build(self):
        # patch configure：config.status 的 confstat 临时目录创建用
        # `umask 077 && mktemp -d -q "./confstatXXXXXX"`——0700 目录在
        # OHOS HMDFS 上写入 Permission denied（config.status 生成
        # Makefile/src/config.h 时必然失败）——umask 改 000 后实测可写
        # （mkdir fallback 的 2771 目录同样可写，此处一并统一为 000）
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            with open(cfg, "r", encoding="latin-1") as f:
                s = f.read()
            s = s.replace(
                '(umask 077 && mktemp -d -q "./confstatXXXXXX")',
                '(umask 000 && mktemp -d -q "./confstatXXXXXX")')
            s = s.replace("(umask 077 && mkdir $tmp)",
                          "(umask 000 && mkdir $tmp)")
            with open(cfg, "w", encoding="latin-1") as f:
                f.write(s)
        # OHOS musl libc 无 glibc 的 MAXNAMLEN 宏（<dirent.h> 中，musl
        # 只有 NAME_MAX）——index_dir.c 用 MAX_FILE_LENGTH=MAXNAMLEN 编译
        # 报 undeclared——patch 源码用 NAME_MAX（<limits.h> 已 include）
        idx = os.path.join(self.source_folder, "src", "index_dir.c")
        if os.path.isfile(idx):
            with open(idx, "r", encoding="latin-1") as f:
                s = f.read()
            s = s.replace("#define MAX_FILE_LENGTH                         MAXNAMLEN",
                          "#define MAX_FILE_LENGTH                         NAME_MAX")
            with open(idx, "w", encoding="latin-1") as f:
                f.write(s)
        autotools = Autotools(self)
        autotools.configure()
        # OHOS 沙箱禁 mkfifo（Operation not permitted）——make -jN 的
        # jobserver 需要 mkfifo——显式 -j1 绕 jobserver（nawk 同款教训）
        autotools.make(args=["-j1"])

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # 构建产物：src/boa（主服务）+ src/boa_indexer（目录索引生成器）
        copy(self, "boa", src=os.path.join(self.build_folder, "src"),
             dst=bin_dir, keep_path=False)
        copy(self, "boa_indexer", src=os.path.join(self.build_folder, "src"),
             dst=bin_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
