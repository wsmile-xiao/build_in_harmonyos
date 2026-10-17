#!/usr/bin/env python3
"""Consumer test for the packaged t-digest JAR."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class TDigestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _emit_failure(reason):
        marker = {
            "executed": False,
            "passed": False,
            "command": reason,
            "discovered": 14,
            "passedCount": 0,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)

    def test(self):
        pkg_folder = self.dependencies["t-digest"].package_folder
        self.output.info("Testing package in: {}".format(pkg_folder))

        java_home = os.environ.get("JAVA_HOME")
        if not (java_home and os.path.isfile(os.path.join(java_home, "bin", "java"))):
            for candidate in (
                os.path.expanduser("~/bishengjdk17"),
                os.path.expanduser("~/usr/local/bishengjdk17"),
                "/usr/lib/jvm/bishengjdk-17",
                "/usr/lib/jvm/java-17-openjdk",
                "/usr/lib/jvm/java-17-openjdk-arm64",
            ):
                if os.path.isfile(os.path.join(candidate, "bin", "java")):
                    java_home = candidate
                    break
        if not (java_home and os.path.isfile(os.path.join(java_home, "bin", "java"))):
            java_on_path = shutil.which("java")
            if java_on_path:
                java_home = os.path.dirname(
                    os.path.dirname(os.path.realpath(java_on_path))
                )
        if not (java_home and os.path.isfile(os.path.join(java_home, "bin", "java"))):
            self._emit_failure("JDK not found")
            raise ConanInvalidConfiguration(
                "t-digest test_package requires java and javac. "
                "Set JAVA_HOME to a JDK 17+ installation path."
            )
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            "{}/bin:{}".format(java_home, os.environ.get("PATH", "/usr/bin:/bin"))
        )

        jar = os.path.join(pkg_folder, "libexec", "t-digest-3.0.jar")
        if not os.path.isfile(jar):
            self._emit_failure("packaged t-digest JAR not found")
            raise ConanInvalidConfiguration(
                "Packaged t-digest JAR is missing: {}".format(jar)
            )

        script = os.path.join(self.source_folder, "test.sh")
        # True machine provides only /bin/sh (no bash); HMBS injects
        # SHELL=/bin/sh. Invoke via sh for portability.
        sh = os.environ.get("SHELL") or shutil.which("sh") or "/bin/sh"
        self.run('\"{}\" \"{}\" \"{}\"'.format(sh, script, pkg_folder), env="conanrun")
