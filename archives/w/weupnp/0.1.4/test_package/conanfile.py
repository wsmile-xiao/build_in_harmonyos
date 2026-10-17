#!/usr/bin/env python3
"""Consumer test for the packaged weupnp JAR (Conan L1).

Compiles and runs TestWeupnp.java against the JAR installed by the weupnp
package, so the test depends on the real artifact (R34) instead of re-building
the sources. Includes OHOS-specific cases (see TestWeupnp.java / MANIFEST.yml).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class WeupnpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _java_executable(java_home, tool):
        return os.path.join(java_home, "bin", tool)

    def _find_java(self):
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/storage/Users/currentUser/usr/local/bishengjdk17",
            "/usr/local/bishengjdk17",
            "/usr/lib/jvm/bishengjdk-17",
            "/usr/lib/jvm/java-17-openjdk",
            "/usr/lib/jvm/java-17-openjdk-arm64",
        ]
        for candidate in candidates:
            if candidate and all(
                os.path.isfile(self._java_executable(candidate, tool))
                for tool in ("java", "javac")
            ):
                return candidate

        java_on_path = shutil.which("java")
        javac_on_path = shutil.which("javac")
        if java_on_path and javac_on_path:
            return os.path.dirname(
                os.path.dirname(os.path.realpath(java_on_path))
            )
        return None

    def test(self):
        java_home = self._find_java()
        if not java_home:
            raise ConanInvalidConfiguration(
                "weupnp test_package requires both java and javac on PATH "
                "or a JDK under ~/bishengjdk17"
            )

        package_folder = self.dependencies["weupnp"].package_folder
        jar = os.path.join(package_folder, "libexec", "weupnp-0.1.4.jar")
        if not os.path.isfile(jar):
            raise ConanInvalidConfiguration(
                "packaged weupnp JAR is missing: {}".format(jar)
            )

        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            os.path.join(java_home, "bin")
            + os.pathsep
            + os.environ.get("PATH", "")
        )

        script = os.path.join(self.source_folder, "test.sh")
        # Keep every build product of the test run out of the recipe tree:
        # test.sh creates this folder and removes it again on exit.
        work_dir = os.path.join(self.build_folder, "weupnp-test-work")
        command = 'sh "{}" "{}" "{}" "{}" "{}" "{}"'.format(
            script,
            self._java_executable(java_home, "java"),
            self._java_executable(java_home, "javac"),
            jar,
            self.source_folder,
            work_dir,
        )
        self.run(command, env="conanbuild")
