#!/usr/bin/env python3
"""Conan recipe for acf-gross 0.6.0.

acf-gross is an Alpine Configuration Framework application module.  It is a
pure Lua/LSP resource package, so packaging mirrors the upstream Makefile
install rule: copy gross* into share/acf/app/gross.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfGrossConan(ConanFile):
    name = "acf-gross"
    version = "0.6.0"
    description = "Alpine ACF web administration module for gross"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-gross"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "gross")
        os.makedirs(appdir, exist_ok=True)

        for name in sorted(os.listdir(self.source_folder)):
            if not name.startswith("gross"):
                continue
            src = os.path.join(self.source_folder, name)
            dst = os.path.join(appdir, name)
            if os.path.islink(src):
                target = os.readlink(src)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(target, dst)
                    except OSError:
                        with open(dst, "w", encoding="utf-8") as f:
                            f.write(target + "\n")
            elif os.path.isfile(src):
                shutil.copy2(src, dst)

        # conan.tools.files.get() may skip dangling symlinks from the GitLab
        # archive. Recreate the ACF shared template links declared by upstream.
        _ensure_link(os.path.join(appdir, "gross-expert-html.lsp"), "../expert-html.lsp")
        _ensure_link(os.path.join(appdir, "gross-logfile-html.lsp"), "../logfile-html.lsp")
        _ensure_link(os.path.join(appdir, "gross-status-html.lsp"), "../status-html.lsp")

        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/acf"]


def _ensure_link(path, target):
    if os.path.lexists(path):
        return
    try:
        os.symlink(target, path)
    except OSError:
        with open(path, "w", encoding="utf-8") as f:
            f.write(target + "\n")
