#!/usr/bin/env python3
"""Conan recipe for the ACF standard modules targeting Lua 5.2."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AcfLibLua52Conan(ConanFile):
    name = "acf-lib-lua5.2"
    version = "0.11.1"
    description = "Lua 5.2 standard modules for the Alpine Configuration Framework"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-lib"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    # L0p 门禁：OHOS profile 需要全部四项 settings（os/compiler/build_type/arch），
    # 缺 compiler/build_type 会被 CI 拦截（与 cfgv 的 L0p 修复一致）。
    settings = "os", "compiler", "build_type", "arch"

    _lua_root = os.path.join("share", "lua", "5.2")
    _modules = (
        "apk.lua",
        "date.lua",
        "db.lua",
        "format.lua",
        "fs.lua",
        "html.lua",
        "processinfo.lua",
        "validator.lua",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.2.4")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-lib-lua5.2 does not support os={self.settings.os}"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="acf-lib-v0.11.1.tar.gz",
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        root = Path(self.source_folder)
        actual = sorted(path.name for path in root.glob("*.lua") if path.is_file())
        expected = sorted(self._modules)
        if actual != expected:
            raise ConanInvalidConfiguration(
                f"Unexpected ACF Lua module inventory: expected {expected}, found {actual}"
            )
        for module in self._modules:
            if (root / module).stat().st_size == 0:
                raise ConanInvalidConfiguration(f"Empty upstream Lua module: {module}")

    def package(self):
        module_root = os.path.join(self.package_folder, self._lua_root)
        copy(
            self,
            "*.lua",
            src=self.source_folder,
            dst=os.path.join(module_root, "acf"),
            keep_path=False,
        )
        # Upstream installs compatibility links such as format.lua -> acf/format.lua.
        # Copies provide the same module names without relying on symlink privileges
        # when the target package is produced on a Windows-hosted OHOS toolchain.
        copy(
            self,
            "*.lua",
            src=self.source_folder,
            dst=module_root,
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = [self._lua_root]
        root = os.path.join(self.package_folder, self._lua_root)
        lua_path = ";".join(
            (
                os.path.join(root, "?.lua"),
                os.path.join(root, "?", "init.lua"),
            )
        )
        self.buildenv_info.define("LUA_PATH", lua_path + ";;")
        self.runenv_info.define("LUA_PATH", lua_path + ";;")
