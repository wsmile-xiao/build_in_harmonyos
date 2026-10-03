#!/usr/bin/env python3
"""Conan recipe — furo 2024.8.30 (platform task ref; upstream release
2024.8.6) — the clean customisable Sphinx documentation theme.

furo's PyPI **sdist** would require a node/webpack toolchain (the theme's
CSS/JS is authored under ``src/`` and built at packaging time), which is not
available on the OHOS build hosts.  The official
``furo-2024.8.6-py3-none-any.whl`` is the upstream-built artifact of the very
same release and carries the finished theme: 80 files under ``furo/`` plus
``furo-2024.8.6.dist-info`` metadata — a pure-asset, pure-Python package.

The wheel contents therefore travel **inside the recipe** (``assets/``,
exported via export_sources): no download, no layout dependence, byte-level
verification in build() (data/source-package exemption pattern,
cf. pari-seadata-big / agnostic-lizard).  Provenance is pinned in
conandata.yml (url + sha256 of the official wheel).

Version note: the platform task ref is 2024.8.30; upstream has no such
release — 2024.8.6 is the actual release on the same 2024 timeline
(cf. libzippp 6.2 precedent).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class FuroConan(ConanFile):
    name = "furo"
    version = "2024.8.30"
    description = (
        "furo 2024.8.6 (task ref 2024.8.30) — clean customisable Sphinx "
        "documentation theme; official PyPI wheel contents shipped in-recipe, "
        "pure assets, no build"
    )
    license = "MIT"
    homepage = "https://github.com/pradyunsg/furo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    # Pure-asset package: no compiler touches any artifact at package time,
    # but the headers/assets are consumed by Python/Sphinx builds, so the
    # settings tuple is kept.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # The wheel contents (85 files) + the validator travel with the recipe.
        # dst=导出根+默认 keep_path=True:文件带 assets/ 前缀落
        # <export>/assets/furo/...,与 _assets_root 对齐。
        # 65993 教训:dst 再加 assets 会 assets/assets 双重嵌套;
        # 66103 教训:keep_path=False 是全摊平(只留文件名),不是去前缀。
        copy(self, "assets/*", src=self.recipe_folder,
             dst=self.export_sources_folder)
        copy(self, "verify_furo.py", src=os.path.join(self.recipe_folder, "test_package"),
             dst=os.path.join(self.export_sources_folder, "test_package"))

    def layout(self):
        basic_layout(self)

    @property
    def _assets_root(self):
        # export_sources_folder 在包阶段不可靠(66368 实测:build 过、
        # package 拷空致 site-packages 缺树):逐候选找含 furo/__init__.py
        # 的 assets 根。
        for base in (self.export_sources_folder, self.build_folder,
                     self.source_folder, self.recipe_folder):
            if base and os.path.isfile(
                    os.path.join(base, "assets", "furo", "__init__.py")):
                return os.path.join(base, "assets")
        return os.path.join(self.export_sources_folder, "assets")

    @property
    def _validator(self):
        return os.path.join(
            self.export_sources_folder,
            "test_package",
            "verify_furo.py",
        )

    def build(self):
        # Deterministic content validation in place of a build step: 85
        # pinned files (80 theme + 5 dist-info), exact inventory, byte level.
        # Runs against the exported assets — no layout dependence at all.
        self.run(
            f'"{sys.executable}" "{self._validator}" '
            f'--source-root "{self._assets_root}"'
        )

    def package(self):
        src = self._assets_root
        site = os.path.join(self.package_folder, "share", "python", "site-packages")
        # 66368 第二面:"furo/*" 模式 + dst=site/furo 的 copy 语义在该 CI
        # conan 上只装出 6 个文件,site-packages 没立起来(test() 报找不到
        # 是真的没有)。src 指进目录内部再整树拷:相对路径不含 furo/ 前缀,
        # dst 恰补一层,布局确定。
        copy(self, "*", src=os.path.join(src, "furo"),
             dst=os.path.join(site, "furo"), keep_path=True)
        copy(self, "*", src=os.path.join(src, "furo-2024.8.6.dist-info"),
             dst=os.path.join(site, "furo-2024.8.6.dist-info"), keep_path=True)
        # MIT license text lives inside dist-info; surface it as usual.
        copy(self, "LICENSE*", src=os.path.join(src, "furo-2024.8.6.dist-info"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = [os.path.join("share", "python", "site-packages")]

        site = os.path.join(
            self.package_folder, "share", "python", "site-packages"
        )
        # Sphinx discovers the theme via its entry points recorded in
        # dist-info; exporting the site-packages dir on PYTHONPATH makes that
        # machinery work for any consumer that drives Sphinx on the device.
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.define_path("FURO_THEME_DIR", os.path.join(site, "furo"))
        self.runenv_info.define_path("FURO_THEME_DIR", os.path.join(site, "furo"))
        self.conf_info.define("user.furo:theme_dir", os.path.join(site, "furo"))
