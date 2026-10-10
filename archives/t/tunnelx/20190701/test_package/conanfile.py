#!/usr/bin/env python3
"""Conan test_package — tunnelx 20190701 (Conan L1 test).

Verifies the installed package from a consumer's point of view on HarmonyOS:

* ``test.sh`` performs the actual checks (package layout, JAR manifest,
  bundled resources, upstream GUI entry reachability, OHOS launcher, OHOS
  probe with java.io.tmpdir redirection);
* ``TunnelOhosProbe.java`` is compiled by ``test.sh`` with the consumer JVM
  and asserted in package ``Tunnel`` (upstream ships package-private classes
  only).

Upstream itself ships no automated test harness — see test_package/MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class TunnelxTestConan(ConanFile):
    """L1 test for tunnelx — delegates to test.sh (Java smoke + OHOS test)."""
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _JDK_URL = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                "releases/download/pkgs/"
                "bishengjdk-17.0.13-ohos-aarch64.tar.gz")

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _is_jdk(java_home):
        return bool(java_home) and all(
            os.path.isfile(os.path.join(java_home, "bin", tool))
            for tool in ("java", "javac", "jar")
        )

    def _ensure_jdk(self):
        """Reuse the platform BiSheng JDK, installing it when the CI worker
        does not provide one (same channel as the recipe itself)."""
        for candidate in (os.environ.get("JAVA_HOME", ""),
                          os.path.expanduser("~/bishengjdk17"),
                          os.path.expanduser("~/usr/local/bishengjdk17"),
                          "/usr/local/bishengjdk17",
                          "/data/service/hnp/bishengjdk17"):
            if self._is_jdk(candidate):
                return candidate

        jdk_dir = os.path.join(self.build_folder, "bishengjdk17")
        os.makedirs(jdk_dir, exist_ok=True)
        get(self, url=self._JDK_URL, destination=jdk_dir)
        candidates = [jdk_dir]
        candidates.extend(
            os.path.join(jdk_dir, entry)
            for entry in sorted(os.listdir(jdk_dir))
            if os.path.isdir(os.path.join(jdk_dir, entry))
        )
        for candidate in candidates:
            if self._is_jdk(candidate):
                return candidate
        raise ConanException(
            f"BiShengJDK 17 downloaded but no JDK layout found under {jdk_dir}")

    def test(self):
        pkg_folder = self.dependencies["tunnelx"].package_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_script = os.path.join(self.source_folder, "test.sh")
        jdk = self._ensure_jdk()
        self.run(f'JAVA_HOME="{jdk}" "{bash}" "{test_script}" "{pkg_folder}"',
                 env="conanrun")
