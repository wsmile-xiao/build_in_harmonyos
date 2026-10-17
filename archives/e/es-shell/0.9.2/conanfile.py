#!/usr/bin/env python3
"""Conan recipe — es-shell 0.9.2 (autotools CLI shell, HarmonyOS PC).

es is a C shell (es-shell).  Upstream tarball ships no pre-generated
`configure` (only configure.ac), so build() runs autoconf first.  It
links against readline for interactive line editing.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_build_aux(src, export_src):
    """Copy autotools aux files (install-sh/config.guess/config.sub) into src.

    The upstream tarball omits them; configure refuses to run without them.
    The OHOS-patched config.guess/config.sub (recognizing aarch64-unknown-
    linux-ohos) are vendored in patches/build-aux/.
    """
    aux_src = os.path.join(export_src, "patches", "build-aux")
    for name in ("install-sh", "config.guess", "config.sub"):
        dst = os.path.join(src, name)
        if not os.path.exists(dst):
            import shutil
            shutil.copy(os.path.join(aux_src, name), dst)
            os.chmod(dst, 0o755)


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir.  Same fix as abiword-plugin-clarisworks."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class EsshellConan(ConanFile):
    name = "es-shell"
    version = "0.9.2"
    description = "es — an extensible shell (es-shell)"
    license = "MIT"
    homepage = "https://github.com/wryun/es-shell"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # 把 patches/（含 build-aux/ 的 OHOS config.guess/config.sub）一并导出
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("readline/8.3")

    # 上游 tarball 无预生成 configure，build() 用系统 autoconf 重新生成
    # （/data/service/hnp/bin/autoconf，profile PATH 已含；与仓库 abiword
    #  系列配方一致——ohpcd 的 autoconf/2.72 tool_require 依赖损坏的 perl
    #  包会报 Perl_my_cxt_init 符号缺失，故不引入 tool_requires）

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"es-shell supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_build_aux(self.source_folder, self.export_sources_folder)
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        # The tarball ships no configure: bootstrap with autoconf.
        self.run("autoconf", cwd=self.source_folder, env="conanbuild")
        self.run("autoheader", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # 上游 Makefile install 规则引用 $(srcdir)/es，但 out-of-tree 构建下
        # es 位于 build folder，且并行 make 的 jobserver fifo 在 HMDFS 上
        # EPERM（E074）。手动拷贝产物规避这两点（es 二进制 + man page）。
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "es", src=self.build_folder, dst=bin_dir)
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "doc/es.1", src=self.source_folder, dst=man_dir)

    def package_info(self):
        # CLI tool: consumers do not link against it.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
