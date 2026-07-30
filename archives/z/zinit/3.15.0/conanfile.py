#!/usr/bin/env python3
"""Conan recipe for zinit 3.15.0 — Zsh plugin manager (pure Shell scripts).

zinit is a flexible and fast Zsh plugin manager. It consists of pure Shell
scripts with optional Zsh byte-compilation (.zwc) for faster loading.

Platform adaptations for OHOS:
  1. Shebang fix: #!/bin/zsh → #!/usr/bin/env zsh (no /bin/zsh on OHOS)
  2. run-help is OHOS-incompatible (uses hardcoded /bin/zsh paths); disabled
"""
import os
import stat
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZinitConan(ConanFile):
    name = "zinit"
    version = "3.15.0"
    description = "Flexible and fast Zsh plugin manager"
    license = "MIT"
    homepage = "https://github.com/zdharma-continuum/zinit"
    url = "https://github.com/zdharma-continuum/zinit"
    package_type = "application"

    settings = "os", "arch"

    script_files = (
        "zinit.zsh", "zinit-autoload.zsh", "zinit-install.zsh",
        "zinit-side.zsh", "zinit-additional.zsh", "_zinit",
        "zi-browse-symbol",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Fix shebangs: OHOS has no /bin/zsh, use /usr/bin/env zsh
        for fname in self.script_files:
            fpath = os.path.join(self.source_folder, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, "r") as f:
                first_line = f.readline()
            if first_line.startswith("#!/bin/zsh"):
                with open(fpath, "r") as f:
                    content = f.read()
                content = content.replace("#!/bin/zsh", "#!/usr/bin/env zsh", 1)
                with open(fpath, "w") as f:
                    f.write(content)
                self.output.info(f"Fixed shebang: {fname}")

        # Try optional Zsh byte-compilation if zsh is available
        try:
            result = subprocess.run(
                ["make", "zwc"], cwd=self.source_folder,
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                self.output.info("Zsh byte-compilation (zwc) succeeded")
            else:
                self.output.info("Zsh byte-compilation skipped (zsh may not be available)")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.output.info("Zsh byte-compilation skipped (make/zsh not available)")

    def package(self):
        # Copy main zsh scripts
        copy(self, "*.zsh", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "zinit"), keep_path=False)
        copy(self, "*.zwc", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "zinit"), keep_path=False)
        copy(self, "_zinit", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "zinit"), keep_path=False)
        copy(self, "zi-browse-symbol", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "zinit"), keep_path=False)
        copy(self, "VERSION", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "zinit"), keep_path=False)
        # Copy scripts directory
        copy(self, "*", src=os.path.join(self.source_folder, "scripts"),
             dst=os.path.join(self.package_folder, "share", "zinit", "scripts"), keep_path=False)
        # Copy share directory (ctags, completions)
        copy(self, "*", src=os.path.join(self.source_folder, "share"),
             dst=os.path.join(self.package_folder, "share", "zinit", "share"), keep_path=False)
        # Copy LICENSE
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "zinit"), keep_path=False)

        # Make scripts executable
        bin_dir = os.path.join(self.package_folder, "share", "zinit")
        for fname in self.script_files:
            fpath = os.path.join(bin_dir, fname)
            if os.path.isfile(fpath):
                os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["share/zinit"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
