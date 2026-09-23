#!/usr/bin/env python3
"""Conan recipe — libgtop-tools 2.41.3 (Autotools).

Split package (same model as util-linux-login): builds ONLY the
command-line tools shipped with libgtop — libgtop_daemon2 (gnuserv
daemon) and libgtop_server2 (suid server helper) — from the libgtop
source tree. The library itself is delivered by the separate
libgtop/2.41.3 package.

Adapted to HarmonyOS PC (aarch64). See notes.md for platform adaptations.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgtopToolsConan(ConanFile):
    name = "libgtop-tools"
    version = "2.41.3"
    description = "GTop command-line tools — libgtop_daemon2 (monitoring daemon) and libgtop_server2 (suid server helper)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgtop"
    url = "https://gitlab.gnome.org/GNOME/libgtop"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _TOOLS = ("libgtop_daemon2", "libgtop_server2")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgtop-tools is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # The daemon links glib dynamically (configure.ac: glib-2.0 >= 2.6.0,
        # gobject-2.0 >= 2.26.0). The libgtop-2.0 library itself is built
        # in-tree (static) and is NOT part of this package — it is delivered
        # by the separate libgtop package.
        self.requires("glib/2.84.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps emits glib-2.0.pc / gobject-2.0.pc for configure's
        # PKG_CHECK_MODULES. AutotoolsToolchain does not inject PKG_CONFIG_PATH
        # automatically, so point configure at the generators folder explicitly.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # OHOS libc 无 libintl；glib 的 gi18n-lib.h 会把 ngettext 宏映射为
        # g_libintl_ngettext 符号，禁用 NLS 后走 gettext fallback 不再引用。
        tc.configure_args.append("--disable-nls")
        _gens = self.generators_folder
        if _gens:
            tc.configure_args.append("PKG_CONFIG_PATH={}".format(_gens))
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # CI 环境无 texinfo（makeinfo 缺失），doc/ 的 libgtop2.info 生成依赖
        # MAKEINFO；注入 MAKEINFO=true 让 configure 不再回退 missing 脚本。
        tc.configure_args.append("MAKEINFO=true")
        # E232 同类：config.status 引导自动依赖跟踪片段时会经 make 直接 exec
        # 源码树里的 install-sh（HMDFS 上 Permission denied, Error 126）。
        # 拆分包一次性构建不需要依赖跟踪；同时把 MKDIR_P 指向 mkdir -p，
        # 避免 make install 阶段的 $(MKDIR_P) 直连 exec install-sh。
        tc.configure_args.append("--disable-dependency-tracking")
        tc.configure_args.append("MKDIR_P=mkdir -p")
        # 树内 libgtop-2.0 库只编静态库：daemon/server 静态链接它，交付的二进制
        # 不再依赖 libgtop-2.0.so.11（动态 .so 由 libgtop 库包交付，本包不重复）。
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        # glib 包的 libintl.h 把 ngettext 宏映射为 g_libintl_ngettext，该符号由
        # glib 包内自带 libintl.so（proxy-libintl）提供，需显式链接 -lintl，
        # 否则 src/daemon 链接报 undefined symbol: g_libintl_ngettext。
        # 用 configure_args 传 LDFLAGS（写入 Makefile 链接行）。
        # LDFLAGS 带 -lintl 后 configure conftest 也链接 libintl.so.8，而该库在
        # glib 包私有 libdir，运行时不会被默认搜索路径找到，加 -Wl,-rpath 让
        # conftest 与 daemon 运行时都能定位 libintl.so.8。
        if "glib" in self.dependencies:
            _dep = self.dependencies["glib"]
            _pf = getattr(_dep, "package_folder", None) or ""
            for _l in _dep.cpp_info.libdirs:
                _libdir = _l if os.path.isabs(_l) else os.path.join(_pf, _l)
                if os.path.isdir(_libdir) and os.path.exists(os.path.join(_libdir, "libintl.so")):
                    tc.configure_args.append(
                        "LDFLAGS=-L{} -lintl -Wl,-rpath,{}".format(_libdir, _libdir))
                    break
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: HarmonyOS PC 上源码拷贝路径（HMDFS）可能丢失 autotools 辅助
        # 脚本的可执行位 → configure 报 Permission denied (Error 126)。
        for _fname in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "compile", "depcomp", "ltconfig", "ltmain.sh"):
            _fpath = os.path.join(self.source_folder, _fname)
            if os.path.isfile(_fpath):
                os.chmod(_fpath, 0o755)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            # E232: OHOS 执行器无法直接 exec HMDFS 上的 configure 脚本
            # （/system/bin/sh: ...configure: Permission denied, Error 126）。
            # CONFIG_SHELL 只影响 configure 内部派生的 shell，首个进程必须用
            # /system/bin/sh 显式前缀执行。
            _configure = os.path.join(self.source_folder, "configure")
            _cmd = ("CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                    + shlex.join(["/system/bin/sh", _configure]))
            if autotools._configure_args:
                _cmd = "{} {}".format(_cmd, autotools._configure_args)
            self.run(_cmd, cwd=self.build_folder)
        else:
            autotools.configure()
        # OHOS 实测：conan self.run() 输出流继承会导致编译器/失败信息静默
        # （make: *** Error 1 但日志无任何 error 行，同目录手工跑 100% 成功）。
        # 每步输出绑定日志文件（E524 配方族通用解法）。
        _make_log = os.path.join(self.build_folder, "make.log")
        self.run("make -j1 > {} 2>&1 || (tail -50 {}; exit 1)".format(_make_log, _make_log),
                 cwd=self.build_folder)

    def package(self):
        # 输出绑定日志文件（同 build()：规避 self.run 输出流静默失败）。
        # conan v2 布局是 prefix=/ + DESTDIR=<package_folder>，裸 make install
        # 会尝试写 //include 等（Permission denied），必须显式带 DESTDIR。
        _install_log = os.path.join(self.build_folder, "install.log")
        _destdir = shlex.quote(self.package_folder)
        self.run("make install DESTDIR={} > {} 2>&1 || (tail -50 {}; exit 1)".format(
            _destdir, _install_log, _install_log),
            cwd=self.build_folder)
        # This is a tools-only split package: keep the two daemon binaries
        # (upstream installs them into libexecdir) and drop everything else
        # (the library/headers/pc files belong to the libgtop package).
        pkg = self.package_folder
        bindir = os.path.join(pkg, "bin")
        for root, _dirs, files in os.walk(pkg):
            for fname in files:
                if fname in self._TOOLS:
                    src = os.path.join(root, fname)
                    dst = os.path.join(bindir, fname)
                    if src != dst:
                        os.makedirs(bindir, exist_ok=True)
                        shutil.move(src, dst)
        for entry in os.listdir(pkg):
            if entry == "bin":
                continue
            full = os.path.join(pkg, entry)
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
