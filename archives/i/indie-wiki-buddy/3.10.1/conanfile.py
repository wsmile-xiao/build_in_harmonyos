#!/usr/bin/env python3
"""indie-wiki-buddy 3.10.1 — Indie Wiki Buddy 浏览器扩展（MIT）。

上游是**浏览器扩展**：把 Fandom/wiki 链接导向独立百科。纯静态资源（JS/CSS/HTML/图片/多语言），
**无编译步骤、无运行期库依赖、无 npm 依赖**（包内没有 package.json）。

打包做法**照抄 Debian 的 debian/*.install 与 debian/rules**：
  * 同一份扩展内容按浏览器装两处（chromium、firefox 各一棵树）；
  * `manifest.json` 由**按浏览器挑选**的模板生成：
      cp manifest-chromium.json -> <chromium 树>/manifest.json   （manifest_version = 3）
      cp manifest-firefox.json  -> <firefox 树>/manifest.json    （manifest_version = 2，带 gecko id）
  * firefox 树沿用 Mozilla 的扩展 ID 目录（与 Debian 一致，便于对照）：
      {ec8030f7-c20a-464f-9b0e-13a3a9e97384}/{cb31ec5d-c49a-4e5a-b240-16c767444f62}

上游测试：扩展自身**无测试套件**（无 package.json / Makefile / test 目录）→ 上游通过率记 N/A
（如实披露）；验证由 test_package 承担（两棵树结构 + 两份 manifest 的关键字段 + 资源齐备性）。
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout

CONTENT_DIRS = ("_locales", "css", "data", "favicons", "images", "pages", "scripts")
CONTENT_FILES = ("background.js", "LICENSE", "README.md")
MANIFEST_SRC = {"chromium": "manifest-chromium.json", "firefox": "manifest-firefox.json"}
BROWSER_REL = {
    "chromium": "res/chromium/extensions/indie-wiki-buddy",
    "firefox": ("res/mozilla/extensions/{ec8030f7-c20a-464f-9b0e-13a3a9e97384}"
                "/{cb31ec5d-c49a-4e5a-b240-16c767444f62}"),
}


class IndieWikiBuddyConan(ConanFile):
    name = "indie-wiki-buddy"
    version = "3.10.1"
    description = ("Indie Wiki Buddy — browser extension that redirects Fandom/wiki links to "
                   "independent wikis (static web-extension, no dependencies)")
    license = "MIT"                    # 上游 LICENSE 首行 "MIT License"
    homepage = "https://github.com/KevinPayravi/indie-wiki-buddy"
    url = "https://github.com/KevinPayravi/indie-wiki-buddy"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        """无编译步骤（纯静态扩展）；仅自检模板与资源齐备。"""
        for browser, name in MANIFEST_SRC.items():
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration("缺少 manifest 模板：%s" % name)
            with open(path, errors="replace") as fh:
                data = json.load(fh)
            if data.get("version") != self.version:
                raise ConanInvalidConfiguration(
                    "%s 的 version=%s 与包版本 %s 不一致"
                    % (name, data.get("version"), self.version))
        missing = [d for d in CONTENT_DIRS
                   if not os.path.isdir(os.path.join(self.source_folder, d))]
        if missing:
            raise ConanInvalidConfiguration("缺少内容目录：%s" % ", ".join(missing))
        total = sum(len(files) for _r, _d, files in os.walk(self.source_folder))
        self.output.info("[build] 无需编译：静态扩展，%d 个文件；两份 manifest 版本均 %s"
                         % (total, self.version))

    def package(self):
        src = self.source_folder
        for browser, rel in BROWSER_REL.items():
            dest = os.path.join(self.package_folder, *rel.split("/"))
            os.makedirs(dest, exist_ok=True)
            for name in CONTENT_DIRS:
                shutil.copytree(os.path.join(src, name), os.path.join(dest, name),
                                dirs_exist_ok=True)
            for name in CONTENT_FILES:
                path = os.path.join(src, name)
                if os.path.isfile(path):
                    shutil.copyfile(path, os.path.join(dest, name))
            # 按浏览器挑选 manifest 模板生成 manifest.json（照抄 debian/rules）
            shutil.copyfile(os.path.join(src, MANIFEST_SRC[browser]),
                            os.path.join(dest, "manifest.json"))
            self.output.info("[package] %s 树 -> %s/" % (browser, rel))

    def package_info(self):
        # 纯数据包：内容在 res/ 下，按浏览器分两棵树
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
