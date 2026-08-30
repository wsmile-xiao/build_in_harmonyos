#!/usr/bin/env python3
"""Conan recipe for cdrdao 1.2.6 — CD 刻录工具（cdrecord 兼容，C++）。

cdrdao（cdrdao/cdrdao）是 CD 刻录工具（C++），autotools 构建。
版本 1.2.6 为上游 tag rel_1_2_6（用户给 1.0.0 不合法——按真实
版 1.2.6，Debian 1:1.2.6-1 确认）。

Upstream: https://codeload.github.com/cdrdao/cdrdao/tar.gz/refs/tags/rel_1_2_6

Build:   autotools（configure + make）。依赖 pthread/socket（系统
         库）+ 可选 libcdio/ncurses/zlib/pcre（制品仓均有 ✅）。
Install: bin/cdrdao + bin/gcdmaster。
Type:   application（CLI 工具——commands.json 软件级声明）

上游测试: testtocs/test（TOC 解析测试，纯工具可实跑）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import get
from conan.tools.layout import basic_layout


class CdrdaoConan(ConanFile):
    name = "cdrdao"
    version = "1.2.6"
    description = "CD-R/CD-RW burning tool with DAO mode (cdrecord compatible)"
    license = "GPL-2.0"
    homepage = "https://cdrdao.sourceforge.net/"
    url = "https://github.com/cdrdao/cdrdao"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # pthread/socket 系统库 + libcdio/ncurses/zlib/pcre（制品仓均有）
    requires = "libcdio/2.3.0", "ncurses/6.4", "zlib/1.3.1", "pcre/8.45"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判 zip（BadZipFile，
        # batsignal/c4project 同款），显式 filename
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="cdrdao-1.2.6.tar.gz")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 老 config.guess 不识 HarmonyOS——显式 build 三元组
        # （catdoc/boa/ccze 同款）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        # AutotoolsToolchain 无 cppflags——依赖路径经 Environment 注入
        # CPATH/LIBRARY_PATH/PATH（catdoc/boa/ccze 同款）
        env = Environment()
        for dep in ("libcdio", "ncurses", "zlib", "pcre"):
            pkg = self.dependencies[dep].package_folder
            env.append_path("CPATH", os.path.join(pkg, "include"))
            env.append_path("LIBRARY_PATH", os.path.join(pkg, "lib"))
            env.append_path("PATH", os.path.join(pkg, "bin"))
        env.vars(self).save_script("conanbuild_dep_env")

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # cdrdao tarball 无预生成 configure/Makefile.in（只有 configure.ac/
        # Makefile.am），且环境无 automake/aclocal（autoreconf 失败）——
        # 下载 Debian automake .deb 解包，patch 脚本路径后生成构建文件
        import glob
        import subprocess
        from conan.tools.files import download
        amdir = os.path.join(self.build_folder, "am")
        os.makedirs(amdir, exist_ok=True)
        deb = os.path.join(amdir, "automake.deb")
        try:
            download(self,
                     "https://deb.debian.org/debian/pool/main/a/automake/automake_1.18.1-4_all.deb",
                     deb)
        except Exception:
            pass
        if os.path.isfile(deb) and os.path.getsize(deb) > 10000:
            # 解包 Debian automake（ar x + tar xf）——用 self.run 走 conan 环境
            self.run("ar x automake.deb && tar xf data.tar.*", env="conanbuild",
                     cwd=amdir)
            amusr = os.path.join(amdir, "usr")
            # patch automake/aclocal 脚本 @INC + Config.pm libdir 指向解包路径
            for f in ("automake-1.18", "aclocal-1.18"):
                p = os.path.join(amusr, "bin", f)
                if os.path.isfile(p):
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        s = fh.read()
                    s = s.replace("/usr/share/automake-1.18",
                                  os.path.join(amusr, "share", "automake-1.18"))
                    s = s.replace("/usr/share/aclocal-1.18",
                                  os.path.join(amusr, "share", "aclocal-1.18"))
                    s = s.replace("/usr/share/aclocal",
                                  os.path.join(amusr, "share", "aclocal"))
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(s)
            cfg = os.path.join(amusr, "share", "automake-1.18", "Automake", "Config.pm")
            if os.path.isfile(cfg):
                with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
                    s = fh.read()
                s = s.replace("/usr/share/automake-1.18",
                              os.path.join(amusr, "share", "automake-1.18"))
                with open(cfg, "w", encoding="utf-8") as fh:
                    fh.write(s)
            # 生成构建文件（aclocal → autoheader → automake → autoconf）
            env = os.environ.copy()
            env["PERL5LIB"] = os.path.join(amusr, "share", "automake-1.18")
            self.run("cd %s && rm -f aclocal.m4 && perl %s/bin/aclocal-1.18"
                     % (self.source_folder, amusr), env="conanbuild")
            self.run("cd %s && autoheader || true" % self.source_folder,
                     env="conanbuild")
            self.run("cd %s && perl %s/bin/automake-1.18 --add-missing --copy || true"
                     % (self.source_folder, amusr), env="conanbuild")
            self.run("cd %s && autoconf || true" % self.source_folder,
                     env="conanbuild")
        # confstat 机制用 `umask 077 && mktemp -d ./confXXXXXX` 创建 0700
        # 临时目录做 config 文件生成——OHOS HMDFS 上 0700 目录对构建进程
        # 不可写（catdoc/boa/ccze 同款，subs1.awk Permission denied）——
        # patch umask 077→000
        cf = os.path.join(self.source_folder, "configure")
        with open(cf, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("(umask 077 && mktemp -d \"./confXXXXXX\")",
                      "(umask 000 && mktemp -d \"./confXXXXXX\")")
        s = s.replace("(umask 077 && mkdir \"$tmp\")",
                      "(umask 000 && mkdir \"$tmp\")")
        with open(cf, "w", encoding="utf-8") as f:
            f.write(s)
        autotools = Autotools(self)
        # cdrdao 大量相对路径（-I../h、../pccts/antlr/antlr、TocParser.cpp
        # 生成位置）在 out-of-tree 下不工作——改为 in-source 构建
        # （cd source && configure && make）
        # TMPDIR 指向 build_folder——OHOS /tmp 只读，configure 的 ac_link
        # cc 冒烟测试（clang 编译 conftest）写 /tmp 失败 → CI 报
        # "C compiler cannot create executables"（本地 TMPDIR 恰好可写
        # 所以本地 ALL PASS、CI 必挂——cdrecord 同款教训）
        self.run("cd %s && TMPDIR=%s && ./configure --prefix=/ "
                 "--bindir=${prefix}/bin --sbindir=${prefix}/bin "
                 "--libdir=${prefix}/lib --includedir=${prefix}/include "
                 "--oldincludedir=${prefix}/include "
                 "--build=aarch64-unknown-linux-gnu"
                 % (self.source_folder, self.build_folder),
                 env="conanbuild")
        # -j1 绕 OHOS 禁 mkfifo jobserver（catdoc/boa 同款）；
        # env="conanbuild" 使依赖注入生效（conanbuild_dep_env）
        self.run("cd %s && TMPDIR=%s && make -j1"
                 % (self.source_folder, self.build_folder), env="conanbuild")

    def package(self):
        # in-source 构建——install 也在 source 目录跑；-j1 绕 OHOS 禁
        # mkfifo jobserver（autotools.install() 用 -j20 并行会失败）
        self.run("cd %s && make install DESTDIR=%s -j1"
                 % (self.source_folder, self.package_folder), env="conanbuild")

    def package_info(self):
        self.output.info("cdrdao 1.2.6: bin/cdrdao")
        self.conf_info.define("user.tools.cdrdao:exe", "cdrdao")
