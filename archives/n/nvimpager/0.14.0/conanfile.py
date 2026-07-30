#!/usr/bin/env python3
"""Conan recipe for nvimpager 0.14.0 — pure Shell (Bash) + Lua script project.

nvimpager uses neovim as a pager to view man pages, git diffs, etc. with
neovim's syntax highlighting and mouse support. It is a pure script project
(Bash + Lua) with no C compilation; "installation" consists of configuring the
main script via sed and copying it together with the Lua runtime modules to a
prefix directory.

Platform compatibility:
  - Shebang #!/usr/bin/env bash is OHOS-compatible (bash resolved via PATH).
  - No C code, no ELF binaries produced by this recipe.
  - nvimpager -v / -h work without neovim (both exit before invoking nvim).
  - Full pager functionality requires neovim >= 0.9.0 at runtime (not a Conan
    dependency; provided by the target system or via NVIMPAGER_NVIM env var).

R28: test_package/ exists.
R32: settings limited to "os", "arch" (no compiler needed for scripts).
R38: Command-line tool — commands.json declared at software level.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NvimpagerConan(ConanFile):
    name = "nvimpager"
    version = "0.14.0"
    description = "Use neovim as a pager to view manpages, diffs, etc. with nvim's syntax highlighting"
    license = "BSD-2-Clause"
    homepage = "https://github.com/lucc/nvimpager"
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
        apply_conandata_patches(self)
        # nvimpager is a pure script tool — no compilation step.

    def package(self):
        # Install directly to the package folder so the RUNTIME path baked
        # into the nvimpager script (via the makefile's sed) points to the
        # correct location inside the Conan cache.
        # VERSION is passed explicitly to skip the makefile's `./nvimpager -v`
        # call (which would require bash) during make variable expansion.
        # install-no-man avoids the scdoc dependency needed to build the man
        # page.
        self.run(
            f'make install-no-man PREFIX="{self.package_folder}" VERSION="{self.version}"',
            cwd=self.source_folder,
        )
        # Ensure the installed script is executable (belt-and-suspenders).
        nvimpager_path = os.path.join(self.package_folder, "bin", "nvimpager")
        if os.path.isfile(nvimpager_path):
            os.chmod(
                nvimpager_path,
                os.stat(nvimpager_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH,
            )

    def package_info(self):
        # Pure script project: executables in bin/, Lua runtime under share/.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
