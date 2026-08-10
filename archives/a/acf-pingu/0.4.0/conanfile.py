#!/usr/bin/env python3
"""Conan recipe for acf-pingu 0.4.0 (Alpine ACF Lua web admin module).

Pure Lua/LSP script package — no compilation. Installs the pingu ACF app
module (controllers/model/html templates/roles/menu) into share/acf/app/pingu.

Upstream: https://gitlab.alpinelinux.org/acf/acf-pingu
ACF framework: Alpine Configuration Framework (web-based system administration).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfPinguConan(ConanFile):
    name = "acf-pingu"
    version = "0.4.0"
    description = "Web-based system administration interface for pingu (ACF module)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-pingu"
    url = ""
    package_type = "application"

    settings = "os", "arch"

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
        # ACF app module layout: $(datadir)/acf/app/pingu
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "pingu")
        os.makedirs(appdir, exist_ok=True)

        # APP_DIST from upstream Makefile: pingu*
        # 上游 tarball 中 pingu-expert-html.lsp / pingu-status-html.lsp 是指向
        # acf-core 共享模板(expert-html.lsp/status-html.lsp)的悬空符号链接,
        # conan copy 默认跳过符号链接 → 改用 python 逐文件复制:
        # 普通文件 copy2,符号链接重建(os.symlink 保持相对目标)
        import shutil as _shutil
        for name in sorted(os.listdir(self.source_folder)):
            if not name.startswith("pingu"):
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
