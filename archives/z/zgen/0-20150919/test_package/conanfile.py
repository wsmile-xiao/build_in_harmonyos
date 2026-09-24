#!/usr/bin/env python3
"""Conan test_package for zgen 0-20150919.

Two layers, both of which execute real assertions against the packaged files:

  1. test.sh       — POSIX sh: package layout + content assertions
                     (installed files, executable bit, applied shebang patch,
                     completion header, 11 public function definitions).
  2. test_zgen.zsh — real zsh run: sources the installed zgen.zsh inside a
                     private sandbox ZGEN_DIR and exercises the public CLI
                     surface (usage/rc, `zgen list`, `zgen saved`, unknown
                     subcommand, sandbox honouring).

zgen ships interpreted, architecture independent Zsh code, so executing it
with the build machine's zsh exercises exactly the bytes that are delivered to
the OHOS aarch64 target. If the machine has no zsh at all, the functional layer
is reported as skipped (warning) instead of being silently treated as passed.
"""
import os
import shlex
import shutil
import tempfile

from conan import ConanFile


class ZgenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["zgen"]
        share_dir = os.path.join(dep.package_folder, "share", "zgen")
        fpath_dir = os.path.join(dep.package_folder, "share", "zsh", "site-functions")
        script = os.path.join(share_dir, "zgen.zsh")

        layout_test = os.path.join(self.recipe_folder, "test.sh")
        self.run(f"sh {shlex.quote(layout_test)} "
                 f"{shlex.quote(share_dir)} {shlex.quote(fpath_dir)}")

        zsh = shutil.which("zsh")
        if zsh is None:
            self.output.warning(
                "zsh is not installed on this machine: the functional zsh layer "
                "is SKIPPED (not passed); layout/content assertions above ran")
            self.run(f"grep -q '^zgen() {{' {shlex.quote(script)}")
            return

        func_test = os.path.join(self.recipe_folder, "test_zgen.zsh")
        self.run(f"{shlex.quote(zsh)} -n {shlex.quote(script)}")

        # Private sandbox for ZGEN_DIR: never touch $HOME or the recipe tree.
        sandbox = tempfile.mkdtemp(prefix="zgen-sandbox-")
        try:
            self.run(f"ZGEN_DIR={shlex.quote(sandbox)} "
                     f"ZGEN_EXPECTED_DIR={shlex.quote(sandbox)} "
                     f"ZGEN_AUTOLOAD_COMPINIT=false "
                     f"{shlex.quote(zsh)} -f {shlex.quote(func_test)} "
                     f"{shlex.quote(script)}")
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)
        self.output.info("zgen functional zsh assertions passed")
