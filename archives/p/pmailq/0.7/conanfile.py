#!/usr/bin/env python3
"""Conan recipe for pmailq 0.7 - Postfix Mail Queue manager.

pmailq is a single-file Python 3 script (no C/C++ compilation) that processes
the output of `postqueue -p` and can list/parse/delete queued messages in
batches. Upstream build system is a trivial Makefile that only regenerates the
manpage via pod2man; the runnable artifact is the `pmailq` script itself.

Build system: custom (pure Python script install).
Package type: application (single executable script in bin/).
"""

import json
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PmailqConan(ConanFile):
    name = "pmailq"
    version = "0.7"
    description = "Postfix Mail Queue manager (list/parse/delete queued messages)"
    license = "WTFPL"
    homepage = "https://github.com/k0lter/pmailq"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # R25/CI L0p: script-only package, compiler/build_type unused but all four
    # settings are required by the profile gate.
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Syntax check replaces compilation for a pure Python script. This is a
        # real verification: a broken script fails py_compile and fails build.
        self.run("python3 -m py_compile pmailq", cwd=self.source_folder)
        # Upstream ships no test suite (no tests/ dir, no check/test target in
        # Makefile, no test framework). Emit the machine-readable marker so the
        # preflight gate can verify the audit instead of guessing.
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "python3 -m py_compile pmailq + source-tree audit",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "upstream 0.7 ships no tests: no tests/ dir, Makefile has only man target, no check/test target",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "pmailq", src=self.source_folder, dst=bin_dir)
        target = os.path.join(bin_dir, "pmailq")
        if os.path.isfile(target):
            os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # Manpage source + docs for completeness.
        doc_dir = os.path.join(self.package_folder, "share", "doc", "pmailq")
        os.makedirs(doc_dir, exist_ok=True)
        for doc in ("README.md", "CHANGELOG", "COPYING", "AUTHORS", "pmailq.pod"):
            src = os.path.join(self.source_folder, doc)
            if os.path.isfile(src):
                copy(self, doc, src=self.source_folder, dst=doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
