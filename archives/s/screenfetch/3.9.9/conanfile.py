#!/usr/bin/env python3
"""Conan recipe for screenfetch 3.9.9 — pure Shell (Bash) script project.

screenFetch is a CLI Bash script that gathers system/theme information for
screenshots. It ships a single self-contained shell script (screenfetch-dev)
plus a man page; there is no build system and no compilation step. "Building"
consists of installing the script and its documentation under a prefix.

Platform compatibility:
  - Shebang #!/usr/bin/env bash is OHOS-compatible (no /bin/bash hard-coded).
  - No C code, no ELF binaries — only a Bash script and a man page.
  - Runtime needs only Bash 4.0+ and common coreutils (awk/sed/grep/date/...),
    all present on HarmonyOS PC.
  - `screenfetch --version` / `--help` work out of the box on OHOS.

R28: test_package/ exists.
R32: settings.os uses "os" only (no compiler needed for a shell script).
R38: Command-line tool — commands.json declared at the software level.
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ScreenfetchConan(ConanFile):
    name = "screenfetch"
    version = "3.9.9"
    description = "CLI Bash script to show system/theme info in screenshots"
    license = "GPL-3.0"
    homepage = "https://github.com/KittyKatt/screenFetch"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # screenfetch is a pure shell project — no compilation step.
        # Nothing to build; the script is installed verbatim in package().

    def package(self):
        src = self.source_folder
        # Install the upstream script (shipped as `screenfetch-dev`) as the
        # conventional `screenfetch` command (distros install it under this
        # name, matching the screenfetch.1 man page).
        script_src = os.path.join(src, "screenfetch-dev")
        # Fail fast if the upstream script is missing or renamed. Conan 2.29's
        # tools.files.copy() has no `raises` kwarg and silently skips a missing
        # source, so an upstream rename would otherwise ship a package with no
        # `screenfetch` command (AI review flagged this silent data-integrity
        # defect; the suggested `raises=True` is unavailable in this Conan
        # version — confirmed via copy() signature — hence the explicit guard
        # on the source file itself, before staging).
        if not os.path.isfile(script_src):
            raise ConanException(
                f"screenfetch-dev not found in source '{src}'; expected the "
                "upstream Bash script to be present after source()."
            )
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "screenfetch-dev", src=src, dst=bin_dir, keep_path=False)
        os.rename(os.path.join(bin_dir, "screenfetch-dev"),
                  os.path.join(bin_dir, "screenfetch"))
        # Make the script executable
        script = os.path.join(bin_dir, "screenfetch")
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        # Install the man page
        copy(self, "screenfetch.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        # Install license and readme
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "share", "licenses", "screenfetch"), keep_path=False)
        copy(self, "README.mkdn", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "screenfetch"), keep_path=False)

    def package_info(self):
        # Pure script project: no libraries, just an executable in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
