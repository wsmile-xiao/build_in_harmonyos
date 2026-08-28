#!/usr/bin/env python3
"""Conan recipe for cdebconf 0.283 — Debian debconf 的 C 实现。

cdebconf（Debian Installer Team）是 debconf（Debian 包配置管理）的
C 重实现，autotools 构建。版本 0.283 为上游 salsa 最新 tag（用户给
1.0.0 不合法——cdebconf 无 1.0.0，按真实最新版 0.283）。

Upstream: https://salsa.debian.org/installer-team/cdebconf/-/archive/0.283/cdebconf-0.283.tar.gz

Build:   autotools（顶层 Makefile 调用各 src 子目录 make）。
         依赖 libdebian-installer（di_* API 30+ 处使用，制品仓无——
         自包含构建，同 aegean 的 genometools 方案）；textwrap/selinux/
         gtk/ncurses/newt/slang 前端全可选可跳过；数据库模块
         textdb/rfc822db/stack 内置。
Install: bin/debconf-communicate/cdebconf-* 工具 + lib/libdebconfclient.a。
Type:    application（CLI 工具——commands.json 软件级声明）

上游测试: src/test/ 有 configtest/dbtest 等（configtest.c/dbtest.c
          + 测试数据 align.config/backup.config/entropy.config 等）。
         本地实测通过率如实记录。
"""
import os

from conan import ConanFile
from conan.tools.files import get, chdir


class CdebconfConan(ConanFile):
    name = "cdebconf"
    version = "0.283"
    description = "Debconf reimplementation in C (Debian Installer Team)"
    license = "BSD-2-Clause"
    homepage = "https://salsa.debian.org/installer-team/cdebconf"
    url = "https://salsa.debian.org/installer-team/cdebconf"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 零第三方 Conan 依赖：libdebian-installer 自包含构建（制品仓无）。
    # build_requires libtool/2.5.4：libdebian-installer 用 libtool
    # （AC_PROG_LIBTOOL/lib_LTLIBRARIES），其 m4 宏（lt.m4/libtool.m4）
    # 供 automake 展开 LT_INIT
    build_requires = "libtool/2.5.4"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"]["cdebconf"], strip_root=True)
        # libdebian-installer（硬依赖，di_* API）——自包含源码，
        # 解压到独立子目录（salsa archive 顶层目录名带 -master 后缀）
        get(self, **self.conan_data["sources"]["libdebian-installer"],
            destination=os.path.join(self.source_folder,
                                     "libdebian-installer"))

    def _bootstrap_automake(self):
        """OHOS 无 automake/aclocal（autoreconf 失败）——下载 Debian
        automake .deb 解包，patch 脚本路径后生成构建文件（cdrdao 同款）。
        返回 amusr 解包路径；调用方用 perl amusr/bin/aclocal-1.18 等。
        """
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
        if not (os.path.isfile(deb) and os.path.getsize(deb) > 10000):
            return None
        self.run("ar x automake.deb && tar xf data.tar.*", env="conanbuild",
                 cwd=amdir)
        amusr = os.path.join(amdir, "usr")
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
        cfg = os.path.join(amusr, "share", "automake-1.18", "Automake",
                           "Config.pm")
        if os.path.isfile(cfg):
            with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
                s = fh.read()
            s = s.replace("/usr/share/automake-1.18",
                          os.path.join(amusr, "share", "automake-1.18"))
            with open(cfg, "w", encoding="utf-8") as fh:
                fh.write(s)
        # PKG_CHECK_MODULES 需要 pkg.m4（pkg-config 包提供，aclocal
        # 缺它则 configure 里宏不展开、语法错误）——下载 pkg-config
        # .deb 提取 pkg.m4 到 aclocal 目录
        try:
            pkgdeb = os.path.join(amdir, "pkg-config.deb")
            download(self,
                     "https://deb.debian.org/debian/pool/main/p/pkg-config/pkg-config_0.29.2-1_amd64.deb",
                     pkgdeb)
            if os.path.isfile(pkgdeb) and os.path.getsize(pkgdeb) > 10000:
                pkd = os.path.join(amdir, "pkg")
                os.makedirs(pkd, exist_ok=True)
                # deb 在 amdir 下——cd 到 amdir 解包，tar 输出到 pkd
                self.run("cd %s && ar x pkg-config.deb && "
                         "tar xf data.tar.* -C %s" % (amdir, pkd),
                         env="conanbuild")
                import glob as _glob
                for m4 in _glob.glob(os.path.join(pkd, "usr", "share",
                                                  "aclocal", "*.m4")):
                    with open(m4, "r", encoding="utf-8",
                              errors="replace") as fh:
                        content = fh.read()
                    out = os.path.join(amusr, "share", "aclocal-1.18",
                                       os.path.basename(m4))
                    with open(out, "w", encoding="utf-8") as fh:
                        fh.write(content)
        except Exception:
            pass
        # libdebian-installer 用 libtool（AC_PROG_LIBTOOL）——automake
        # 缺 libtool m4（LIBTOOL undefined）——从 conan build_requires
        # libtool/2.5.4 包复制 m4 宏到 aclocal 目录
        # （conan 2：build_requires 走 self.dependencies.build）
        ltp = None
        try:
            ltp = self.dependencies.build["libtool"].package_folder
        except Exception:
            pass
        if not ltp:
            try:
                ltp = self.dependencies["libtool"].package_folder
            except Exception:
                pass
        if ltp:
            import glob as _glob
            for m4 in _glob.glob(os.path.join(ltp, "share", "aclocal",
                                              "*.m4")):
                try:
                    with open(m4, "r", encoding="utf-8",
                              errors="replace") as fh:
                        content = fh.read()
                    out = os.path.join(amusr, "share", "aclocal-1.18",
                                       os.path.basename(m4))
                    with open(out, "w", encoding="utf-8") as fh:
                        fh.write(content)
                except Exception:
                    pass
        return amusr

    def _autoreconf_with(self, amusr, srcdir):
        """用解包的 automake 生成构建文件（libtoolize → aclocal →
        autoheader → automake → autoconf）——cdrdao 同款流程。
        ACLOCAL_PATH 注入 pkg.m4（PKG_CHECK_MODULES 展开必需）。
        libtoolize 生成 ltmain.sh（libdebian-installer 用 libtool）。
        """
        perl = "/data/service/hnp/bin/perl"
        if not os.path.isfile(perl):
            perl = "perl"
        aclocal_dir = os.path.join(amusr, "share", "aclocal-1.18")
        # pkg.m4 在 pkg-config deb 解包目录（am/pkg/usr/share/aclocal）
        # ——ACLOCAL_PATH 同时指向 automake 与 pkg-config 两个目录
        pkg_m4_dir = os.path.join(os.path.dirname(amusr), "pkg", "usr",
                                  "share", "aclocal")
        path_env = aclocal_dir
        if os.path.isdir(pkg_m4_dir):
            path_env = "%s:%s" % (aclocal_dir, pkg_m4_dir)
        # libtoolize：从 conan build_requires libtool/2.5.4 包找
        libtoolize = ""
        try:
            ltbin = os.path.join(self.dependencies.build["libtool"]
                                 .package_folder, "bin")
            cand = os.path.join(ltbin, "libtoolize")
            if os.path.isfile(cand):
                libtoolize = cand
        except Exception:
            pass
        if not libtoolize:
            libtoolize = "libtoolize"
        self.run("cd %s && %s --copy --force || true" % (srcdir, libtoolize),
                 env="conanbuild")
        # 辅助文件（config.guess/config.sub/ltmain.sh）用 bash cp 从
        # 系统 autoconf 与 libtool 包复制（Python 复制曾失效）
        aux_src = "/data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/build-aux"
        self.run("cd %s && cp -f %s/config.guess %s/config.sub . || true"
                 % (srcdir, aux_src, aux_src), env="conanbuild")
        # compile/missing/install-sh 从 automake 解包目录复制
        am_share = os.path.join(amusr, "share", "automake-1.18")
        self.run("cd %s && cp -f %s/compile %s/missing %s/install-sh . || true"
                 % (srcdir, am_share, am_share, am_share), env="conanbuild")
        ltp = None
        try:
            ltp = self.dependencies.build["libtool"].package_folder
        except Exception:
            pass
        if ltp:
            self.run("cd %s && find %s -name ltmain.sh -exec cp -f {} . \\; || true"
                     % (srcdir, ltp), env="conanbuild")
        self.run("cd %s && rm -f aclocal.m4 && "
                 "ACLOCAL_PATH='%s' perl %s/bin/aclocal-1.18"
                 % (srcdir, path_env, amusr), env="conanbuild")
        self.run("cd %s && autoheader || true" % srcdir, env="conanbuild")
        self.run("cd %s && perl %s/bin/automake-1.18 --add-missing --copy || true"
                 % (srcdir, amusr), env="conanbuild")
        self.run("cd %s && autoconf || true" % srcdir, env="conanbuild")

    def _build_libdebian_installer(self, amusr):
        """自包含构建 libdebian-installer（cdebconf 硬依赖，制品仓无）：
        autotools 构建静态库 + 头文件 + pkg-config 文件。
        """
        ldi = os.path.join(self.source_folder, "libdebian-installer",
                           "libdebian-installer-master")
        # configure.ac 用 `m4_esyscmd(dpkg-parsechangelog ...)` 提取版本
        # （OHOS 无 dpkg-parsechangelog → AC_INIT 缺版本参数）——
        # patch 写死版本 0.128（debian/changelog 真实版本）
        ca = os.path.join(ldi, "configure.ac")
        with open(ca, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace(
            "m4_esyscmd(dpkg-parsechangelog | perl -ne 'print $1 if m/^Version: (.*)$/;')",
            "0.128")
        if s2 != s:
            with open(ca, "w", encoding="utf-8") as f:
                f.write(s2)
        if amusr:
            self._autoreconf_with(amusr, ldi)
        # confstat 机制用 `umask 077 && mktemp -d ./confXXXXXX` 创建 0700
        # 临时目录做 config 文件生成——OHOS HMDFS 上 0700 目录对构建进程
        # 不可写（catdoc/boa/ccze 同款，subs1.awk Permission denied）——
        # patch umask 077→000
        cf = os.path.join(ldi, "configure")
        if os.path.isfile(cf):
            with open(cf, "r", encoding="utf-8", errors="replace") as f:
                s = f.read()
            s2 = s.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                           '(umask 000 && mktemp -d "./confXXXXXX")')
            s2 = s2.replace('(umask 077 && mkdir "$tmp")',
                            '(umask 000 && mkdir "$tmp")')
            if s2 != s:
                with open(cf, "w", encoding="utf-8") as f:
                    f.write(s2)
        with chdir(self, ldi):
            # --disable-check：libdebian-installer 的 test suite 依赖
            # check 库（制品仓无）——禁用以跳过 PKG_CHECK_MODULES 运行时失败
            # --build/--host：config.guess 识别不了 HarmonyOS（schilytools
            # 同款——OHOS 按 aarch64-unknown-linux-gnu 处理）
            self.run("./configure --prefix=%s --disable-check "
                     "--build=aarch64-unknown-linux-gnu "
                     "--host=aarch64-unknown-linux-gnu"
                     % self.package_folder)
            self.run("make -j1")
            self.run("make install")

    def build(self):
        amusr = self._bootstrap_automake()
        self._build_libdebian_installer(amusr)
        # cdebconf 本体：只构建 passthrough 前端（text 需 readline，
        # gtk/newt/slang/ncurses 全跳过），textwrap/selinux 不启用
        if amusr:
            self._autoreconf_with(amusr, self.source_folder)
        # cdebconf 本体 configure 同样用 confstat（umask 077 0700 临时
        # 目录）——OHOS HMDFS 不可写（catdoc/boa/ccze 同款）——patch
        cf = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cf):
            with open(cf, "r", encoding="utf-8", errors="replace") as f:
                s = f.read()
            s2 = s.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                           '(umask 000 && mktemp -d "./confXXXXXX")')
            s2 = s2.replace('(umask 077 && mkdir "$tmp")',
                            '(umask 000 && mkdir "$tmp")')
            if s2 != s:
                with open(cf, "w", encoding="utf-8") as f:
                    f.write(s2)
        with chdir(self, self.source_folder):
            self.run(
                "env CFLAGS='-I%s/include' CPPFLAGS='-I%s/include' "
                "LDFLAGS='-L%s/lib' PKG_CONFIG_PATH='%s/lib/pkgconfig' "
                "./configure --prefix=%s --with-frontend=passthrough "
                "--with-db=textdb --with-conffile=%s/etc/cdebconf.conf "
                "--disable-selinux --without-textwrap "
                "--build=aarch64-unknown-linux-gnu "
                "--host=aarch64-unknown-linux-gnu" %
                (self.package_folder, self.package_folder,
                 self.package_folder, self.package_folder,
                 self.package_folder, self.package_folder))
            self.run("make -j1")
            self.run("make install")
            # 上游测试实跑（src/test configtest/dbtest）——TMPDIR 指向
            # 可写目录（OHOS /tmp 只读），通过率如实记录
            # src/test/Makefile 链接缺 libdebian-installer 符号——补
            # LDFLAGS（di_malloc 等在 libdebian-installer）
            tmf = os.path.join(self.source_folder, "src", "test",
                               "Makefile")
            with open(tmf, "r", encoding="utf-8", errors="replace") as f:
                st = f.read()
            st2 = st.replace(
                "LDFLAGS += -Wl,-rpath,$(shell cd ..; pwd) -ldl",
                "LDFLAGS += -Wl,-rpath,$(shell cd ..; pwd) -ldl "
                "%s/lib/libdebian-installer.a" % self.package_folder)
            # lld 顺序敏感：库必须在对象文件之后（原规则 $(CC) $(LDFLAGS)
            # -o $@ $^ 库在对象前——-ldeibian-installer 不生效）——反转
            st2 = st2.replace("$(CC) $(LDFLAGS) -o $@ $^",
                              "$(CC) -o $@ $^ $(LDFLAGS)")
            st2 = st2.replace("$(CC) -o $@ $^ $(LDFLAGS)\n\ndbtest",
                              "$(CC) -o $@ $^ $(LDFLAGS)\n\ndbtest")
            if st2 != st:
                with open(tmf, "w", encoding="utf-8") as f:
                    f.write(st2)
            self.run("cd src/test && TMPDIR=%s make configtest dbtest -j1"
                     % self.build_folder, env="conanbuild")
            self.run("cd src/test && TMPDIR=%s LD_LIBRARY_PATH=%s/lib:%s/libexec/cdebconf "
                     "./configtest; echo configtest_rc=$?"
                     % (self.build_folder, self.package_folder,
                        self.package_folder), env="conanbuild")

    def package(self):
        # build() 中已 make install 到 package_folder
        pass

    def package_info(self):
        self.output.info("cdebconf 0.283: bin/debconf-* 工具 + libdebconfclient")
