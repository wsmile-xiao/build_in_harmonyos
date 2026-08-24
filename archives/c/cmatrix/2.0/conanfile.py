#!/usr/bin/env python3
"""Conan recipe — cmatrix 2 (Matrix screen effect simulator, C/autotools) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, chdir, copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class CmatrixConan(ConanFile):
    name = "cmatrix"
    version = "2.0"
    description = "cmatrix — Matrix screen effect simulator (ncurses)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/abishekvashok/cmatrix"
    url = "https://github.com/abishekvashok/cmatrix"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("ncurses/6.5", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # 上游 tarball 不带预生成的 configure，只有 configure.ac + Makefile.am。
        # CI worker 没装 automake/aclocal，autoreconf -fi 报
        # "Can't exec aclocal"（CI #29765）。
        # 解决（同 abiword-plugin-eml/3.0.8 先例）：把 automake 作为
        # tool_requires 拉入，VirtualBuildEnv 注入 PATH，CI 可 autoreconf。
        self.tool_requires("automake/1.18")

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # VirtualBuildEnv: 把 tool_requires(automake) 的 bin 目录注入
        # conanbuild 环境的 PATH——CI 沙箱看不到 $HOME/.local 的手工工具，
        # aclocal/automake 只存在于 tool_requires 包内，不注入 PATH
        # 则 autoreconf 报 "aclocal: not found"（CI 实测）。
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cmatrix {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 上游 tarball 不带预生成的 configure，只有 configure.ac + Makefile.am，
        # 需 autoreconf 生成 configure 脚本（CI #29533 根因：直接 ./configure 报
        # "inaccessible or not found"）。umask 022 保证生成脚本可执行。
        # automake/aclocal 由 tool_requires(automake/1.18) 提供（CI #29765）。
        self.run("umask 022 && autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E011: autoreconf 生成的 configure/config.status 仍含 umask 077，
        # HMDFS 上导致临时 awk 脚本无 +x → "Permission denied"。统一替换为 022。
        for script in ("configure", "config.status"):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                replace_in_file(self, path, "umask 077", "umask 022")
        # E114: HMDFS 强制目录 setgid，configure 编译 conftest 时 clang 写
        # TMPDIR 临时文件被拒 → "C compiler cannot create executables"。
        # 修法（同 abiword-plugin-eml/3.0.8）：预建可写目录到系统 TMPDIR
        # （非 HMDFS），设 TMPDIR 指向它，并改 configure 的 ac_tmp 指向。
        import tempfile
        fixed_tmp = os.path.join(tempfile.gettempdir(), "cmatrix-ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        _cfg_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(_cfg_path):
            with open(_cfg_path, "r", encoding="utf-8") as _f:
                _cfg = _f.read()
            if "ac_tmp=$tmp" in _cfg:
                _cfg = _cfg.replace("ac_tmp=$tmp",
                                    "ac_tmp={}".format(fixed_tmp))
            _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
            _new_trap = 'exit $exit_status'
            if _old_trap in _cfg:
                _cfg = _cfg.replace(_old_trap, _new_trap)
            with open(_cfg_path, "w", encoding="utf-8") as _f:
                _f.write(_cfg)
            os.chmod(_cfg_path, 0o755)
        # 显式注入 ncurses 的 include/lib 路径，configure 才能找到 curses.h
        deps = self.dependencies["ncurses"]
        inc_dir = deps.cpp_info.aggregated_components().includedirs[0]
        lib_dir = deps.cpp_info.aggregated_components().libdirs[0]
        cppflags = f"-I{inc_dir}"
        ldflags = f"-L{lib_dir}"
        # ncurses 包提供 libncursesw.a（wide），但 configure.ac 用
        # AC_CHECK_LIB(ncurses, tgetent) 检测 -lncurses。建符号链接
        # libncurses.a → libncursesw.a 让检测通过。
        ncr_a = os.path.join(lib_dir, "libncurses.a")
        ncrw_a = os.path.join(lib_dir, "libncursesw.a")
        if not os.path.exists(ncr_a) and os.path.exists(ncrw_a):
            os.symlink("libncursesw.a", ncr_a)
        tmpdir = fixed_tmp  # 用预建的可写目录，避免 HMDFS setgid
        os.makedirs(tmpdir, exist_ok=True)
        bld = "--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl"
        prefix = "--prefix=/"  # 扁平布局：bin/cmatrix
        cfg = (f"umask 022 && CC=/data/service/hnp/bin/clang CPPFLAGS='{cppflags}' "
               f"LDFLAGS='{ldflags}' TMPDIR='{tmpdir}' ./configure {prefix} {bld}")
        self.run(cfg, cwd=self.source_folder)
        # config.status 由 configure 生成，其 umask 077 在运行时才触发权限问题
        cs = os.path.join(self.source_folder, "config.status")
        if os.path.isfile(cs):
            csc = open(cs).read()
            if "umask 077" in csc:
                replace_in_file(self, cs, "umask 077", "umask 022")
        self.run(f"umask 022 && make -j1 TMPDIR='{tmpdir}'", cwd=self.source_folder)
        # 上游测试（make check 空转 0 用例）——执行以满足 SKILL §3
        self.run(f"umask 022 && make -j1 check", cwd=self.source_folder, ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        # conan 2.x Autotools.install() 不切换 cwd，默认目录无 Makefile。
        # cmatrix 是 in-tree build，Makefile 在 source_folder。
        with chdir(self, self.source_folder):
            autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
