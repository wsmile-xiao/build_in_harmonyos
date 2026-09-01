#!/usr/bin/env python3
"""Conan recipe for aurpublish — PKGBUILD management framework for the AUR.

Pure bash-script CLI, no compiled artifacts: the upstream Makefile renders
aurpublish.in via sed (substituting the @HOOKSDIR@ placeholder) and installs
the script, git hooks and shell completions.  man pages require a2x
(asciidoc) which is unavailable on this platform and in CI — skipped, see
notes.md.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, load, save)
from conan.tools.layout import basic_layout


class AurpublishConan(ConanFile):
    name = "aurpublish"
    version = "20231227.3b978be"
    description = ("PKGBUILD management framework for the Arch User "
                   "Repository: publish package subtrees to the AUR via git")
    license = "GPL-2.0-only"
    homepage = "https://github.com/eli-schwartz/aurpublish"
    url = "https://github.com/eli-schwartz/aurpublish"

    package_type = "application"

    # L0p: OHOS profile requires all four settings attributes
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream renders the script with sed (Makefile: `edit` rule):
        #   sed -e 's|@HOOKSDIR@|$(HOOKSDIR)|g' aurpublish.in > aurpublish
        # The default HOOKSDIR is a build-time absolute path
        # ($(PREFIX)/share/aurpublish). Inject a runtime-resolved path
        # relative to the installed script instead, so the conan package is
        # relocatable (no hardcoded prefix inside the packaged script).
        hooksdir = '$(dirname -- "$(readlink -f -- "$0")")/../share/aurpublish'
        src = os.path.join(self.source_folder, "aurpublish.in")
        content = load(self, src)
        content = content.replace("@HOOKSDIR@", hooksdir)
        script = os.path.join(self.build_folder, "aurpublish")
        save(self, script, content)
        os.chmod(script, 0o755)

    def package(self):
        # bin/aurpublish — the rendered script
        copy(self, "aurpublish", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        os.chmod(os.path.join(self.package_folder, "bin", "aurpublish"), 0o755)

        # share/aurpublish/*.hook — git hooks, installed as symlinks by
        # `aurpublish setup` (must be executable)
        hook_dst = os.path.join(self.package_folder, "share", "aurpublish")
        copy(self, "*.hook", src=self.source_folder, dst=hook_dst,
             keep_path=False)
        for hook in glob.glob(os.path.join(hook_dst, "*.hook")):
            os.chmod(hook, 0o755)

        # shell completions (upstream layout)
        zsh_dst = os.path.join(self.package_folder, "share", "zsh",
                               "site-functions")
        copy(self, "aurpublish.zsh",
             src=os.path.join(self.source_folder, "completion"), dst=zsh_dst,
             keep_path=False)
        os.rename(os.path.join(zsh_dst, "aurpublish.zsh"),
                  os.path.join(zsh_dst, "_aurpublish"))
        copy(self, "aurpublish.bash",
             src=os.path.join(self.source_folder, "completion"),
             dst=os.path.join(self.package_folder, "share",
                              "bash-completion", "completions"),
             keep_path=False)
        # man pages skipped: a2x (asciidoc) unavailable, see notes.md

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
