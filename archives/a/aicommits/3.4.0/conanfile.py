#!/usr/bin/env python3
"""Conan recipe — aicommits 3.4.0 (npm / Node.js CLI tool).

aicommits is a zero-dependency Node.js CLI (dist/cli.mjs is the final
bundled artifact from the npm tarball; no build step required). It is
packaged as an application: dist/ files are installed to libexec and a
thin launcher script is generated in bin/ that invokes the system node.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AicommitsConan(ConanFile):
    name = "aicommits"
    version = "3.4.0"
    description = "A CLI that writes your git commit messages for you with AI"
    license = "MIT"
    homepage = "https://github.com/Nutlope/aicommits"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply any patches declared in conandata.yml (currently none)
        apply_conandata_patches(self)
        # No build step: the npm tarball ships the bundled dist/cli.mjs.
        # Verify the entry point exists so packaging fails loudly if the
        # upstream layout ever changes.
        entry = os.path.join(self.source_folder, "dist", "cli.mjs")
        if not os.path.exists(entry):
            raise ConanException("dist/cli.mjs not found in source")

    def package(self):
        # Install bundled JS into libexec/aicommits/
        copy(self, "dist/*", self.source_folder,
             os.path.join(self.package_folder, "libexec", "aicommits"))
        copy(self, "package.json", self.source_folder,
             os.path.join(self.package_folder, "libexec", "aicommits"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "libexec", "aicommits"))

        # Launcher: aicommits + aic alias, executed via system node.
        # node crashes (Signal 5) when inherited OHOS-specific env vars
        # (AppSpawn/ALACRITTY/UBSAN...) are present, so run under a clean
        # env -i with only PATH/HOME/TMPDIR (verified stable on this device).
        cli_abs = os.path.join(self.package_folder, "libexec", "aicommits", "dist", "cli.mjs")
        launcher_body = "\n".join((
            "#!/bin/sh",
            'exec env -i PATH="/data/service/hnp/bin:/usr/bin:/bin" \\',
            'HOME="${HOME:-/storage/Users/currentUser}" \\',
            'TMPDIR="${TMPDIR:-/storage/Users/currentUser/tmp}" \\',
            'node "{}" "$@"'.format(cli_abs),
            "",
        ))
        launcher = os.path.join(self.package_folder, "bin", "aicommits")
        save(self, launcher, launcher_body)
        os.chmod(launcher, 0o755)
        # `aic` alias launcher (upstream package.json declares both bin names)
        alias = os.path.join(self.package_folder, "bin", "aic")
        save(self, alias, launcher_body)
        os.chmod(alias, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
