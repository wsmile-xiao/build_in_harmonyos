#!/usr/bin/env python3
"""Conan recipe — jackson-core 2.14.1 (Java source compilation).

Downloads upstream source tarball, compiles with Maven (./mvnw),
runs upstream JUnit tests in build(), and packages the resulting JAR.

Source: GitHub (FasterXML/jackson-core tag jackson-core-2.14.1)
License: Apache-2.0
Build system: Maven (via mvnw wrapper)
Upstream tests: 104 @Test methods (JUnit 5 + JUnit Vintage)

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package calls jackson-core API (JsonFactory/JsonParser)
R38: library package (no commands.json needed)
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class JacksonCoreConan(ConanFile):
    name = "jackson-core"
    version = "2.14.1"
    description = "Jackson core: low-level streaming JSON parser/generator library"
    license = "Apache-2.0"
    homepage = "https://github.com/FasterXML/jackson-core"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jackson-core does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.

        Checks (in order):
          1. JAVA_HOME environment variable
          2. ~/bishengjdk17 and ~/usr/local/bishengjdk17 (standard cmd-pkgs paths)
          3. java on PATH
          4. Auto-install via cmd-pkgs install-jdk.sh (CI workers may lack JDK)

        Returns the JAVA_HOME path. Raises ConanInvalidConfiguration if all fail.
        """
        # 1. Check JAVA_HOME env
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        # 2. Check common cmd-pkgs install locations
        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        # 3. Try to find java in PATH
        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

        # 4. Auto-install bishengjdk 17.0.13 via cmd-pkgs
        self.output.info("Java not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh"
        )
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))

        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home

        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def build(self):
        apply_conandata_patches(self)

        # 确保 JDK 17+ 可用（CI worker 可能未预装，自动通过 cmd-pkgs 安装）
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        # 赋予 mvnw 执行权限
        mvnw = os.path.join(self.source_folder, "mvnw")
        if os.path.exists(mvnw):
            os.chmod(mvnw, os.stat(mvnw).st_mode | stat.S_IEXEC)

        # Maven 编译 + 运行上游 JUnit 测试（104 个 @Test 方法）+ 打包 JAR
        # package 阶段：test 在 package 前自动执行（运行上游测试），并产出 target/jackson-core-2.14.1.jar
        # -B: 批处理模式（无交互）
        # -DskipTests=false: 确保运行测试
        # R34/L1c: build() 必须包含上游测试执行
        self.run(
            f'bash -c "cd {self.source_folder} && ./mvnw clean package -B '
            f'-DskipTests=false"',
            env="conanbuild",
        )

    def package(self):
        # 打包编译产物 JAR
        jar_name = f"jackson-core-{self.version}.jar"
        jar_path = os.path.join(self.source_folder, "target", jar_name)
        if os.path.exists(jar_path):
            copy(self, jar_name, os.path.join(self.source_folder, "target"),
                 os.path.join(self.package_folder, "libexec"))
        else:
            raise ConanInvalidConfiguration(
                f"Build artifact not found: {jar_path}. "
                "Ensure Maven build completed successfully."
            )

        # 打包 LICENSE
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
