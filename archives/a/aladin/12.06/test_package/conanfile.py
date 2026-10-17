#!/usr/bin/env python3
"""Conan test_package — aladin 12.06 (L1 test).

Runs the upstream Java test classes (cds.astro.Test / cds.astro.TestRegion)
packaged inside Aladin.jar to verify the package works on HarmonyOS.

This is the L1 test in the five-level test system. CI runs this
automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class AladinTestConan(ConanFile):
    """L1 test for aladin — delegates to test.sh (Java smoke test)."""
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _is_jdk(java_home):
        return all(
            os.path.isfile(os.path.join(java_home, "bin", tool))
            for tool in ("java", "jar")
        )

    def _ensure_jdk(self):
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/usr/local/bishengjdk17",
            "/data/service/hnp/bishengjdk17",
        ]
        for candidate in candidates:
            if candidate and self._is_jdk(candidate):
                return candidate

        jdk_dir = os.path.join(self.build_folder, "bishengjdk17")
        os.makedirs(jdk_dir, exist_ok=True)
        get(
            self,
            url=(
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                "download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz"
            ),
            destination=jdk_dir,
        )
        candidates = [jdk_dir]
        candidates.extend(
            os.path.join(jdk_dir, entry)
            for entry in os.listdir(jdk_dir)
            if os.path.isdir(os.path.join(jdk_dir, entry))
        )
        for candidate in candidates:
            if self._is_jdk(candidate):
                return candidate
        raise ConanException(
            f"BiShengJDK 17 was downloaded but not found under {jdk_dir}"
        )

    def test(self):
        pkg_folder = self.dependencies["aladin"].package_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_script = os.path.join(self.source_folder, "test.sh")
        jdk = self._ensure_jdk()
        self.run(
            f'JAVA_HOME="{jdk}" "{bash}" "{test_script}" "{pkg_folder}"',
            env="conanrun",
        )
