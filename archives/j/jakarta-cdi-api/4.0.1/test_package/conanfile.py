from conan import ConanFile
import os


class JakartaCdiApiTest(ConanFile):
    # L0p：OHOS profile 要求 settings 四项齐全（与主配方一致；仅进 package_id）
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["jakarta-cdi-api"].package_folder
        self.output.info(f"Testing package in: {pkg_folder}")

        # 解析 JAVA_HOME：优先环境变量，其次检测常见 JDK 安装路径
        # build() 阶段可能已通过 cmd-pkgs 自动安装 bishengjdk 到 ~/bishengjdk17
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
            raise Exception(
                "JAVA_HOME not set and no JDK found in common locations. "
                "Set JAVA_HOME to a JDK 17+ installation path."
            )
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            f"{java_home}/bin:{os.environ.get('PATH', '/usr/bin:/bin')}"
        )

        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'bash "{script}" "{pkg_folder}"', env="conanrun")
