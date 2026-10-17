#!/usr/bin/env python3
"""Conan recipe — adarkroom 1.4+dfsg.1 (A Dark Room browser game).

Pure HTML/CSS/JS browser text-adventure game: no native compilation.
The recipe downloads the official Debian DFSG repack tarball
(adarkroom_1.4+dfsg.1.orig.tar.xz, SHA256 verified) and installs the
web assets under share/adarkroom/www/, mirroring the Debian package
layout (/usr/share/adarkroom/www/).

Upstream: https://github.com/doublespeakgames/adarkroom (tag 1.4)
Platform version 1.4+dfsg.1 is the Debian DFSG repack of upstream 1.4
(minified third-party libs and generated translation bundles removed).
"""
import os
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AdarkroomConan(ConanFile):
    name = "adarkroom"
    version = "1.4+dfsg.1"
    description = "A Dark Room - a minimalist text adventure game for your browser"
    license = "MPL-2.0"
    homepage = "https://github.com/doublespeakgames/adarkroom"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure browser game: nothing to compile.
        apply_conandata_patches(self)

    def package(self):
        www = os.path.join(self.package_folder, "share", "adarkroom", "www")
        os.makedirs(www, exist_ok=True)

        # 顶层网页入口文件
        for name in ("index.html", "browserWarning.html", "mobileWarning.html", "favicon.ico"):
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                _shutil.copy2(src, os.path.join(www, name))

        # 资源目录（对应 Debian install 清单）
        for sub in ("audio", "css", "img", "lang", "lib", "script"):
            src = os.path.join(self.source_folder, sub)
            dst = os.path.join(www, sub)
            if os.path.isdir(src):
                _shutil.copytree(src, dst, dirs_exist_ok=True)

        # 许可证与文档
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        docdir = os.path.join(self.package_folder, "share", "doc", "adarkroom")
        os.makedirs(docdir, exist_ok=True)
        for name in ("README.md", "contributing.md"):
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                _shutil.copy2(src, os.path.join(docdir, name))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/adarkroom"]
