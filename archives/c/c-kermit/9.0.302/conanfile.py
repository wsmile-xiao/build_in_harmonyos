#!/usr/bin/env python3
"""Conan recipe — c-kermit 9.0.302 (custom hand-written Makefile).

C-Kermit is Columbia University's portable serial/file-transfer/scripting
tool. Upstream ships no configure/CMake — only a hand-written `makefile`
whose `linux` target probes headers/libs, then recurses into `linuxa`
to build the `wermit` binary (select-based CONNECT module, xermit).
Upstream provides no automated test suite (see test_package/MANIFEST.yml
audit); verification is consumer-side CLI smoke tests in test_package.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CKermitConan(ConanFile):
    name = "c-kermit"
    version = "9.0.302"
    description = "C-Kermit file transfer, terminal connection and scripting tool"
    license = "BSD-3-Clause"
    homepage = "https://www.kermitproject.org/ckermit.html"
    url = "https://www.kermitproject.org/ckermit.html"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # HMBS readonly-/tmp hardening (source phase): conan's get() stages
        # the archive via tempfile (honors TMPDIR); pin it to the HMBS
        # task-private dir so a read-only /tmp cannot truncate the download
        # and cause a spurious sha256 mismatch here (cf. preflight.sh /tmp
        # errors). Upstream hash itself verified locally (3122219 bytes).
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP"))
        if tmpdir:
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
        # cku302.tar.gz unpacks flat (74 top-level entries, no root dir).
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        apply_conandata_patches(self)
        # HMBS readonly-/tmp hardening: redirect tool temp files to the
        # task-private dir injected as TMPDIR/TMP/TEMP (preflight.sh itself
        # hit "can't create temporary file /tmp/..." on a read-only /tmp).
        # Upstream makefile writes no /tmp files; this only covers compiler
        # / make temp files via the environment they already honor.
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP"))
        if tmpdir:
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
        # R33: compiler from Conan conf, never ${CC} from shell env.
        # NOTE: tools.build:compiler_executables is a dict conf
        # (e.g. {"c": "clang", "cpp": "clang++"}); the ":c" sub-key form
        # does not exist in Conan 2.30's conf list and raises
        # "does not exist in configuration list", so read the dict first.
        try:
            compiler_exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compiler_exes = {}
        if isinstance(compiler_exes, dict) and compiler_exes.get("c"):
            cc = compiler_exes["c"]
        else:
            cc = "clang"
        make = os.environ.get("HMBS_MAKE", "make")
        sh = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Upstream `linuxa` recurses with a hardcoded "CC = gcc" / "CC2 = gcc"
        # (72 such sites in the makefile), which discards our CC=... command
        # line override; CI clean env has no gcc -> `gcc: command not found`
        # (build #40845), while a device with gcc in PATH masks the bug.
        # Provide a `gcc` shim on PATH pointing at the Conan compiler so the
        # hardcoded name resolves without touching upstream targets.
        shim_dir = os.path.join(self.build_folder, "hmbs-shim")
        os.makedirs(shim_dir, exist_ok=True)
        gcc_shim = os.path.join(shim_dir, "gcc")
        try:
            if os.path.islink(gcc_shim) or os.path.exists(gcc_shim):
                os.remove(gcc_shim)
            os.symlink(cc, gcc_shim)
        except Exception:
            with open(gcc_shim, "w", newline="\n") as f:
                f.write('#!/bin/sh\nexec "%s" "$@"\n' % cc)
            try:
                os.chmod(gcc_shim, 0o755)
            except Exception:
                pass
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
        # makefile lives in source_folder (basic_layout separates source and
        # build folders; self.run defaults to build_folder where no makefile
        # exists -> "No rule to make target 'linux'"). Build in-place so
        # ./wermit lands where package() expects (source_folder/wermit).
        # R9: -j1 (OHOS build constraint).
        self.run(f"{make} linux CC={cc} CC2={cc} SHELL={sh} -j1",
                 cwd=self.source_folder)

    def package(self):
        # Upstream produces ./wermit; ship it as bin/kermit.
        src = os.path.join(self.source_folder, "wermit")
        dst_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, "kermit"))
        copy(self, "COPYING.TXT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
