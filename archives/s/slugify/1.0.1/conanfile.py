#!/usr/bin/env python3
"""Conan recipe for slugify 1.0.1 — bash command that converts filenames and
directories to a web friendly format.

Pure bash script (no compilation). The script relies on bash-only syntax
([[ ]], `function`, `==` in test, getopts), so the interpreter comes from the
bash/5.3 package instead of whatever shell the host happens to have.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class SlugifyConan(ConanFile):
    name = "slugify"
    version = "1.0.1"
    description = ("Bash command that converts filenames and directories to a "
                   "web friendly format")
    license = "MIT"
    homepage = "https://github.com/JabberLabs/slugify"
    url = "https://github.com/JabberLabs/slugify"
    topics = ("slug", "rename", "filename", "cli", "bash")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"slugify targets Linux/OHOS only, got os={self.settings.os}")

    def requirements(self):
        # run=True: consumers need the interpreter at runtime, so its binary
        # is always installed and VirtualRunEnv puts its bin/ on their PATH.
        self.requires("bash/5.3", run=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # The v1.0.1 tag predates the upstream LICENSE file (see conandata.yml).
        download(self, filename="LICENSE",
                 **self.conan_data["license"][self.version])

    def build(self):
        apply_conandata_patches(self)
        if can_run(self):
            # Parse-only check of the patched script with the target bash.
            bash = os.path.join(self.dependencies["bash"].package_folder,
                                "bin", "bash")
            self.run(f'"{bash}" -n slugify', cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "slugify", src=self.source_folder, dst=bindir)
        copy(self, "slugify.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Best effort: HMDFS normalises permission bits, and HarmonyOS refuses
        # to exec #! scripts from user storage anyway, so the supported
        # invocation there is `bash "$(command -v slugify)"` (see notes.md).
        try:
            os.chmod(os.path.join(bindir, "slugify"), 0o755)
        except OSError as exc:
            self.output.warning(f"chmod on bin/slugify failed: {exc}")

    def package_id(self):
        # Only an interpreted script is packaged: one package for every
        # configuration.
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
