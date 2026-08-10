#!/usr/bin/env python3
"""Conan recipe for acf-iproute2-qos 0.4.0 (Alpine ACF Lua web admin module).

Pure Lua/LSP script package — no compilation. Installs the qos ACF app
module (controllers/model/html templates/roles/menu) into share/acf/app/qos.

Upstream: https://gitlab.alpinelinux.org/acf/acf-iproute2-qos
ACF framework: Alpine Configuration Framework (web-based system administration).
"""
import os
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfIproute2QosConan(ConanFile):
    name = "acf-iproute2-qos"
    version = "0.4.0"
    description = "Web-based system administration interface for iproute2 qos (ACF module)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-iproute2-qos"
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
        # ACF app module layout: $(datadir)/acf/app/qos
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "qos")
        os.makedirs(appdir, exist_ok=True)

        # APP_DIST from upstream Makefile: qos*
        # 上游 tarball 中 qos-expert-html.lsp / qos-status-html.lsp 是指向
        # acf-core 共享模板(filedetails-html.lsp/status-html.lsp)的悬空符号链接,
        # conan copy 默认跳过符号链接 → 改用 python 逐文件复制:
        # 普通文件 copy2,符号链接重建(os.symlink 保持相对目标)
        for name in sorted(os.listdir(self.source_folder)):
            if not name.startswith("qos"):
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
