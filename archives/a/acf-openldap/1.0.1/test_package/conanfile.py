#!/usr/bin/env python3
"""Conan test_package for acf-openldap."""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class AcfOpenldapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["acf-openldap"].package_folder
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.source_folder, "test_openldap.sh")
        self.run(f'"{shell}" "{script}" "{pkg_folder}"', env="conanrun")

        appdir = os.path.join(pkg_folder, "share", "acf", "app", "openldap")
        lua_files = sorted(glob.glob(os.path.join(appdir, "*.lua")))
        self.output.info(f"Found {len(lua_files)} Lua module file(s) in {appdir}")

        if can_run(self):
            lua_bin = _find_lua()
            if lua_bin:
                for path in lua_files:
                    if os.path.basename(lua_bin).startswith("luac"):
                        cmd = [lua_bin, "-p", path]
                    else:
                        cmd = [lua_bin, "-e", "assert(loadfile(arg[1]))", path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode != 0:
                        raise AssertionError(
                            f"Lua syntax check failed for {path}: {result.stderr}"
                        )
                    self.output.info(f"  [ok] lua syntax: {os.path.basename(path)}")
            else:
                self.output.info("Lua interpreter not found; file layout smoke already passed")


def _find_lua():
    for candidate in ("luac", "lua", "lua5.4", "lua5.3", "lua5.2"):
        path = shutil.which(candidate)
        if path:
            return path
    return None
