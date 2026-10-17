#!/usr/bin/env python3
"""test_package for lua-stringy — verifies string operations work.

Uses the packaged lua binary to load stringy.so and run assertions
from the upstream test suite.
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile


class LuaStringyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def generate(self):
        pass

    def _is_ohos(self):
        return self.settings.os == "OHOS"

    def _sign_elf(self, path):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            # .codesign section may not exist on unsigned binaries
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
        # Copy test script to build folder
        for f in ["test_stringy.lua", "test.sh"]:
            src = os.path.join(self.source_folder, f)
            dst = os.path.join(self.build_folder, f)
            if os.path.exists(src):
                try:
                    shutil.copy(src, dst)
                except shutil.SameFileError:
                    pass
        os.chmod(os.path.join(self.build_folder, "test.sh"), 0o755)

    def test(self):
        # R34: Test must substantively depend on the tested package
        pkg = self.dependencies["lua-stringy"]
        pkg_dir = pkg.package_folder

        # Locate lua binary from the package
        lua_bin = os.path.join(pkg_dir, "bin", "lua")
        assert os.path.exists(lua_bin), (
            f"lua binary not found at {lua_bin}"
        )

        # Sign lua binary on OHOS if needed
        if self._is_ohos():
            self._sign_elf(lua_bin)

        # Set env for test.sh
        os.environ["LUA_STRINGY_ROOT"] = pkg_dir
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        test_sh = os.path.join(self.build_folder, "test.sh")
        self.run(f'"{bash}" "{test_sh}"', env="conanrun")
