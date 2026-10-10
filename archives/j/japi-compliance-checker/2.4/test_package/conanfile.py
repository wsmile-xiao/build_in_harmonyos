import os
import shutil

from conan import ConanFile


class JapiComplianceCheckerTestConan(ConanFile):
    """test_package for japi-compliance-checker.

    Exercises the installed CLI on real jars compiled on the fly with
    the JDK (R34): a v1/v2 library pair where v2 removes a public
    method must be flagged as binary incompatible, an identical pair
    must stay 100% compatible, and -dump must produce an API dump.
    """
    # L0p: OHOS profile requires all four settings (same as the main recipe)
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # JDK resolution (same policy as archives/j/jackson-core 2.14.1
        # test_package): the recipe's build() auto-installs bishengjdk to
        # ~/bishengjdk17 via cmd-pkgs when the host has no JDK.
        java_home = os.environ.get("JAVA_HOME", "")
        if not (java_home and
                os.path.isfile(os.path.join(java_home, "bin", "java"))):
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
        if not (java_home and
                os.path.isfile(os.path.join(java_home, "bin", "java"))):
            raise Exception(
                "JAVA_HOME not set and no JDK found in common locations. "
                "Set JAVA_HOME to a JDK 17+ installation path.")
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            os.path.join(java_home, "bin") + ":" +
            os.environ.get("PATH", ""))

        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
