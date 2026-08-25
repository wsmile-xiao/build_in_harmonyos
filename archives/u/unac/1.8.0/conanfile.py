#!/usr/bin/env python3
"""Conan recipe — unac 1.8.0 (autotools)"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnacConan(ConanFile):
    name = "unac"
    version = "1.8.0"
    description = "C library and tool for removing accents from characters"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/libunac/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # CI worker 有 autoconf 但无 automake/aclocal → tool_requires 补齐
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess 不认 uname -s=HarmonyOS → 显式三元组跳过
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS conftest 写 dummy.c 报 Permission denied → 指到稳定可写目录
        _tmp = os.path.join(os.path.expanduser("~"), ".conan_build_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # orig.tar.gz 不含预生成 configure，需 autoreconf 生成
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            # config.rpath 由 gettext 提供，autoreconf 需要
            config_rpath_candidates = [
                "/data/service/hnp/gettext.org/gettext_0.26/share/gettext/config.rpath",
                "/usr/local/share/gettext/config.rpath",
                "/usr/share/gettext/config.rpath",
            ]
            for cr in config_rpath_candidates:
                if os.path.isfile(cr) and not os.path.isfile(os.path.join(self.source_folder, "config.rpath")):
                    shutil.copy(cr, os.path.join(self.source_folder, "config.rpath"))
                    break
            # autoreconf 生成 configure 等；ACLOCAL_PATH 在 shell 中设置
            # (Conan 环境已激活, libtoolize/automake 的 bin/ 在 PATH 中)
            # 优先找到 tool_requires 安装的 libtool.m4 (2.5.4)，避免与
            # 系统残留 libtool.m4 (2.4.7) 产生版本不匹配。
            # autoreconf 后重新 aclocal+autoconf 修复版本不匹配：
            # autoreconf 的 aclocal 可能找到系统旧版 libtool.m4 (2.4.7)，
            # 导致与 ./libtool (2.5.4 from libtoolize) 版本冲突，
            # 用已设置的 ACLOCAL_PATH 重新 aclocal + autoconf 修复。
            self.run(
                'LT_BIN=$(which libtoolize 2>/dev/null) && '
                'LT_ROOT=$(dirname $(dirname "$LT_BIN")) && '
                'LT_M4_DIR=$(find "$LT_ROOT" -name "libtool.m4" 2>/dev/null | head -1 | xargs dirname 2>/dev/null) && '
                'GT_M4="/data/service/hnp/gettext.org/gettext_0.26/share/gettext/m4" && '
                'if [ -n "$LT_M4_DIR" ]; then export ACLOCAL_PATH="$LT_M4_DIR:$GT_M4:${ACLOCAL_PATH}"; '
                'elif [ -d "$GT_M4" ]; then export ACLOCAL_PATH="$GT_M4:${ACLOCAL_PATH}"; fi && '
                'autoreconf --install --force && '
                'aclocal --force && autoconf --force && autoheader --force',
                cwd=self.source_folder
            )
        # 修复 configure 中 umask 077 → 022（HMDFS 权限问题）
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        # builder Perl 脚本用 $ENV{'srcdir'} 定位 unaccent-local-map.perl
        os.environ["srcdir"] = self.source_folder
        # builder 脚本 slurp("unac.c") 直接从 CWD 读取，out-of-tree 时需复制
        for _f in ("unac.c", "unac.h"):
            _src = os.path.join(self.source_folder, _f)
            _dst = os.path.join(self.build_folder, _f)
            if os.path.isfile(_src) and not os.path.exists(_dst):
                shutil.copy(_src, _dst)
        # -j1 避免 HMDFS 软链接创建延迟导致链接失败
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # HELP2MAN=/bin/true: 鸿蒙无 help2man，跳过 manpage 生成
        autotools.install(args=["HELP2MAN=/bin/true"])

    def package_info(self):
        self.cpp_info.libs = ["unac"]
        self.cpp_info.bindirs = ["bin"]
