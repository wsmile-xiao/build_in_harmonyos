#!/usr/bin/env python3
"""Conan recipe for bmt 0.6 — Software Analysis Benchmarking Toolkit.

Pure shell/Perl toolkit, no compilation required.
Installs cpbm entry point and supporting scripts.
"""
from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class BmtConan(ConanFile):
    name = "bmt"
    version = "0.6"
    description = "Software Analysis Benchmarking Toolkit — patch set management, benchmark execution and result evaluation"
    license = "BSD-4-Clause"
    homepage = "https://github.com/tautschnig/bmt"
    url = "https://github.com/tautschnig/bmt"
    topics = ("benchmark", "testing", "cprover", "verification")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        if isinstance(src, list):
            get(self, **src[0], strip_root=True)
        else:
            get(self, **src, strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        share_dir = os.path.join(self.package_folder, "share", "cpbm")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(share_dir, exist_ok=True)

        copy(self, "cpbm", src=os.path.join(self.source_folder, "scripts"), dst=bin_dir)
        for pattern in ["*.sh", "*.pl", "VERSION", "rules.template", "rules.cpbm.generic", "Changelog", "README", "LICENSE"]:
            copy(self, pattern, src=os.path.join(self.source_folder, "scripts"), dst=share_dir)

        # Fix shebangs and SCRIPT_HOME for HarmonyOS /bin/sh compatibility (HNP bash getcwd issue).
        # - Rewrite /bin/bash -> /bin/sh for all installed scripts.
        # - Patch cpbm SCRIPT_HOME to point to ../share/cpbm relative to bin (Debian installs to /usr/share/cpbm).
        for root_folder in [bin_dir, share_dir]:
            for dirpath, _, filenames in os.walk(root_folder):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    except Exception:
                        continue
                    orig = content
                    # Shebang fixes
                    if content.startswith("#!/bin/bash"):
                        content = content.replace("#!/bin/bash", "#!/bin/sh", 1)
                    if content.startswith("#! /bin/bash"):
                        content = content.replace("#! /bin/bash", "#!/bin/sh", 1)
                    if content.startswith("#!/usr/bin/env bash"):
                        content = content.replace("#!/usr/bin/env bash", "#!/usr/bin/env sh", 1)
                    # cpbm specific: SCRIPT_HOME
                    if fname == "cpbm" and "SCRIPT_HOME=`dirname $0`" in content:
                        content = content.replace(
                            "SCRIPT_HOME=`dirname $0`",
                            'SCRIPT_HOME="$(dirname "$0")/../share/cpbm"'
                        )
                    # Fallback if already with $0 but without share fix
                    if fname == "cpbm" and 'SCRIPT_HOME="$(dirname "$0")"' in content:
                        # ensure share suffix
                        if "../share/cpbm" not in content:
                            content = content.replace(
                                'SCRIPT_HOME="$(dirname "$0")"',
                                'SCRIPT_HOME="$(dirname "$0")/../share/cpbm"'
                            )
                    if content != orig:
                        try:
                            with open(fpath, "w", encoding="utf-8", newline="\n") as f:
                                f.write(content)
                        except Exception:
                            pass

        # Ensure cpbm executable bit (HMDFS may ignore chmod, but best effort)
        cpbm_path = os.path.join(bin_dir, "cpbm")
        if os.path.exists(cpbm_path):
            try:
                os.chmod(cpbm_path, 0o755)
            except Exception:
                pass
        # Also chmod share scripts (non-essential)
        for dirpath, _, filenames in os.walk(share_dir):
            for fname in filenames:
                if fname.endswith(".sh") or fname.endswith(".pl"):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        os.chmod(fpath, 0o755)
                    except Exception:
                        pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
