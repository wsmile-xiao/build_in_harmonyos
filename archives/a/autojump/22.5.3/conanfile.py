#!/usr/bin/env python3
"""Conan recipe for autojump — a cd command that learns.

autojump is a pure Python/bash script tool (no C compilation).
Build: python3 install.py copies scripts to staging directory.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class AutojumpConan(ConanFile):
    name = "autojump"
    version = "22.5.3"
    description = "A cd command that learns - easily navigate directories from the command line"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/wting/autojump"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        zshshare = os.path.join(staging, "usr", "share", "zsh", "site-functions")
        self.run(
            'python3 install.py -d "{}" -p usr/local -z "{}" --force'.format(
                staging, zshshare
            )
        )
        # install.py's modify_autojump_sh() appends a "custom install" check
        # containing the absolute staging path — a build-machine path that
        # will not exist on consumer devices. Strip that block; conan
        # installs are served by the AUTOJUMP_SHARE_DIR branch (patch 0001).
        autojump_sh = os.path.join(staging, "etc", "profile.d", "autojump.sh")
        with open(autojump_sh, "r") as f:
            content = f.read()
        marker = "# check custom install"
        if marker not in content:
            raise ConanInvalidConfiguration(
                "install.py no longer appends the '%s' block; re-check "
                "modify_autojump_sh() handling in this recipe" % marker
            )
        content = content.split(marker)[0].rstrip() + "\n"
        with open(autojump_sh, "w") as f:
            f.write(content)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        # Copy usr/local (bin, share, share/man)
        copy(
            self,
            "*",
            src=os.path.join(staging, "usr", "local"),
            dst=os.path.join(self.package_folder, "usr", "local"),
        )
        # Copy etc/profile.d (autojump.sh shell integration)
        etc_dir = os.path.join(staging, "etc", "profile.d")
        if os.path.exists(etc_dir):
            copy(
                self,
                "*",
                src=etc_dir,
                dst=os.path.join(self.package_folder, "etc", "profile.d"),
            )
        # Copy zsh completions
        zsh_dir = os.path.join(staging, "usr", "share", "zsh", "site-functions")
        if os.path.exists(zsh_dir):
            copy(
                self,
                "*",
                src=zsh_dir,
                dst=os.path.join(
                    self.package_folder, "usr", "share", "zsh", "site-functions"
                ),
            )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/local/bin"]
        self.cpp_info.resdirs = ["usr/local/share/autojump"]
        # autojump.sh (patch 0001) checks AUTOJUMP_SHARE_DIR to locate the
        # shell integration files. runenv_info is what consumers' VirtualRunEnv
        # aggregates; the path is evaluated on the consumer machine from
        # package_folder, never a build-machine cache path.
        share_dir = os.path.join(
            self.package_folder, "usr", "local", "share", "autojump"
        )
        self.runenv_info.define("AUTOJUMP_SHARE_DIR", share_dir)
