#!/usr/bin/env python3
"""Conan recipe for shml 1.1.0: a Bash library that users ``source`` (nothing is compiled).

Upstream: https://github.com/odb/shml (MIT).
Upstream tests: ``make test`` fetches the shunt framework with ``curl | bash`` from a
floating ref at test time (not reproducible, banned in recipes by CI L0o).  shunt v0.3.1
is pinned in conandata.yml instead and runs the 9 unmodified ``test/*_tests.sh`` files.
"""
import glob
import os
import re
import shlex
import shutil
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Runtime assertions shunt counts for the 9 upstream test files (142 assert_equal call
# sites, several inside loops). A different total means tests were silently skipped.
UPSTREAM_ASSERTIONS = 172


def _find_bash():
    found = shutil.which("bash")
    if found:
        return found
    for candidate in ("/data/service/hnp/bin/bash", "/bin/bash"):
        if os.path.isfile(candidate):
            return candidate
    raise ConanException("bash is required to test and consume shml")


class ShmlConan(ConanFile):
    name = "shml"
    version = "1.1.0"
    description = "SHML: sourceable Bash helpers for ANSI colours, attributes and layout"
    license = "MIT"
    homepage = "https://github.com/odb/shml"
    url = "https://github.com/odb/shml"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        get(self, **self.conan_data["shunt"], strip_root=True,
            destination=os.path.join(self.source_folder, "shunt"))

    def build(self):
        apply_conandata_patches(self)
        tests = sorted(os.path.relpath(p, self.source_folder) for p in
                       glob.glob(os.path.join(self.source_folder, "test", "*_tests.sh")))
        if not tests:
            raise ConanException("shml upstream test files are missing")
        # Relative paths on purpose: shunt greps its own argv for "-h" / "--plain".
        cmd = " ".join([shlex.quote(_find_bash()), "shunt/shunt.sh", "--plain", "--verbose"]
                       + [shlex.quote(t) for t in tests])
        out, err = StringIO(), StringIO()
        rc = self.run(cmd, cwd=self.source_folder, stdout=out, stderr=err,
                      ignore_errors=True)
        log = out.getvalue() + err.getvalue()
        summary = re.search(r"Total: (\d+)\s+Passed: (\d+)\s+Failed: (\d+)", log)
        if not summary:
            raise ConanException("shunt printed no summary:\n" + log[-2000:])
        total, passed, failed = (int(x) for x in summary.groups())
        self.output.info(f"SHML UPSTREAM TEST PASS/FAIL: {passed}/{total} "
                         f"({len(tests)} test files, rc={rc})")
        if rc != 0 or failed or total != UPSTREAM_ASSERTIONS:
            raise ConanException(f"shml upstream tests failed (rc={rc}, failed={failed}, "
                                 f"total={total}, expected {UPSTREAM_ASSERTIONS}):\n"
                                 + log[-4000:])

    def package(self):
        copy(self, "shml.sh", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "shml"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()  # one script for every os/arch/compiler

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.define_path(
            "SHML_SCRIPT", os.path.join(self.package_folder, "share", "shml", "shml.sh"))
