#!/usr/bin/env python3
"""Conan test_package — leaflet-markercluster 1.5.3-dfsg

L1 smoke test: verify the packaged dist assets (js/css/sourcemap in
share/leaflet-markercluster, MIT licence + README in licenses/).
Asset package has no compiled binary — verification = presence + content
anchors + sha256 integrity (test.sh), plus python-side existence checks.
"""
import os
import shutil

from conan import ConanFile


class LeafletMarkerclusterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # 同主配方：OHOS settings.yml 为 OHOS 定义 version 子设置且无默认值，
        # 未声明 os.version 时 test_package 自身 package_id 校验同样报
        # "Invalid: 'settings.os.version' value not defined"（知识库
        # DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe），rm_safe 移除之。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["leaflet-markercluster"].package_folder

        # L0d: 真跑一个真实测试程序（test.sh，16 条核心断言 + 可选 node --check）
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{script}" "{pkg_folder}"', env="conanrun")

        # python 侧兜底存在性检查
        d = os.path.join(pkg_folder, "share", "leaflet-markercluster")
        for f in ("leaflet.markercluster.js", "leaflet.markercluster-src.js",
                  "MarkerCluster.css", "MarkerCluster.Default.css"):
            p = os.path.join(d, f)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise AssertionError(f"Missing/empty dist asset: {p}")
            self.output.info(f"  [ok] {f}")
        lic = os.path.join(pkg_folder, "licenses", "MIT-LICENCE.txt")
        if not os.path.isfile(lic):
            raise AssertionError(f"Missing licence: {lic}")
        self.output.info("  [ok] MIT-LICENCE.txt")
