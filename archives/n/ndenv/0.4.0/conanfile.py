#!/usr/bin/env python3
"""Conan recipe for ndenv 0.4.0 — Node.js version manager (shell scripts).

ndenv is a pure shell script project (rbenv-style dispatcher, no C/C++
compilation). The recipe packages bin + libexec scripts + shell
completions with symlinks preserved.
Upstream ships no test suite (no test/ dir, no bats/Makefile/CMake
targets), so build() only sanity-checks the payload and emits the
no_tests evidence marker; test_package provides the real smoke test.
OHOS portability fix is applied recipe-side in build()
(_patch_ohos_getcwd_fallback, pure-Python string replacement, no .patch
files): libexec/ndenv and libexec/ndenv-which tolerate getcwd failures
(HNP /storage sandbox reports "Not supported") by falling back to $PWD.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class NdenvConan(ConanFile):
    name = "ndenv"
    version = "0.4.0"
    description = "Node.js version manager based on rbenv (shell scripts)"
    license = "MIT"
    homepage = "https://github.com/riywo/ndenv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_ohos_getcwd_fallback(self):
        # HarmonyOS HNP /storage sandbox reports getcwd "Not supported";
        # pwd then fails and `set -e` aborts the dispatcher. Fall back to
        # $PWD, which POSIX shells maintain. Pure-Python edit (no .patch
        # files) to avoid Conan patch-parser fragility on this host.
        ndenv = os.path.join(self.source_folder, "libexec", "ndenv")
        which = os.path.join(self.source_folder, "libexec", "ndenv-which")
        replace_in_file(self, ndenv,
                        'local cwd="$(pwd)"',
                        'local cwd="$(pwd 2>/dev/null || echo "${PWD:-/}")"')
        replace_in_file(self, ndenv,
                        'NDENV_DIR="$(pwd)"',
                        'NDENV_DIR="$(pwd 2>/dev/null || echo "${PWD:-/}")"')
        replace_in_file(self, ndenv,
                        '  pwd\n  cd "$cwd"',
                        '  pwd 2>/dev/null || echo "${cwd:-/}"\n  cd "$cwd" 2>/dev/null || true')
        replace_in_file(self, ndenv,
                        '  cd "$OLDPWD"',
                        '  cd "$OLDPWD" 2>/dev/null || true')
        replace_in_file(self, which,
                        'local cwd="$(pwd)"',
                        'local cwd="$(pwd 2>/dev/null || echo "${PWD:-/}")"')
        replace_in_file(self, which,
                        '  cd "$1"\n  pwd\n  cd "$cwd"',
                        '  cd "$1" 2>/dev/null || return 1\n  pwd 2>/dev/null || echo "$1"\n  cd "$cwd" 2>/dev/null || true')

    def build(self):
        self._patch_ohos_getcwd_fallback()
        # Payload sanity check: dispatcher + version reporter must exist.
        dispatcher = os.path.join(self.source_folder, "libexec", "ndenv")
        versioner = os.path.join(self.source_folder, "libexec", "ndenv---version")
        for script in (dispatcher, versioner):
            if not os.path.isfile(script):
                raise ConanException(f"ndenv payload incomplete, missing: {script}")
        # Upstream ships no test suite (see test_package/MANIFEST.yml audit),
        # so there is nothing to execute here; emit the no_tests marker.
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "payload sanity check (upstream ships no test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "ndenv 0.4.0 上游无测试套件：仓库根仅 bin/completions/libexec，无 test 目录、无 bats/Makefile/CMake 测试目标（审计见 test_package/MANIFEST.yml）",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        # Copy libexec scripts (the core of ndenv) preserving symlinks.
        libexec_src = os.path.join(self.source_folder, "libexec")
        libexec_dst = os.path.join(self.package_folder, "libexec")
        shutil.copytree(libexec_src, libexec_dst, symlinks=True)

        # Create bin/ndenv as symlink to ../libexec/ndenv (same as upstream).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        bin_link = os.path.join(bin_dir, "ndenv")
        if os.path.islink(bin_link) or os.path.exists(bin_link):
            os.remove(bin_link)
        os.symlink("../libexec/ndenv", bin_link)

        # Copy shell completions.
        completions_src = os.path.join(self.source_folder, "completions")
        completions_dst = os.path.join(self.package_folder, "completions")
        if os.path.isdir(completions_src):
            shutil.copytree(completions_src, completions_dst, symlinks=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec"]
