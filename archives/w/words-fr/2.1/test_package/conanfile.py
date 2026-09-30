#!/usr/bin/env python3
"""AArch64 HarmonyOS Conan consumer for words-fr 2.1."""
import os
import platform
import shutil
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class WordsFrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "words-fr consumer validation requires the OHOS AArch64 (armv8) host profile"
            )

    def build(self):
        runner = Path(self.recipe_folder) / "test_harmony.py"
        output = Path(self.build_folder) / "build" / "test_words_fr"
        output.parent.mkdir(parents=True, exist_ok=True)
        compiler = os.environ.get("OHOS_CXX") or shutil.which("clang++")
        if not compiler:
            raise ConanInvalidConfiguration(
                "AArch64 consumer cross-build requires OHOS_CXX or clang++ in PATH"
            )
        command = [
            sys.executable,
            str(runner),
            "--target",
            "aarch64-linux-ohos",
            "--clang",
            compiler,
            "--output",
            str(output),
        ]
        sysroot = os.environ.get("OHOS_SYSROOT")
        if sysroot:
            command.extend(["--sysroot", sysroot])
        quoted = " ".join(f'"{part}"' if " " in part else part for part in command)
        self.run(quoted)

    def test(self):
        dependency = self.dependencies["words-fr"]
        package_root = Path(dependency.package_folder)
        for name in ("Copyright", "COPYING"):
            if not (package_root / "licenses" / name).is_file():
                raise AssertionError(f"packaged license missing: licenses/{name}")

        actual_machine = platform.machine().lower()
        actual_system = platform.system().lower()
        native_ohos_aarch64 = (
            can_run(self)
            and actual_machine in ("aarch64", "arm64")
            and actual_system in ("ohos", "openharmony", "harmonyos")
        )
        with VirtualRunEnv(self).vars().apply():
            # Always consume the Conan package with the Python data consumer on the
            # actual build machine; on a native OHOS/AArch64 runner, additionally
            # execute the HarmonyOS-compiled C++ consumer against the same package.
            script = Path(self.recipe_folder) / "test_words_fr.py"
            self.run(f'"{sys.executable}" "{script}"')
            self.run(
                f'"{sys.executable}" "{script}" --word-list '
                f'"{self.build_folder}/missing-words-fr" --expect-missing'
            )

            if native_ohos_aarch64:
                binary = Path(self.build_folder) / "build" / "test_words_fr"
                self.run(f'"{binary}" --require-ohos --expect-machine=aarch64')
                self.run(
                    f'"{binary}" --word-list="{self.build_folder}/missing-words-fr" '
                    "--expect-missing --require-ohos --expect-machine=aarch64"
                )
