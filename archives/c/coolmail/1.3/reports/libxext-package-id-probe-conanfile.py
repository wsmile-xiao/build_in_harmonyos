#!/usr/bin/env python3
"""Minimal probe proving libxext/6.4.0.1 has no binary for the libxt/1.3.1 graph.

Reproduce (the file must be named conanfile.py inside the probe directory;
<ABS_WORKTREE> is the absolute path of this build_in_harmonyos worktree):

    mkdir -p probe && cp libxext-package-id-probe-conanfile.py probe/conanfile.py
    conan install probe \
        -pr:h=<ABS_WORKTREE>/ci/conan/profiles/ohos-aarch64 \
        --build=never -of probe/out

The profile MUST be given as an absolute path (or at least ./relative): Conan's
get_profile_path() looks in $CONAN_HOME/profiles/ FIRST for any relative path
that does not start with ./ or ../, so a bare `-pr:h=ci/conan/profiles/...`
can silently pick up a stale same-named copy and fail with an unrelated
"settings.os.version value not defined" error (observed exit code 6 here).

Expected: exit code 1 with
    ERROR: Missing binary: libxext/6.4.0.1:eab79208a9437a856077cc57885309d75bdb4a31
The full output is archived verbatim in libxext-package-id-probe-log.md.
"""
from conan import ConanFile

class CoolmailXextProbe(ConanFile):
    name = "coolmailxextprobe"
    version = "1.3"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libxt/1.3.1")
        self.requires("libxext/6.4.0.1")
        self.requires("libx11/1.8.13", force=True)
