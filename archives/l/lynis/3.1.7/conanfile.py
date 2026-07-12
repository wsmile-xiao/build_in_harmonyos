#!/usr/bin/env python3
"""Conan recipe for lynis 3.1.7 — shell script security auditing tool.

Lynis is a pure shell script tool with no compiled binaries.
This recipe installs the script and data files directly.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file, export_conandata_patches


class LynisConan(ConanFile):
    name = "lynis"
    version = "3.1.7"
    description = "Security and system auditing tool (shell script based)"
    license = "GPL-3.0"
    homepage = "https://cisofy.com/lynis/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No dependencies

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # No toolchain needed for shell scripts

    def build(self):
        lynis_script = os.path.join(self.source_folder, "lynis")
        # Fix shebang for OpenHarmony (E165): /bin/sh -> /data/service/hnp/bin/bash (mksh hangs on lynis script)
        replace_in_file(self, lynis_script, "#!/bin/sh", "#!/data/service/hnp/bin/bash")
        # Patch lynis to find data files relative to script location (not just CWD)
        # This allows lynis to work when installed via conan in non-standard paths
        replace_in_file(
            self, lynis_script,
            'WORKDIR=$(pwd)',
            'WORKDIR=$(pwd)\n        SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)'
        )
        # Add script-relative paths to include search targets
        replace_in_file(
            self, lynis_script,
            'tINCLUDE_TARGETS="/usr/local/include/lynis /usr/local/lynis/include /usr/share/lynis/include ./include"',
            'tINCLUDE_TARGETS="${SCRIPT_DIR}/../include/lynis ${SCRIPT_DIR}/../share/lynis/include /usr/local/include/lynis /usr/local/lynis/include /usr/share/lynis/include ./include"'
        )
        # Add script-relative paths to DB search targets
        replace_in_file(
            self, lynis_script,
            'tDB_TARGETS="/usr/local/share/lynis/db /usr/local/lynis/db /usr/share/lynis/db ./db"',
            'tDB_TARGETS="${SCRIPT_DIR}/../share/lynis/db /usr/local/share/lynis/db /usr/local/lynis/db /usr/share/lynis/db ./db"'
        )
        # Add script-relative paths to plugin search targets
        replace_in_file(
            self, lynis_script,
            'tPLUGIN_TARGETS="/usr/local/lynis/plugins /usr/local/share/lynis/plugins /usr/share/lynis/plugins /etc/lynis/plugins ./plugins"',
            'tPLUGIN_TARGETS="${SCRIPT_DIR}/../share/lynis/plugins /usr/local/lynis/plugins /usr/local/share/lynis/plugins /usr/share/lynis/plugins /etc/lynis/plugins ./plugins"'
        )
        # Make security check read non-blocking (for non-interactive environments)
        replace_in_file(self, lynis_script, "read -r void", "read -r void < /dev/null 2>/dev/null || true")
        # Add early --version handling (skip initialization for version query)
        replace_in_file(
            self, lynis_script,
            'PROGRAM_VERSION="3.1.7"',
            'PROGRAM_VERSION="3.1.7"\n\n    # Early --version handling for non-interactive environments\n    for arg in "$@"; do\n        case "$arg" in\n            --version|-V) echo "Lynis $PROGRAM_VERSION"; exit 0 ;;\n            --help|-h) ;;\n        esac\n    done'
        )
        # Verify syntax
        self.run(f"sh -n {lynis_script}", env="conanrun")

    def package(self):
        # Install lynis script and data files
        copy(self, "lynis", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "lynis.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "*", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "share", "lynis", "include"))
        copy(self, "*", src=os.path.join(self.source_folder, "db"), dst=os.path.join(self.package_folder, "share", "lynis", "db"))
        copy(self, "*", src=os.path.join(self.source_folder, "plugins"), dst=os.path.join(self.package_folder, "share", "lynis", "plugins"))
        copy(self, "default.prf", src=self.source_folder, dst=os.path.join(self.package_folder, "etc", "lynis"))
        copy(self, "developer.prf", src=self.source_folder, dst=os.path.join(self.package_folder, "etc", "lynis"))

    def package_info(self):
        # Lynis is a shell script tool — no compiled libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
