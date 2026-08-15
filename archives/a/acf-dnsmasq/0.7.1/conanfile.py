#!/usr/bin/env python3
"""Conan recipe for acf-dnsmasq 0.7.1 (Alpine ACF Lua web admin module).

Pure Lua/LSP script package — no compilation. Installs the dnsmasq ACF app
module (controllers/model/html templates/roles/menu) into share/acf/app/dnsmasq
(mirrors upstream Makefile install: cp -a dnsmasq* → appdir/dnsmasq).

Upstream: https://gitlab.alpinelinux.org/acf/acf-dnsmasq
ACF framework: Alpine Configuration Framework (web-based system administration).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfDnsmasqConan(ConanFile):
    name = "acf-dnsmasq"
    version = "0.7.1"
    description = "Web-based system administration interface for dnsmasq (ACF module)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-dnsmasq"
    url = ""
    package_type = "application"

    # L0p 门禁: OHOS profile 需要 settings 全四项(os/compiler/build_type/arch)
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
        # ACF app module layout: $(datadir)/acf/app/dnsmasq
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "dnsmasq")
        os.makedirs(appdir, exist_ok=True)

        # APP_DIST from upstream Makefile: dnsmasq*
        # 上游 tarball 中 dnsmasq-expert/logfile/status/viewleases-html.lsp 是指向
        # acf-core 共享模板(../expert-html.lsp 等)的悬空符号链接, conan copy 默认
        # 跳过符号链接 → 改用 python 逐文件复制: 普通文件 copy2, 符号链接重建。
        import shutil as _shutil
        for name in sorted(os.listdir(self.source_folder)):
            if not name.startswith("dnsmasq"):
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
