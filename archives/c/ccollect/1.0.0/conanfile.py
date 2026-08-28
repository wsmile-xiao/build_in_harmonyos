#!/usr/bin/env python3
"""Conan recipe for ccollect 1.0.0 — pure POSIX sh backup tool.

ccollect is a (pseudo) incremental backup tool wrapping rsync. It is a
pure POSIX sh script with a Makefile (install-only, no compilation), so
this package is an application-type recipe: fetch source, apply the OHOS
TMPDIR patch, and install the `ccollect` script to bindir.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    chmod,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CcollectConan(ConanFile):
    name = "ccollect"
    version = "1.0.0"
    description = "(pseudo) incremental backup tool using hardlinks and rsync (pure POSIX sh)"
    homepage = "https://www.nico.schottelius.org/software/ccollect/"
    license = "GPL-3.0-or-later"
    url = ""

    package_type = "application"
    # OHOS profile 使用四项目录 settings：os/compiler/build_type/arch
    # （CI L0p 门禁要求 recipe settings 包含全部四项，防止 profile 不兼容）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply OHOS TMPDIR portability patch (no compilation needed)
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "ccollect", src=self.source_folder, dst=bin_dir)
        chmod(self, os.path.join(bin_dir, "ccollect"), 0o755)
        # Documentation and license
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "ccollect"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "licenses", "ccollect"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
