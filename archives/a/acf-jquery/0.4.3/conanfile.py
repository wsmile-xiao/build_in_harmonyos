#!/usr/bin/env python3
"""Conan recipe for acf-jquery 0.4.3 (Alpine ACF jquery addon package).

Static JS/CSS asset package — no compilation. Installs the jquery library
bundle (jquery-latest.js, jquery.flot.js, jquery.tablesorter.js, widgets/,
parsers/) into share/acf/app and the tablesorter theme assets into
share/acf/www/skins/static (upstream staticdir=$(wwwdir)/skins/static).

Upstream: https://gitlab.alpinelinux.org/acf/acf-jquery
ACF framework: Alpine Configuration Framework (web-based system administration).
"""
import os
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcfJqueryConan(ConanFile):
    name = "acf-jquery"
    version = "0.4.3"
    description = "jquery addon package for ACF (Alpine Configuration Framework)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-jquery"
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
        # APP_DIST: *.js + widgets/*.js + parsers/*.js -> $(appdir) (share/acf/app)
        # 上游 Makefile install 目标: cp "$$i" "$(install_dir)/$$i" 保持子目录
        appdir = os.path.join(self.package_folder, "share", "acf", "app")
        os.makedirs(appdir, exist_ok=True)

        for name in sorted(os.listdir(self.source_folder)):
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src) and name.endswith(".js"):
                _shutil.copy2(src, os.path.join(appdir, name))
            elif os.path.isdir(src) and name in ("widgets", "parsers"):
                _shutil.copytree(src, os.path.join(appdir, name), dirs_exist_ok=True)

        # STATIC_DIST: tablesorter/* -> $(staticdir) = $(wwwdir)/skins/static
        staticdir = os.path.join(self.package_folder, "share", "acf", "www", "skins", "static")
        os.makedirs(staticdir, exist_ok=True)
        _ts_src = os.path.join(self.source_folder, "tablesorter")
        if os.path.isdir(_ts_src):
            _shutil.copytree(_ts_src, os.path.join(staticdir, "tablesorter"),
                             dirs_exist_ok=True)

        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/acf"]
