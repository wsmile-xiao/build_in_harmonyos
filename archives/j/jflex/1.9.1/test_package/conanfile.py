#!/usr/bin/env python3
"""Consumer test for the packaged JFlex scanner generator."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class JflexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

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

    @staticmethod
    def _emit_failure(reason):
        marker = {
            "executed": False,
            "passed": False,
            "command": reason,
            "discovered": 19,
            "passedCount": 0,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)

    def test(self):
        java_home = self._find_java()
        if not java_home:
            self._emit_failure("JDK not found")
            raise ConanInvalidConfiguration(
                "JFlex test_package requires java and javac"
            )

        package_folder = self.dependencies.build["jflex"].package_folder
        jar = os.path.join(
            package_folder, "libexec", "jflex-full-1.9.1.jar"
        )
        if not os.path.isfile(jar):
            self._emit_failure("packaged full JAR not found")
            raise ConanInvalidConfiguration(
                "Packaged JFlex full JAR is missing: {}".format(jar)
            )
        wrapper = os.path.join(package_folder, "libexec", "jflex.sh")
        if not os.path.isfile(wrapper):
            self._emit_failure("packaged JFlex wrapper not found")
            raise ConanInvalidConfiguration(
                "Packaged JFlex wrapper is missing: {}".format(wrapper)
            )

        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            os.path.join(java_home, "bin")
            + os.pathsep
            + os.environ.get("PATH", "")
        )
        script = os.path.join(self.source_folder, "test.sh")
        command = 'sh "{}" "{}" "{}" "{}" "{}"'.format(
            script,
            self._java_executable(java_home, "java"),
            self._java_executable(java_home, "javac"),
            self.source_folder,
            self.build_folder,
        )
        self.run(command, env="conanbuild")
