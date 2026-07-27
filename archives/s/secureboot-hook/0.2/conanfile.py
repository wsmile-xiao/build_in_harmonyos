#!/usr/bin/env python3
"""Conan recipe for secureboot-hook 0.2 — pure Shell script project.

secureboot-hook is a Void Linux kernel hook that generates a signed UKI
(Unified Kernel Image) for secure boot. It is a pure shell script project
with no compilation step; "installation" consists of copying scripts and
config files to etc/kernel.d/.

Platform compatibility:
  - Shebang #!/usr/bin/bash is OHOS-compatible
  - No C code, no ELF binaries
  - Runtime deps: dracut, sbctl, binutils (Void Linux specific)

R28: test_package/ exists.
R32: settings.os uses "os" only (no compiler needed for shell scripts).
R38: Command-line tool — commands.json declared at software level.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SecurebootHookConan(ConanFile):
    name = "secureboot-hook"
    version = "0.2"
    description = "Void Linux kernel hook for signed UKI generation (pure shell scripts)"
    license = "GPL-3.0"
    homepage = "https://github.com/spflaumer/secureboot-hook-void"
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
        # secureboot-hook is a pure shell project — no compilation needed.
        # Stage install into a temporary prefix within the source folder.
        prefix = os.path.join(self.source_folder, "staging")
        self.run(f'make install PREFIX="{prefix}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.source_folder, "staging")
        # Copy installed etc/kernel.d/ files
        etc_dir = os.path.join(staging, "etc", "kernel.d")
        if os.path.isdir(etc_dir):
            copy(self, "*", src=etc_dir,
                 dst=os.path.join(self.package_folder, "etc", "kernel.d"),
                 keep_path=True)
        # Ensure hook script is executable
        hook_path = os.path.join(self.package_folder, "etc", "kernel.d",
                                 "post-install", "30-secureboot")
        if os.path.isfile(hook_path):
            os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # Pure script project: no libraries
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["etc"]
