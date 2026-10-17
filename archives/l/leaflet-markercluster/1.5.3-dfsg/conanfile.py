#!/usr/bin/env python3
"""Conan recipe — leaflet-markercluster 1.5.3-dfsg（纯 JS 前端资产包，无编译）

版本口径（取证见 notes.md）：任务版本 1.5.3-dfsg = Debian leaflet-markercluster
1.5.3~dfsg 的平台归一化。上游 git 标签的 dist/ 不含预编译 JS
（WhereAreTheJavascriptFiles.txt 明示"JS 只在版本标签与 npm 发布"），Debian 也须
rollup+terser 现构建；目标环境无 node → 源码取 npm 官方发布包（dist/ 含 2 JS + 2 CSS +
sourcemap，与 Debian 构建产物同源），sha256 钉死。

消费方形态同 acf-jquery 先例：application 资产包，resdirs 指向
share/leaflet-markercluster/，无 lib/include/bin。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LeafletMarkerclusterConan(ConanFile):
    name = "leaflet-markercluster"
    version = "1.5.3-dfsg"
    description = "Leaflet.markercluster — marker clustering plugin for Leaflet"
    license = "MIT"
    homepage = "https://github.com/Leaflet/Leaflet.markercluster"
    package_type = "application"

    # CI L0p（#62054 实测）要求四项齐备：settings = "os", "compiler",
    # "build_type", "arch"；os.version 子设置由 configure() rm_safe 处理。
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS settings.yml 为 OHOS 定义了 version 子设置（无默认值），配方未声明
        # os.version 时 package_id 校验会报 "Invalid: 'settings.os.version' value
        # not defined"（知识库 DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe）：
        # 有该子设置才 rm_safe 移除，Windows 等无此子设置的平台不受影响。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

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
        # dist 4 件套 + sourcemap + 上游说明 → share/leaflet-markercluster/
        # （消费方 Web 应用按需拷贝到静态资源目录；README 与许可证进 licenses/）
        dst = os.path.join(self.package_folder, "share", "leaflet-markercluster")
        os.makedirs(dst, exist_ok=True)
        src = os.path.join(self.source_folder, "dist")
        for f in ("leaflet.markercluster.js", "leaflet.markercluster-src.js",
                  "MarkerCluster.css", "MarkerCluster.Default.css",
                  "leaflet.markercluster.js.map", "leaflet.markercluster-src.js.map",
                  "WhereAreTheJavascriptFiles.txt"):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        copy(self, "MIT-LICENCE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/leaflet-markercluster"]
