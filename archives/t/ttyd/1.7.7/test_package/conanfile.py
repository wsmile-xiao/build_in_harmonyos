#!/usr/bin/env python3
"""Conan test_package — ttyd 1.7.7 consumer test.

Runs the installed `ttyd` CLI: --version, --help, and a minimal local
web-terminal server startup (offline, no external network).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class TtydTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built ttyd consumers cannot run here.")
            return
        binary = os.path.join(
            self.dependencies["ttyd"].package_folder, "bin", "ttyd"
        )
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(f"ttyd binary not found: {binary}")
        if self.settings.os == "OHOS":
            self._sign_executables(binary)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")

    def _sign_executables(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS binary execution requires llvm-objcopy and binary-sign-tool"
            )
        temporary = f"{path}.signing"
        original_mode = os.stat(path).st_mode
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" -outFile "{temporary}" '
                "-selfSign 1"
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler)
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
        )
        return next((p for p in candidates if os.path.isfile(p)), "")
