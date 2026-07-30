#!/usr/bin/env python3
"""Conan recipe — libtool 2.5.4 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class LibtoolConan(ConanFile):
    name = "libtool"
    version = "2.5.4"
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
        self._make_libtoolize_relocatable()

    def _make_libtoolize_relocatable(self):
        """libtoolize 也把 @datadir@ 烤死了（报 `$pkgauxdir is not a directory: '//share/libtool/build-aux'`）。

        它**没有**对应的命令行选项，但认环境变量 `_lt_pkgdatadir`（见上游 libtoolize.in：
        设了就从它派生 pkgauxdir=$_lt_pkgdatadir/build-aux、
        pkgltdldir=$_lt_pkgdatadir/libltdl、aclocaldir=$_lt_pkgdatadir/m4）。

        注意那三个子目录名是**源码树布局**，与 install 出来的布局不同
        （安装后 m4 宏在 share/aclocal）。所以这里在包内造一份「源码树形状」的目录，
        用软链指向真实位置，再让 package_info 把 _lt_pkgdatadir 指过来。
        软链是相对的，整包搬走依然有效。
        """
        import os
        share = os.path.join(self.package_folder, "share")
        want = os.path.join(share, "libtool-conan")
        os.makedirs(want, exist_ok=True)
        # 真实位置在设备上才确定，这里按候选逐个探
        cand = {
            "build-aux": [os.path.join(share, "libtool", "build-aux"),
                          os.path.join(share, "libtool")],
            "libltdl":   [os.path.join(share, "libtool", "libltdl")],
            "m4":        [os.path.join(share, "aclocal")],
        }
        for sub, paths in cand.items():
            dst = os.path.join(want, sub)
            if os.path.lexists(dst):
                continue
            for src in paths:
                if os.path.isdir(src):
                    os.symlink(os.path.relpath(src, want), dst)
                    self.output.info("libtoolize 布局: %s -> %s" % (sub, src))
                    break
            else:
                self.output.warning("libtoolize 布局: 找不到 %s 的来源（候选 %s）" % (sub, paths))



    def package_info(self):
        self.cpp_info.libs = ["ltdl"]
        self.cpp_info.bindirs = ["bin"]
        # libtoolize 要能被 autoreconf 找到；libtool.m4 等宏要进 ACLOCAL_PATH，
        # 否则消费方 configure.ac 里的 LT_INIT / AC_PROG_LIBTOOL 会展开失败
        # （典型报错：`possibly undefined macro: LT_INIT`）。
        import os
        self.buildenv_info.append_path("ACLOCAL_PATH",
                                      os.path.join(self.package_folder, "share", "aclocal"))
        self.buildenv_info.define_path("LIBTOOLIZE",
                                      os.path.join(self.package_folder, "bin", "libtoolize"))
        # libtoolize 靠这个环境变量绕开烤死的 @datadir@（见 _make_libtoolize_relocatable）
        self.buildenv_info.define_path("_lt_pkgdatadir",
                                      os.path.join(self.package_folder, "share", "libtool-conan"))
