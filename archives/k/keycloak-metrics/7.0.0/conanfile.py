#!/usr/bin/env python3
"""Conan recipe — keycloak-metrics 7.0.0 (Java SPI plugin for Keycloak).

Upstream: aerogear/keycloak-metrics-spi (tag 7.0.0, no v-prefix)
A Keycloak SPI plugin exposing Prometheus metrics endpoint
(EventListenerProvider + RealmResourceProvider). Built with Gradle 8.5
(wrapper), fat-jar shaded with prometheus simpleclient.

Package layout (follows archives/j/jackson-core/2.14.1 precedent):
  libexec/keycloak-metrics-spi-6.0.1-SNAPSHOT.jar   <- fat jar artifact
  licenses/LICENSE

Build chain:
  bishengjdk 17.0.13 (auto-install via cmd-pkgs, same as jackson-core)
  + Gradle 8.5 (pre-fetched zip, wrapper pointed at local file)
  + Maven Central deps (keycloak SPI jars are provided-scope, pulled from
    Maven Central at compile time; nothing keycloak-specific is bundled)

Upstream tests: 26 @Test methods (JUnit 4 + Mockito + system-stubs),
run in build() via "gradle test" — same as upstream Jenkinsfile
(./gradlew test).

R32: validate() checks settings.os in (Linux, OHOS)
     (settings declares full OHOS quadruple os/compiler/build_type/arch for
      the L0 quality gate, even though a pure-Java jar build ignores them)
R34: test_package loads the fat jar and verifies SPI registration files
     + prometheus shaded classes (real consumer-side verification)
R38: library package (no commands.json needed)
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class KeycloakMetricsConan(ConanFile):
    name = "keycloak-metrics"
    version = "7.0.0"
    description = (
        "Prometheus metrics endpoint as a Keycloak SPI plugin "
        "(EventListenerProvider + RealmResourceProvider)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/aerogear/keycloak-metrics-spi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    # 上游 gradle.properties 固定的 project.version（产物 jar 名）
    _jar_name = "keycloak-metrics-spi-6.0.1-SNAPSHOT.jar"
    # Gradle 发行版：官方 URL 在 CI worker 上 java 直连常超时，
    # 使用腾讯云镜像预下载后把 wrapper distributionUrl 指向本地文件
    _gradle_zip_url = "https://mirrors.cloud.tencent.com/gradle/gradle-8.5-all.zip"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"keycloak-metrics does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.

        Same chain as archives/j/jackson-core/2.14.1:
          1. JAVA_HOME environment variable
          2. ~/bishengjdk17 (standard cmd-pkgs path)
          3. java on PATH
          4. Auto-install via cmd-pkgs install-jdk.sh
        """
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

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

    def _prepare_gradle(self):
        """Fetch Gradle 8.5 zip via mirror and point the wrapper at it.

        上游 gradlew 脚本在本机 (busybox xargs 不剥引号) 会把 JVM 参数带引号
        传给 java 导致启动失败；且 wrapper 默认从 services.gradle.org 下载，
        java 直连该域超时。因此：
          1. curl 从腾讯镜像预下载 gradle-8.5-all.zip（curl 通镜像）
          2. 改 gradle-wrapper.properties 的 distributionUrl 为 file:// 本地路径
          3. 绕过 gradlew shell 脚本，直接 java -cp gradle-wrapper.jar 调
             GradleWrapperMain（wrapper 只负责解压/定位发行版，语义不变）
        """
        wrapper_props = os.path.join(
            self.source_folder, "gradle", "wrapper", "gradle-wrapper.properties"
        )
        zip_path = os.path.join(self.build_folder, "gradle-8.5-all.zip")

        if not os.path.isfile(zip_path):
            self.output.info("Downloading Gradle 8.5 from mirror ...")
            # conanbuild 环境的 PATH 里可能有带自签 CA 链问题的 curl
            # （本机实测 usr/local/bin/curl 8.19 报 error 60），故优先用
            # python urllib（走系统 CA，跨环境稳定），失败再退回 curl
            dl = (
                "import sys, urllib.request, shutil;\n"
                f"req = urllib.request.Request({self._gradle_zip_url!r})\n"
                "with urllib.request.urlopen(req, timeout=600) as r, "
                f"open({zip_path!r}, 'wb') as f:\n"
                "    shutil.copyfileobj(r, f)\n"
            )
            try:
                self.run(f'python3 -c "{dl}"')
            except Exception:
                self.output.info("python download failed, fallback to curl ...")
                self.run(
                    f'curl -fsSL --retry 3 -o "{zip_path}" "{self._gradle_zip_url}"'
                )

        # wrapper distributionUrl -> 本地 zip（file 协议）
        with open(wrapper_props, "a", encoding="utf-8") as f:
            f.write(
                "\n# PATCHED by conanfile: use pre-fetched local distribution\n"
                f"distributionUrl=file\\://{zip_path}\n"
            )
        # properties 文件后写的同名 key 生效（java.util.Properties 语义）
        self.output.info(f"wrapper distributionUrl -> file://{zip_path}")

    def _gradle(self, *tasks):
        """Invoke the gradle wrapper without the gradlew shell script."""
        wrapper_jar = os.path.join(
            self.source_folder, "gradle", "wrapper", "gradle-wrapper.jar"
        )
        task_args = " ".join(tasks)
        self.run(
            f'java -Dorg.gradle.appname=gradlew -classpath "{wrapper_jar}" '
            f"org.gradle.wrapper.GradleWrapperMain {task_args} --no-daemon",
            env="conanbuild",
        )

    def build(self):
        # 0) 应用测试 JVM 参数补丁（Mockito 自附加，CI worker 挂死问题）
        apply_conandata_patches(self)

        # 1) JDK 17（CI worker 可能未预装，自动通过 cmd-pkgs 安装）
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        # 本机 bishengjdk17 的 libjvm.so 依赖 libc++_shared.so（鸿蒙平台），
        # conan 缓存中若有 clang/libcxx 包则加入 LD_LIBRARY_PATH
        conan_libcxx = os.path.expanduser(
            "~/.conan2/p/clang86483f2566f6b/p/lib"
        )
        if os.path.isdir(conan_libcxx):
            os.environ["LD_LIBRARY_PATH"] = (
                conan_libcxx + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            )

        # 2) Gradle 8.5 发行版（镜像预下载 + wrapper 指向本地）
        self._prepare_gradle()

        # 3) 上游测试：gradle test —— 与上游 Jenkinsfile 一致（./gradlew test）
        #    26 个 @Test（PrometheusExporterTest 24 + MetricsFilterTest 2）
        #    R34/L1c: build() 必须包含上游测试执行
        self._gradle("test")

        # 4) 打包 fat jar（shade prometheus simpleclient）
        self._gradle("jar")

    def package(self):
        jar_path = os.path.join(
            self.source_folder, "build", "libs", self._jar_name
        )
        if not os.path.exists(jar_path):
            raise ConanInvalidConfiguration(
                f"Build artifact not found: {jar_path}. "
                "Ensure Gradle build completed successfully."
            )
        copy(
            self,
            self._jar_name,
            os.path.join(self.source_folder, "build", "libs"),
            os.path.join(self.package_folder, "libexec"),
        )
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
