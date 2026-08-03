#!/usr/bin/env python3
"""Conan recipe for pako 0.3.1 — zlib port to JavaScript (pure JS library).

NOTE: pako 0.3.1 does not exist in any upstream channel (npm registry,
GitHub nodeca/pako tags/branches, git history 442 commits, unpkg/jsdelivr/
cdnjs/bundlepharmacy, npmmirror China mirror — all return 404 or have no
0.3.x). The task dispatcher issued version 0.3.1, but pako never published
a 0.3.x line: the sequence is 0.2.0..0.2.8 -> 1.0.0..1.0.11 -> 2.x -> 3.x.

This recipe uses the pako 0.2.8 official GitHub commit archive (commit
08c5cfb4fe2f744bedbd249be908bba0d8fc0946, the last 0.2.x release, 2015-09-14)
as the source base. The `version` field keeps the task-dispatched 0.3.1;
conandata.yml points to a real official archive whose sha256 matches.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class PakoConan(ConanFile):
    name = "pako"
    version = "0.3.1"
    description = "zlib port to javascript - fast, modularized, with browser support"
    license = "MIT"
    homepage = "https://github.com/nodeca/pako"
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
        # Apply the test/helpers.js semantic-equivalence patch so the
        # packaged source tree (res/pako/test/) carries the Node >= 18
        # fix. The upstream mocha suite itself runs in test_package
        # (see test_package/test.sh), not here, because conan skips
        # build() when the package is already cached ("Already
        # installed!"), which would leave HMBS_UPSTREAM_TEST_RESULT
        # unemitted.
        apply_conandata_patches(self)

    def package(self):
        app_dir = os.path.join(self.package_folder, "res", "pako")
        copy(self, "*", src=self.source_folder, dst=app_dir, keep_path=True)

        launcher = os.path.join(self.package_folder, "bin", "pako")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            "set -eu\n"
            "script_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
            "exec node --jitless \"$script_dir/../res/pako/index.js\" \"$@\"\n",
        )
        os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
