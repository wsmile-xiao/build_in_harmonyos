#!/usr/bin/env python3
"""Conan recipe for acf-squid 0.11.0."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfSquidConan(ConanFile):
    name = "acf-squid"
    version = "0.11.0"
    description = "Alpine ACF web administration module for Squid"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-squid"
    url = ""

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
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "squid")
        os.makedirs(appdir, exist_ok=True)

        for name in sorted(os.listdir(self.source_folder)):
            if not name.startswith("squid"):
                continue
            _copy_or_link(os.path.join(self.source_folder, name), os.path.join(appdir, name))

        _ensure_link(os.path.join(appdir, "squid-editfile-html.lsp"), "../filedetails-html.lsp")
        _ensure_link(os.path.join(appdir, "squid-expert-html.lsp"), "../expert-html.lsp")
        _ensure_link(os.path.join(appdir, "squid-status-html.lsp"), "../status-html.lsp")

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
        self.cpp_info.resdirs = ["share/acf"]


def _copy_or_link(src, dst):
    if os.path.islink(src):
        _ensure_link(dst, os.readlink(src))
    elif os.path.isfile(src):
        shutil.copy2(src, dst)


def _ensure_link(path, target):
    if os.path.lexists(path):
        return
    try:
        os.symlink(target, path)
    except OSError:
        with open(path, "w", encoding="utf-8") as f:
            f.write(target + "\n")
