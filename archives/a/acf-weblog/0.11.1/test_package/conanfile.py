#!/usr/bin/env python3
"""Conan test_package — acf-weblog 0.11.1

L1 smoke test: verify the ACF app module files are installed in the package
(weblog*.lua controllers/model, *.lsp html templates, roles, menu, cron
script, png icons) and that each .lua file is syntactically valid Lua.

L0d gate: test() must call self.run() to execute a real test program —
the shell script test_weblog.sh verifies the installed module files.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AcfWeblogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["acf-weblog"].package_folder

        # L0d: run a real test program via self.run() — test_weblog.sh
        # verifies the installed ACF module files (incl. dangling symlinks
        # via -L, matching upstream cp -a semantics).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_weblog.sh")
        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )

        appdir = os.path.join(pkg_folder, "share", "acf", "app", "weblog")
        self.output.info(f"ACF app module dir: {appdir}")
        if not os.path.isdir(appdir):
            raise AssertionError(f"ACF app module dir not found: {appdir}")

        lua_files = sorted(glob.glob(os.path.join(appdir, "*.lua")))
        lsp_files = sorted(glob.glob(os.path.join(appdir, "*.lsp")))
        self.output.info(f"  Found {len(lua_files)} .lua files, {len(lsp_files)} .lsp templates")

        # cron 脚本 + png 图标(upstream install 的额外产物)
        cron = os.path.join(pkg_folder, "etc", "periodic", "daily", "weblogimport")
        if not os.path.isfile(cron):
            raise AssertionError(f"cron script not installed: {cron}")
        self.output.info(f"  [ok] cron script: {cron}")
        static = os.path.join(pkg_folder, "share", "acf", "www", "skins", "static")
        pngs = sorted(glob.glob(os.path.join(static, "*.png")))
        self.output.info(f"  Found {len(pngs)} png icons")

        # Lua syntax check for each .lua file (no host deps needed for parse)
        if can_run(self):
            lua_bin = _find_lua()
            if lua_bin:
                import subprocess
                for f in lua_files:
                    r = subprocess.run([lua_bin, "-p", f], capture_output=True, text=True, timeout=10)
                    if r.returncode != 0:
                        raise AssertionError(f"Lua syntax check failed for {f}: {r.stderr}")
                    self.output.info(f"  [ok] lua -p {os.path.basename(f)}")
            else:
                self.output.info("  lua interpreter not found, skipping -p syntax check (files verified present)")
        else:
            self.output.info("  Cross-compiling detected, skipping lua syntax check")


def _find_lua():
    import shutil
    for cand in ("lua", "lua5.4", "lua5.3", "lua5.2"):
        if shutil.which(cand):
            return cand
    return None
