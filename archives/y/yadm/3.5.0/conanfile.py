#!/usr/bin/env python3
"""Conan recipe — yadm 3.5.0 (script/makefile)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class YadmConan(ConanFile):
    name = "yadm"
    version = "3.5.0"
    description = "Yet Another Dotfiles Manager — manage dotfiles using Git"
    license = "GPL-3.0-only"
    homepage = "https://yadm.io"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # yadm is a pure bash script, no compilation needed
        pass

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "yadm", self.source_folder, bin_dir)
        copy(self, "yadm.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "share", "doc", "yadm"))
        copy(self, "CHANGES", self.source_folder, os.path.join(self.package_folder, "share", "doc", "yadm"))

        # OHOS: /bin/sh 不存在，修改 shebang 为鸿蒙 bash 路径
        yadm_path = os.path.join(bin_dir, "yadm")
        with open(yadm_path, "r") as f:
            content = f.read()
        content = content.replace("#!/bin/sh", "#!/data/service/hnp/bin/bash", 1)
        with open(yadm_path, "w") as f:
            f.write(content)
        os.chmod(yadm_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
