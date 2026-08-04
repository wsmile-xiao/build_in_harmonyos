#!/usr/bin/env python3
"""Conan recipe for gel 0.3.0 — modern Ruby gem manager.

gel is a pure Ruby script tool for managing Ruby gems. No compilation
is required; packaging copies the exe/gel script and lib/ directory
into the Conan package. Man pages are generated from .ronn sources
using ronn if available, otherwise skipped.

Platform compatibility:
  - Shebang #!/usr/bin/env ruby --disable=gems works on OHOS if Ruby is installed
  - No C code, no ELF binaries
  - require_relative paths work with bin/ + lib/ package layout

R28: test_package/ exists.
R32: settings.os uses "os" only (no compiler needed for Ruby scripts).
R34: test_package exercises the packaged CLI by running gel --help.
R38: Command-line tool — commands.json declared at software level.
"""
import os
import stat
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class GelConan(ConanFile):
    name = "gel"
    version = "0.3.0"
    description = "A modern gem manager"
    license = "MIT"
    homepage = "https://gel.dev"
    url = ""

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
        # gel is a pure Ruby script tool — no compilation needed.
        # Try to generate man pages from .ronn files using ronn.
        man_dir = os.path.join(self.source_folder, "man", "man1")
        if os.path.isdir(man_dir):
            ronn_files = sorted(
                os.path.join(man_dir, f) for f in os.listdir(man_dir) if f.endswith(".ronn")
            )
            if ronn_files:
                try:
                    cmd = ["ronn", "--manual", "Gel Manual"] + ronn_files
                    subprocess.run(cmd, check=True, capture_output=True, timeout=60)
                    self.output.info("Man pages generated successfully with ronn")
                except FileNotFoundError:
                    self.output.warning(
                        "ronn not available — man pages will be skipped. "
                        "Install ronn (gem install ronn) to enable man page generation."
                    )
                except subprocess.CalledProcessError as e:
                    self.output.warning(
                        f"ronn failed (exit {e.returncode}): "
                        f"{e.stderr.decode('utf-8', errors='replace') if e.stderr else 'unknown'}. "
                        "Man pages will be skipped."
                    )
                except subprocess.TimeoutExpired:
                    self.output.warning("ronn timed out — man pages will be skipped.")

    def package(self):
        # Copy executable: exe/gel -> bin/gel
        copy(self, "gel", src=os.path.join(self.source_folder, "exe"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # Copy lib directory (preserves structure: lib/gel/...)
        copy(self, "*", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=True)

        # Copy man pages if generated (.1 files, not .ronn sources)
        man_src = os.path.join(self.source_folder, "man", "man1")
        if os.path.isdir(man_src):
            copy(self, "*.1", src=man_src,
                 dst=os.path.join(self.package_folder, "share", "man", "man1"),
                 keep_path=False)

        # Ensure gel executable has execute permission
        gel_bin = os.path.join(self.package_folder, "bin", "gel")
        if os.path.isfile(gel_bin):
            os.chmod(gel_bin, os.stat(gel_bin).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
