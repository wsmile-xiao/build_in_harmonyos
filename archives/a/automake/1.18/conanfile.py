#!/usr/bin/env python3
"""Conan recipe — automake 1.18 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class AutomakeConan(ConanFile):
    name = "automake"
    version = "1.18"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball（ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改（改的是不存在的文件，
        # 或改完又被覆盖）。
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])
        self._make_relocatable()

    def _make_relocatable(self):
        """让 aclocal 的宏目录跟着包走，而不是烤死在脚本里。

        automake 在 configure 期把 `@datadir@` 烤进 aclocal，且**没有对应的环境变量**
        可以覆盖（只有 --automake-acdir / --system-acdir 两个命令行选项，
        见上游 bin/aclocal.in 的 @automake_includes / @system_includes）。
        conan 用 --prefix=/ + DESTDIR 安装，于是脚本里是 `//share/aclocal-1.18`，
        一跑就报 `couldn't open directory '//share/aclocal-1.18'`。

        两条路：
          ① configure 时给 --prefix=<package_folder> —— 会把**本机 conan cache 路径**
             烤进脚本，换机器/换 cache 哈希即废，与 SONAME 烤路径同一个病，不取。
          ② 装一层包装脚本，运行时从 $0 推算前缀 —— 可重定位，取这条。
        """
        import os
        import stat
        bindir = os.path.join(self.package_folder, "bin")
        api = "1.18"
        # 两组工具都烤了 @datadir@，但覆盖方式不同：
        #   aclocal  → 只有 --automake-acdir / --system-acdir 两个命令行选项
        #   automake → 有 --libdir 命令行选项（见上游 bin/automake.in 的 'libdir=s'）
        # 都没有环境变量，故一律包装。第一轮只包了 aclocal，结果 automake 本体照样报
        #   automake: cannot open < //share/automake-1.18/am/header-vars.am
        for name in ("automake", "automake-" + api):
            real = os.path.join(bindir, name)
            if not os.path.isfile(real):
                continue
            hidden = os.path.join(bindir, "." + name + "-real")
            os.replace(real, hidden)
            with open(real, "w", encoding="utf-8") as f:
                f.write(
                    "#!/bin/sh\n"
                    "# conan 包装：从自身位置推算 libdir，使包可重定位。\n"
                    'here=$(cd "$(dirname "$0")" && pwd)\n'
                    'pfx=$(dirname "$here")\n'
                    'exec "$here/.%s-real" --libdir="$pfx/share/automake-%s" "$@"\n'
                    % (name, api))
            os.chmod(real, os.stat(real).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            self.output.info("已为 %s 装可重定位包装脚本" % name)

        for name in ("aclocal", "aclocal-" + api):
            real = os.path.join(bindir, name)
            if not os.path.isfile(real):
                continue
            hidden = os.path.join(bindir, "." + name + "-real")
            os.replace(real, hidden)
            with open(real, "w", encoding="utf-8") as f:
                f.write(
                    "#!/bin/sh\n"
                    "# conan 包装：从自身位置推算 datadir，使包可重定位。\n"
                    "# 原脚本在同目录下的 .%s-real。\n"
                    'here=$(cd "$(dirname "$0")" && pwd)\n'
                    'pfx=$(dirname "$here")\n'
                    'exec "$here/.%s-real" \\\n'
                    '  --automake-acdir="$pfx/share/aclocal-%s" \\\n'
                    '  --system-acdir="$pfx/share/aclocal" "$@"\n'
                    % (name, name, api))
            os.chmod(real, os.stat(real).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            self.output.info("已为 %s 装可重定位包装脚本" % name)



    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # 作为 tool_requires 被消费时，conan 会自动把 bindirs 挂上 PATH。
        # 但 aclocal 找宏靠 ACLOCAL_PATH，必须显式给，否则消费方
        # 的 configure.ac 用到 PKG_INSTALLDIR / LT_INIT 这类宏就找不到。
        import os
        self.buildenv_info.append_path("ACLOCAL_PATH",
                                      os.path.join(self.package_folder, "share", "aclocal"))
        self.buildenv_info.define_path("AUTOMAKE",
                                      os.path.join(self.package_folder, "bin", "automake"))
        self.buildenv_info.define_path("ACLOCAL",
                                      os.path.join(self.package_folder, "bin", "aclocal"))
        # automake 的 aclocal/automake 是 perl 脚本，安装时把 `$prefix/share/automake-1.18`
        # **烤进了脚本自身**。conan 用 --prefix=/ + DESTDIR 装，于是脚本里的
        # @INC 变成 `//share/automake-1.18`，一跑就报
        #   Can't locate Automake/Config.pm in @INC
        # 这与 SONAME 烤路径是同一家族的问题（安装产物里带死绝对前缀）。
        #
        # 修法选可重定位的那条：**不改脚本里的路径**（那会把 conan cache 路径烤死，
        # 换机器同样废），而是用 PERL5LIB 把真实位置补进 @INC。
        _pl = os.path.join(self.package_folder, "share", "automake-1.18")
        self.buildenv_info.append_path("PERL5LIB", _pl)
        # aclocal 找自带宏也靠这个目录的同级 aclocal-1.18
        self.buildenv_info.append_path("ACLOCAL_PATH",
                                      os.path.join(self.package_folder, "share", "aclocal-1.18"))
        # ── 把系统里其它软件装的 m4 宏也纳入搜索路径 ──
        # 我们的 aclocal 包装用 --system-acdir 指向本包的 share/aclocal，
        # 这会**替换**掉默认的系统宏目录，于是 hnp 里 pkg-config 自带的 pkg.m4 被挡在外面，
        # 消费方 configure.ac 里的 PKG_INSTALLDIR 展开失败，报
        #   Makefile.am:8: error: 'pkgconfig_DATA' is used but 'pkgconfigdir' is undefined
        # （musl-fts / musl-obstack 实测）。
        # 这里 glob 出 hnp 各包的 share/aclocal 追加进 ACLOCAL_PATH —— 自发现而非写死路径，
        # 与 _ohos_toolchain() 找 SDK 是同一手法。
        import glob
        for _d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            self.buildenv_info.append_path("ACLOCAL_PATH", _d)
