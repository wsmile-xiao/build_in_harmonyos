#!/usr/bin/env python3
"""Conan recipe — gpatch 2.8 (Autotools)"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GpatchConan(ConanFile):
    name = "gpatch"
    version = "2.8"
    package_type = "application"
    description = "GNU patch utility for applying diff files to original files"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/patch/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
            tc.configure_args.append(f"SHELL={bash}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: HMDFS 上 umask 077 创建的临时目录权限为 2700/drwx--S---，
        # 导致 configure 二次运行时无法在临时目录中创建文件。
        # 将 configure 脚本中的 umask 077 改为 umask 022 适配 HMDFS。
        import glob as _glob
        import os as _os
        for _cfg in _glob.glob(_os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
                self.output.info("configure: umask 077 → 022 (E011 HMDFS compatibility)")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
