from conan import ConanFile
import os


class JameicaH2DatabaseTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["jameica-h2database"].package_folder
        self.output.info(f"Testing package in: {pkg_folder}")

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
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            os.environ["JAVA_HOME"] = java_home
            os.environ["PATH"] = f"{java_home}/bin:{os.environ.get('PATH', '/usr/bin:/bin')}"

        script = os.path.join(self.source_folder, "check_h2.py")
        self.run(f'python3 "{script}" "{pkg_folder}"', env="conanrun")
