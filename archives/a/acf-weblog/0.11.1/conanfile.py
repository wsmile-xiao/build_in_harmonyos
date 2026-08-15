#!/usr/bin/env python3
"""Conan recipe for acf-weblog 0.11.1 (Alpine ACF Lua web admin module).

Pure Lua/LSP script package — no compilation. Installs the weblog ACF app
module (controllers/model/html templates/roles/menu) into share/acf/app/weblog,
the log-import cron script into etc/periodic/daily, and the png icons into
share/acf/www/skins/static (mirrors upstream Makefile install).

Upstream: https://gitlab.alpinelinux.org/acf/acf-weblog
ACF framework: Alpine Configuration Framework (web-based system administration).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfWeblogConan(ConanFile):
    name = "acf-weblog"
    version = "0.11.1"
    description = "Web-based system administration interface for web log (ACF module)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-weblog"
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
        # ACF app module layout: $(datadir)/acf/app/weblog
        appdir = os.path.join(self.package_folder, "share", "acf", "app", "weblog")
        os.makedirs(appdir, exist_ok=True)

        # APP_DIST from upstream Makefile: weblog-* + weblog.roles + weblog.menu
        # 上游 tarball 中 weblog-editfile-html.lsp 是指向 acf-core 共享模板
        # (../filedetails-html.lsp) 的悬空符号链接, conan copy 默认跳过符号链接
        # → 改用 python 逐文件复制: 普通文件 copy2, 符号链接重建 (os.symlink)。
        import shutil as _shutil
        for name in sorted(os.listdir(self.source_folder)):
            if not (name.startswith("weblog") or name in ("weblog.roles", "weblog.menu")):
                continue
            src = os.path.join(self.source_folder, name)
            dst = os.path.join(appdir, name)
            if os.path.islink(src):
                target = os.readlink(src)
                if not os.path.lexists(dst):
                    os.symlink(target, dst)
            elif os.path.isfile(src):
                _shutil.copy2(src, dst)

        # CRON_FILE=weblogimport → /etc/periodic/daily (upstream install)
        cron_file = os.path.join(self.source_folder, "weblogimport")
        if os.path.isfile(cron_file):
            cron_dir = os.path.join(self.package_folder, "etc", "periodic", "daily")
            os.makedirs(cron_dir, exist_ok=True)
            _shutil.copy2(cron_file, os.path.join(cron_dir, "weblogimport"))
            os.chmod(os.path.join(cron_dir, "weblogimport"), 0o755)

        # IMAGE_DIST: bypass.png/denied.png/dodgy.png → share/acf/www/skins/static
        static_dir = os.path.join(self.package_folder, "share", "acf", "www", "skins", "static")
        for img in ("bypass.png", "denied.png", "dodgy.png"):
            src = os.path.join(self.source_folder, img)
            if os.path.isfile(src):
                os.makedirs(static_dir, exist_ok=True)
                _shutil.copy2(src, os.path.join(static_dir, img))

        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/acf"]
