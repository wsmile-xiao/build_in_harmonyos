#!/usr/bin/env python3
"""Conan recipe for acf-tinydns 0.11.1 (Alpine ACF Lua web admin module).

Pure Lua/LSP script package — no compilation. Installs the tinydns ACF app
module (controllers/model/html templates/roles/menu) into share/acf/app/tinydns
(mirrors upstream Makefile install: cp -a tinydns* → appdir/tinydns).

Upstream: https://gitlab.alpinelinux.org/acf/acf-tinydns
ACF framework: Alpine Configuration Framework (web-based system administration).
"""
import os
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfTinydnsConan(ConanFile):
    name = "acf-tinydns"
    version = "0.11.1"
    description = "Web-based system administration interface for tinydns (ACF module)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-tinydns"
    url = ""
    package_type = "application"

    # L0p gate: OHOS profile needs all four settings
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: os check must accept both Linux and OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        # ACF app module layout: $(datadir)/acf/app/tinydns
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "tinydns")
        os.makedirs(appdir, exist_ok=True)

        # APP_DIST from upstream Makefile: tinydns*
        # The tarball contains a dangling symlink tinydns-editfile-html.lsp
        # → ../filedetails-html.lsp (target provided by acf-core framework).
        # conan copy skips symlinks by default, so we use python per-file copy:
        # regular files via copy2, symlinks rebuilt with os.symlink.
        for name in sorted(os.listdir(self.source_folder)):
            if not name.startswith("tinydns"):
                continue
            src = os.path.join(self.source_folder, name)
            dst = os.path.join(appdir, name)
            if os.path.islink(src):
                target = os.readlink(src)
                if not os.path.lexists(dst):
                    os.symlink(target, dst)
            elif os.path.isfile(src):
                _shutil.copy2(src, dst)

        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/acf"]
