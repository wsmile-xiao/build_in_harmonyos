#!/usr/bin/env python3
"""Conan recipe for alacarte — GNOME menu editor (pure Python 3 + GTK3).

alacarte is a pure Python application (Alacarte/*.py + alacarte launcher).
It contains no C/C++ source; the upstream autotools build only glues
translations and installs the .py files. For the OHOS PC environment we
package it directly (no configure/make):

  * Alacarte/ Python package (with config.py generated from config.py.in)
      -> lib/python3.12/site-packages/Alacarte
  * alacarte launcher (generated from alacarte.in) -> bin/alacarte
  * runtime UI resources (data/*.ui + icons)       -> share/alacarte/

Runtime system deps (GTK3 / pygobject / libgnome-menu) are provided by the
target image, not by conan (pygobject & libgnome-menu are not in ohpcd).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class AlacarteConan(ConanFile):
    name = "alacarte"
    version = "3.58.0"
    description = "GNOME menu editor using the freedesktop.org menu specification"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/alacarte"
    url = "https://gitlab.gnome.org/GNOME/alacarte"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # 运行时依赖：GTK3（经 pygobject 供 dlopen）。pygobject 与
    # libgnome-menu-3.0 不在 ohpcd 制品仓，由目标镜像提供（见 notes.md）。
    requires = "gtk/3.24.38"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _gen_config_py(in_path, out_path, prefix):
        """Generate Alacarte/config.py from config.py.in (mirrors Makefile.am)."""
        subs = {
            "@prefix@": prefix,
            "@datadir@": os.path.join(prefix, "share"),
            "@pkgdatadir@": os.path.join(prefix, "share", "alacarte"),
            "@libexecdir@": os.path.join(prefix, "libexec"),
            "@libdir@": os.path.join(prefix, "lib"),
            "@PACKAGE@": "alacarte",
            "@VERSION@": "3.58.0",
            "@GETTEXT_PACKAGE@": "alacarte",
        }
        with open(in_path, encoding="utf-8") as f:
            content = f.read()
        for k, v in subs.items():
            content = content.replace(k, v)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _gen_launcher(in_path, out_path):
        """Generate bin/alacarte from alacarte.in (mirrors Makefile.am)."""
        with open(in_path, encoding="utf-8") as f:
            content = f.read()
        # Upstream substitutes an absolute python path; use env shebang for OHOS.
        content = content.replace("@PYTHON@", "/usr/bin/env python3")
        content = content.replace("@PYOPTIONS@", "")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(out_path, 0o755)

    def build(self):
        # Pure Python application — nothing to compile.
        pass

    def package(self):
        prefix = self.package_folder
        site = os.path.join(prefix, "lib", "python3.12", "site-packages")

        # 1. Python package with generated config.py
        src_pkg = os.path.join(self.source_folder, "Alacarte")
        dst_pkg = os.path.join(site, "Alacarte")
        shutil.copytree(
            src_pkg, dst_pkg,
            ignore=shutil.ignore_patterns("*.in", "__pycache__", "Makefile.am"))
        self._gen_config_py(
            os.path.join(src_pkg, "config.py.in"),
            os.path.join(dst_pkg, "config.py"),
            prefix)

        # 2. launcher -> bin/
        self._gen_launcher(
            os.path.join(self.source_folder, "alacarte.in"),
            os.path.join(prefix, "bin", "alacarte"))

        # 3. runtime UI resources -> share/alacarte/
        data_src = os.path.join(self.source_folder, "data")
        data_dst = os.path.join(prefix, "share", "alacarte")
        for name in ("alacarte.ui", "directory-editor.ui", "launcher-editor.ui"):
            s = os.path.join(data_src, name)
            if os.path.isfile(s):
                copy(self, name, data_src, data_dst)
        icons_src = os.path.join(data_src, "icons")
        if os.path.isdir(icons_src):
            copy(self, "*", icons_src, os.path.join(data_dst, "icons"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
