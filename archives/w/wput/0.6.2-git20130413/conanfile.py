#!/usr/bin/env python3
"""Conan recipe for Wput 0.6.2, pinned to the 2013-04-13 upstream commit."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class WputConan(ConanFile):
    name = "wput"
    version = "0.6.2-git20130413"
    description = "Command-line FTP file uploader"
    license = "GPL-2.0-or-later"
    homepage = "https://wput.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        git = Git(self)
        git_dir = os.path.join(self.source_folder, ".git")
        if not os.path.isdir(git_dir):
            # Conan may reuse a source folder left by an interrupted create.
            # Clear its contents without removing Conan's current working dir.
            for entry in os.listdir(self.source_folder):
                path = os.path.join(self.source_folder, entry)
                if os.path.islink(path) or not os.path.isdir(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
            os.makedirs(self.source_folder, exist_ok=True)
            git.clone(url=source["url"], target=".", args=["--no-checkout"])
        # HarmonyOS Git rejects Conan cache paths as dubious ownership. Scope
        # safe.directory to this single checkout command; do not alter user config.
        checkout_path = shlex.quote(self.source_folder.replace("\\", "/"))
        self.run(
            "git -c safe.directory=%s -C %s checkout --force %s"
            % (checkout_path, checkout_path, shlex.quote(source["commit"]))
        )
        self.run("git -c safe.directory=%s -C %s clean -fdx -e patches/" % (checkout_path, checkout_path))

    def generate(self):
        AutotoolsToolchain(self, prefix="/").generate()

    def build(self):
        # In this layout Conan resolves export_sources_folder to the source
        # tree during build(). Point patch_file entries to the exported recipe
        # sources explicitly so apply_conandata_patches can open them reliably.
        for patch_entry in self.conan_data.get("patches", []):
            patch_entry["patch_file"] = os.path.abspath(
                os.path.join(self.recipe_folder, "..", "es", patch_entry["patch_file"])
            )
        apply_conandata_patches(self)

        toolchain = AutotoolsToolchain(self, prefix="/")
        toolchain.configure_args.extend([
            "--without-ssl",
            "--disable-g-switch",
        ])
        # The pinned 2009 config.guess cannot recognize HarmonyOS, while its
        # config.sub accepts this equivalent native AArch64 Linux build triplet.
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) == "armv8":
            toolchain.configure_args.append("--build=aarch64-unknown-linux-gnu")

        configure = os.path.join(self.source_folder, "configure")
        command = "%s %s" % (shlex.quote(configure), shlex.join(toolchain.configure_args))
        # This snapshot's hand-written Makefiles are not VPATH-safe, so configure
        # and make must run in the checkout itself.
        self.run(command, cwd=self.source_folder, env="conanbuild")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "wput", src=self.source_folder, dst=bindir, keep_path=False)

        licenses = os.path.join(self.package_folder, "licenses")
        os.makedirs(licenses, exist_ok=True)
        copy(self, "COPYING", src=self.source_folder, dst=licenses, keep_path=False)
        copy(self, "wput.1", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
