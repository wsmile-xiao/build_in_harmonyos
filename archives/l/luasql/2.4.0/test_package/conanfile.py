#!/usr/bin/env python3
"""Conan test_package for luasql 2.4.0 — verifies the SQLite3 driver works.

LuaSQL is a Lua extension module (.so), not a C library to link against.
The test uses the bundled lua binary to load the luasql.sqlite3 module
and performs database operations (create, insert, query).
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile


class LuasqlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def layout(self):
        # Simple layout — no CMake needed
        self.folders.build = "."
        self.folders.source = "."

    def _is_ohos(self):
        return self.settings.os == "OHOS"

    def _sign_elf(self, path):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(
                f'{objcopy} --remove-section .codesign "{path}" || true'
            )
            self.run(
                f'{sign_tool} sign -inFile "{path}" '
                f'-outFile "{path}.signed" -selfSign 1'
            )
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def build(self):
        # Copy the test Lua script (may be same file if layout uses same folder)
        test_script = os.path.join(self.source_folder, "test_luasql.lua")
        dest = os.path.join(self.build_folder, "test_luasql.lua")
        if os.path.exists(test_script):
            try:
                shutil.copy(test_script, dest)
            except shutil.SameFileError:
                pass

    def test(self):
        # R34: Test must substantively depend on the tested package
        pkg = self.dependencies["luasql"]
        pkg_dir = pkg.package_folder

        # Locate lua binary from the package
        lua_bin = os.path.join(pkg_dir, "bin", "lua")
        assert os.path.exists(lua_bin), f"lua binary not found at {lua_bin}"

        # Sign lua binary on OHOS if needed
        if self._is_ohos():
            self._sign_elf(lua_bin)

        # Set up LUA_CPATH to find the luasql module
        cpath = os.path.join(pkg_dir, "lib", "lua", "5.4", "?.so")
        test_script = os.path.join(self.build_folder, "test_luasql.lua")

        # Set environment variables directly
        old_cpath = os.environ.get("LUA_CPATH", "")
        os.environ["LUA_CPATH"] = f"{cpath};;{old_cpath}" if old_cpath else f"{cpath};;"

        try:
            self.run(f'"{lua_bin}" "{test_script}"')
        finally:
            if old_cpath:
                os.environ["LUA_CPATH"] = old_cpath
            else:
                os.environ.pop("LUA_CPATH", None)
