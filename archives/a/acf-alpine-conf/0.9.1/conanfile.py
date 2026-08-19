#!/usr/bin/env python3
"""Conan recipe for acf-alpine-conf 0.9.1.

acf-alpine-conf is an Alpine Configuration Framework application module for
the lbu (local backup utility) tool. It is a pure Lua/LSP resource package,
so packaging mirrors the upstream Makefile install rule: copy lbu* into
share/acf/app/alpine-conf.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfAlpineConfConan(ConanFile):
    name = "acf-alpine-conf"
    version = "0.9.1"
    description = "Alpine ACF web administration module for lbu (alpine-conf)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-alpine-conf"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, filename="acf-alpine-conf-0.9.1.tar.gz")

    def build(self):
        pass

    def package(self):
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "alpine-conf")
        os.makedirs(appdir, exist_ok=True)

        for name in sorted(os.listdir(self.source_folder)):
            if not name.startswith("lbu"):
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

        copy(
            self,
            "Makefile",
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
