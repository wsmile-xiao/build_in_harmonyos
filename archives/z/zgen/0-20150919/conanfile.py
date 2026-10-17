#!/usr/bin/env python3
"""Conan recipe for zgen 0-20150919 — lightweight Zsh plugin manager.

zgen is a pure Zsh project (a single sourced script `zgen.zsh` plus a `_zgen`
completion function). There is no native build step; adaptation work for
OpenHarmony is limited to the interpreter path:

  * `zgen.zsh` shipped a `#!/bin/zsh` shebang. OpenHarmony has no `/bin/zsh`
    (zsh is installed under the package prefix), so the shebang is patched to
    `#!/usr/bin/env zsh` — see patches/0001-zgen.zsh.patch.

The package is architecture independent (`package_id` cleared): the very same
scripts are consumed by the aarch64 OHOS zsh at runtime.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZgenConan(ConanFile):
    name = "zgen"
    version = "0-20150919"
    description = ("Lightweight Zsh plugin manager that generates a static "
                   "init.zsh for fast shell startup")
    license = "MIT"
    homepage = "https://github.com/tarjoilija/zgen"
    url = "https://github.com/tarjoilija/zgen"
    topics = ("zsh", "shell", "plugin-manager", "dotfiles")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # E483: the codeload snapshot URL ends with a commit id, so conan would
        # guess the archive format from that name and fail with BadZipFile.
        # Pass an explicit filename to pin the format.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename=f"zgen-{self.version}.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        self.output.info("zgen is a pure Zsh project; no native build step")

    def package(self):
        share_dir = os.path.join(self.package_folder, "share", "zgen")
        copy(self, "zgen.zsh", src=self.source_folder, dst=share_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=share_dir)
        copy(self, "README.md", src=self.source_folder, dst=share_dir)
        # `_zgen` is a `#compdef zgen` completion function: it must live on FPATH.
        copy(self, "_zgen", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "zsh", "site-functions"))

        script = os.path.join(share_dir, "zgen.zsh")
        os.chmod(script, os.stat(script).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_id(self):
        # Pure Zsh scripts: identical payload for every arch/compiler/build_type.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["share/zgen"]

        share_dir = os.path.join(self.package_folder, "share", "zgen")
        fpath_dir = os.path.join(self.package_folder, "share", "zsh", "site-functions")
        # Consumers add `source $ZGEN_SOURCE_FILE` to .zshrc; FPATH exposes `_zgen`.
        self.runenv_info.define_path("ZGEN_SOURCE_FILE",
                                     os.path.join(share_dir, "zgen.zsh"))
        self.runenv_info.prepend_path("FPATH", fpath_dir)
