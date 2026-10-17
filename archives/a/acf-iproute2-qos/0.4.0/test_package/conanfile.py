#!/usr/bin/env python3
"""Conan test_package — acf-iproute2-qos 0.4.0

L1 smoke test: verify the ACF app module files are installed in the package
(qos*.lua controllers/model, *.lsp html templates, roles, menu) and that
each .lua file is syntactically valid Lua.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AcfIproute2QosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["acf-iproute2-qos"].package_folder

        # L0d: run a real test program via self.run() — test_iproute2_qos.sh
        # verifies the installed ACF qos module assets (controller/model lua,
        # roles/menu, html lsp symlink templates, etc config).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_iproute2_qos.sh")
        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )

        appdir = os.path.join(pkg_folder, "share", "acf", "app", "qos")

        self.output.info(f"ACF app module dir: {appdir}")
        if not os.path.isdir(appdir):
            raise AssertionError(f"ACF app module dir not found: {appdir}")

        lua_files = sorted(glob.glob(os.path.join(appdir, "*.lua")))
        lsp_files = sorted(glob.glob(os.path.join(appdir, "*.lsp")))
        self.output.info(f"  Found {len(lua_files)} .lua files, {len(lsp_files)} .lsp templates")

        # Core module files (from upstream Makefile APP_DIST: qos*)
        # 注意: qos-expert-html.lsp / qos-status-html.lsp 在上游 tarball 中
        # 是指向 acf-core 共享模板(filedetails-html.lsp/status-html.lsp)的符号链接,
        # 目标由 ACF 框架宿主运行时提供,本包内为悬空链接 → 用 lexists 检查
        # (不解析链接目标),与上游 cp -a 复制链接本身的语义一致
        required = [
            os.path.join(appdir, "qos-controller.lua"),
            os.path.join(appdir, "qos-model.lua"),
            os.path.join(appdir, "qos.roles"),
            os.path.join(appdir, "qos.menu"),
            os.path.join(appdir, "qos-details-html.lsp"),
            os.path.join(appdir, "qos-expert-html.lsp"),
            os.path.join(appdir, "qos-status-html.lsp"),
        ]
        for f in required:
            if not os.path.lexists(f):
                raise AssertionError(f"Required module file missing: {f}")
            extra = ""
            if os.path.islink(f):
                extra = f" (symlink -> {os.readlink(f)})"
            self.output.info(f"  [ok] {os.path.basename(f)}{extra}")

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
