#!/usr/bin/env python3
"""Conan recipe for chruby 0.3.9 — pure Shell (Bash) script project.

chruby is a Ruby version management tool. It is a pure Shell script project
with no compilation step; "installation" consists of copying scripts from
bin/ and share/ to a prefix directory.

Platform compatibility:
  - Shebang #!/usr/bin/env bash is already OHOS-compatible (no /bin/bash needed)
  - No C code, no ELF binaries
  - chruby-exec --version works out of the box

R28: test_package/ exists.
R32: settings.os uses "os" only (no compiler needed for shell scripts).
R38: Command-line tool — commands.json declared at software level.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ChrubyConan(ConanFile):
    name = "chruby"
    version = "0.3.9.1"
    description = "Ruby version management tool (pure Bash scripts)"
    license = "MIT"
    homepage = "https://github.com/postmodern/chruby"
    url = "https://github.com/postmodern/chruby"

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
        # chruby is a pure shell project — no compilation needed.
        # Stage install into a temporary prefix within the source folder.
        prefix = os.path.join(self.source_folder, "staging")
        self.run(f'make install PREFIX="{prefix}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.source_folder, "staging")
        # Copy bin/ scripts
        copy(self, "*", src=os.path.join(staging, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Copy share/chruby/ shell libraries (preserve directory structure)
        copy(self, "*", src=os.path.join(staging, "share"),
             dst=os.path.join(self.package_folder, "share"), keep_path=True)
        # Ensure executables are executable
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for fname in os.listdir(bin_dir):
                fpath = os.path.join(bin_dir, fname)
                if os.path.isfile(fpath):
                    os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # Pure script project: no libraries, just executables in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
