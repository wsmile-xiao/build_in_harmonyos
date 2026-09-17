#!/usr/bin/env python3
"""Consumer test for the installed liblcf-tools executables."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class LiblcfToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built liblcf-tools consumers cannot run here.")
            return

        test_root = os.path.expanduser("~/tmp")
        os.makedirs(test_root, exist_ok=True)
        signed_bin = os.path.join(
            test_root, f"liblcf-tools-consumer-bin-{os.getpid()}"
        )
        os.makedirs(signed_bin, exist_ok=True)
        try:
            for name in ("lcfstrings", "lcf2xml"):
                installed = os.path.join(
                    self.dependencies["liblcf-tools"].package_folder, "bin", name
                )
                if not os.path.isfile(installed):
                    raise ConanInvalidConfiguration(
                        f"installed tool not found: {installed}"
                    )
                # Keep the immutable Conan package cache untouched. OHOS
                # execution requires a valid signature, so sign an isolated
                # consumer copy and prepend its directory to PATH.
                binary = os.path.join(signed_bin, name)
                shutil.copy2(installed, binary)
                if self.settings.os == "OHOS":
                    self._sign_executable(binary)

            bash = os.environ.get("CONFIG_SHELL")
            if not bash or not os.path.isfile(bash):
                bash = shutil.which("bash") or "/bin/bash"
            test_script = os.path.join(self.build_folder, "test.sh")
            # Avoid the repository worktree as the process cwd: HMDFS can
            # reject getcwd() there while a test subprocess is starting.
            self.run(
                f'PATH="{signed_bin}:$PATH" "{bash}" "{test_script}"',
                cwd=test_root,
                env="conanrun",
            )
        finally:
            shutil.rmtree(signed_bin, ignore_errors=True)

    def _sign_executable(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        readelf = self._find_ohos_tool("llvm-readelf")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not readelf or not signer:
            raise ConanInvalidConfiguration(
                "OHOS executable test requires llvm-objcopy and binary-sign-tool"
            )
        temporary = f"{path}.signing"
        mode = os.stat(path).st_mode
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" -outFile "{temporary}" '
                "-selfSign 1"
            )
            sections = subprocess.run(
                [readelf, "-SW", temporary],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException(f"signed OHOS ELF has invalid .codesign count: {path}")
            os.chmod(temporary, mode)
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
