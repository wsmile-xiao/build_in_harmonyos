#!/usr/bin/env python3
"""Conan test_package — acf-openssl 0.11.0

L1 smoke test: verify the ACF app module files are installed in the package
(openssl*.lua controllers/model, *.lsp html templates, roles, menu) and that
each .lua file is syntactically valid Lua.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AcfOpensslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["acf-openssl"].package_folder

        # L0d: run a real test program via self.run() — test_openssl.sh
        # verifies the installed ACF openssl module assets (controller/
        # model lua, roles/menu, html lsp templates, ca config).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_openssl.sh")
        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )

        appdir = os.path.join(pkg_folder, "share", "acf", "app", "openssl")
        etcdir = os.path.join(pkg_folder, "share", "acf", "openssl")

        self.output.info(f"ACF app module dir: {appdir}")
        if not os.path.isdir(appdir):
            raise AssertionError(f"ACF app module dir not found: {appdir}")

        lua_files = sorted(glob.glob(os.path.join(appdir, "*.lua")))
        lsp_files = sorted(glob.glob(os.path.join(appdir, "*.lsp")))
        self.output.info(f"  Found {len(lua_files)} .lua files, {len(lsp_files)} .lsp templates")

        # Core module files (from upstream Makefile APP_DIST)
        required = [
            os.path.join(appdir, "openssl-controller.lua"),
            os.path.join(appdir, "openssl-model.lua"),
            os.path.join(appdir, "openssl.roles"),
            os.path.join(appdir, "openssl.menu"),
            os.path.join(appdir, "openssl-html.lsp"),
            os.path.join(appdir, "openssl-read-html.lsp"),
        ]
        for f in required:
            if not os.path.isfile(f):
                raise AssertionError(f"Required module file missing: {f}")
            self.output.info(f"  [ok] {os.path.basename(f)}")

        # ETC_DIST
        cnf = os.path.join(etcdir, "openssl-ca-acf.cnf")
        if not os.path.isfile(cnf):
            raise AssertionError(f"Required config file missing: {cnf}")
        self.output.info(f"  [ok] openssl-ca-acf.cnf")

        # Lua syntax check for each .lua file (no host deps needed for parse)
        if can_run(self):
            lua_bin = "lua" if _lua_available() else None
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


def _lua_available():
    import shutil
    return shutil.which("lua") is not None or shutil.which("lua5.4") is not None or shutil.which("lua5.3") is not None
