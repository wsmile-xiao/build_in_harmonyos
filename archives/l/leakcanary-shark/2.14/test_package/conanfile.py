# conanfile.py — test_package for leakcanary-shark 2.14
# Consumer-side API verification: compiles and runs a Java test program that
# drives the shark heap-analysis pipeline (HprofWriter/Hprof/HeapAnalyzer),
# the ProguardMapping reader and SharkLog from the packaged JARs.
# Meets R34 substantive verification requirement.

from conan import ConanFile
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["leakcanary-shark"].package_folder
        self.output.info(f"Testing package in: {pkg_folder}")

        # Resolve JAVA_HOME: prefer env, then common JDK install paths
        java_home = os.environ.get("JAVA_HOME")
        if not (java_home and os.path.isfile(os.path.join(java_home, "bin", "java"))):
            for candidate in (
                os.path.expanduser("~/bishengjdk17"),
                os.path.expanduser("~/usr/local/bishengjdk17"),
                "/storage/Users/currentUser/bishengjdk17",
                "/usr/lib/jvm/bishengjdk-17",
                "/usr/lib/jvm/java-17-openjdk",
            ):
                if os.path.isfile(os.path.join(candidate, "bin", "java")):
                    java_home = candidate
                    break
        if not (java_home and os.path.isfile(os.path.join(java_home, "bin", "java"))):
            raise Exception(
                "JAVA_HOME not set and no JDK found in common locations. "
                "Set JAVA_HOME to a JDK 17+ installation path."
            )
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = f"{java_home}/bin:{os.environ.get('PATH', '/usr/bin:/bin')}"

        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'bash "{script}" "{pkg_folder}"', env="conanrun")
