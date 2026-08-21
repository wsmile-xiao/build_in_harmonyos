#!/usr/bin/env python3
"""Conan recipe for xz 5.8.3 — general-purpose data compression library
(liblzma + xz CLI, C, autotools, tukaani source, zero deps).

Adaptation lessons applied:
- E007: config.guess cannot guess OHOS — pass --build/--host explicitly.
- E011: config.status temp-dir creation may hit Permission denied on
  hmdfs — set TMPDIR to the build staging dir (CI cache may differ).
- self.run env arg must be a list — use command-prefix env vars.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XzConan(ConanFile):
    name = "xz"
    version = "5.8.3.1"
    description = "General-purpose data compression library (liblzma)"
    license = "0BSD"
    homepage = "https://tukaani.org/xz/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    package_type = "library"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        tmpdir = os.path.join(self.build_folder, "cfg-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        # E011 (CI #29098): config.status 在子 shell 中重新应用 umask 077，
        # 致生成的 ./confXXX/ 临时目录 0700 权限——HMDFS 下目录 owner 与进程
        # UID 不一致 → subs1.awk: Permission denied。shell 前缀 'umask 022'
        # 被 config.status 内部 umask 077 覆盖（CI #29096 修复无效）。
        # 根因修复：直接 patch configure 脚本内容，将 'umask 077' 替换为
        # 'umask 022'，使 config.status 生成的临时目录可被进程访问。
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            configure_content = f.read()
        if "umask 077" in configure_content:
            configure_content = configure_content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(configure_content)
        bld = "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
        cfg = (f"umask 022 && CC=/data/service/hnp/bin/clang TMPDIR='{tmpdir}' "
               f"./configure {bld} --disable-nls")
        self.run(cfg, cwd=self.source_folder)
        self.run(f"umask 022 && make -j2 TMPDIR='{tmpdir}'", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        if not os.path.isfile(os.path.join(src, "src", "xz", "xz")):
            raise ConanException(f"xz binary missing under {src}")
        for entry in ("src", "lib", "include"):
            s = os.path.join(src, entry)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(self.package_folder, entry))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "src", "xz")
        self.output.info(f"PATH={bindir}")
