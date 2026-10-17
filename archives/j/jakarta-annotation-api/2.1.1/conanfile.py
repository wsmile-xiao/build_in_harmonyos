#!/usr/bin/env python3
"""Conan recipe — jakarta-annotation-api 2.1.1 (Java API jar, source compilation).

Downloads upstream source tarball, compiles the api Maven module with Maven
and packages the produced JAR into libexec/ (same house pattern as
archives/j/jackson-core 2.14.1 / archives/j/jakarta-inject-api 2.0.1).

Source: GitHub (jakartaee/common-annotations-api tag 2.1.1)
License: EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0
Build system: Maven 3.9.11 (binary fetched from repo1.maven.org, sha256-pinned;
              upstream repo ships no mvnw wrapper)
Upstream tests: none (API-only module, zero test sources — verified in tarball:
                no src/test directory, surefire reports "No tests to run")

Only the api module is built (`-f api/pom.xml`), mirroring upstream CI
(.travis.yml runs `mvn -f api/pom.xml verify -B -V`); the spec module is
asciidoc documentation only and produces no artifact we package.

No patches needed: upstream already pins maven-bundle-plugin 5.1.1 (newer bnd,
no ZipFile ConcurrentModificationException on JDK 17.0.13+), and javadoc
doclint passes on this JDK (verified locally: BUILD SUCCESS, jar +
sources + javadoc produced).

Maven dependency channel: routes `central` to the Aliyun mirror via a
generated settings.xml, retries 3 times, then falls back to direct Central
(same fix as archives/j/jakarta-validation-api 3.0.2 — CI runners hit
repo1.maven.org connection resets on direct access).

R32: validate() checks settings.os in ("Linux", "OHOS")
R34: test_package/ compiles and runs Java consumer programs on-device
R38: library package (no commands.json needed)
"""
import hashlib
import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, save


MAVEN_VERSION = "3.9.11"
MAVEN_URL = ("https://repo1.maven.org/maven2/org/apache/maven/apache-maven/"
             f"{MAVEN_VERSION}/apache-maven-{MAVEN_VERSION}-bin.tar.gz")
MAVEN_SHA256 = "4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac"


class JakartaAnnotationApiConan(ConanFile):
    name = "jakarta-annotation-api"
    version = "2.1.1"
    description = ("Jakarta Annotations API (jakarta.annotation) — common "
                   "annotations for the Jakarta EE platform")
    license = "EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0"
    homepage = "https://github.com/jakartaee/common-annotations-api"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R32/L0p：四项齐全（Java 包不消费 compiler/build_type，仅进 package_id）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jakarta-annotation-api does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.
        (same logic as archives/j/jackson-core 2.14.1)"""
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
        install_url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
                       "/releases/download/pkgs/install-jdk.sh")
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))
        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home
        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def _ensure_maven(self):
        """Fetch Apache Maven binary tarball from repo1.maven.org (sha256-pinned).
        Upstream repo ships no mvnw wrapper. Cached under ~/apache-maven-<ver>."""
        maven_home = os.path.expanduser("~/apache-maven-" + MAVEN_VERSION)
        mvn = os.path.join(maven_home, "bin", "mvn")
        if os.path.isfile(mvn):
            self.output.info("Maven found at " + maven_home)
            return maven_home
        self.output.info("Maven not found — downloading apache-maven-" + MAVEN_VERSION + " ...")
        dest = os.path.expanduser("~/apache-maven-" + MAVEN_VERSION + "-bin.tar.gz")
        try:
            self.run('curl -fsSL -o "{}" "{}"'.format(dest, MAVEN_URL))
        except ConanException:
            # OHOS 真机无 curl、python3 无 CA bundle：urllib 免证书下载，
            # 完整性由下方 sha256 钉校验兜底（真机实踩 2026-09-27，见 cdi 配方）
            self.output.warning("curl unavailable/failed — python3 urllib fallback (no TLS verify; sha256 pin below)")
            py = (
                "import ssl,urllib.request,shutil;"
                "ctx=ssl._create_unverified_context();"
                "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                "r=o.open('{}',timeout=300);f=open('{}','wb');"
                "shutil.copyfileobj(r,f);f.close();r.close()"
            ).format(MAVEN_URL, dest)
            self.run('python3 -c "{}"'.format(py))
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != MAVEN_SHA256:
            raise ConanInvalidConfiguration(
                "apache-maven tarball sha256 mismatch: " + h.hexdigest()
            )
        os.makedirs(maven_home, exist_ok=True)
        self.run('tar -xzf "{}" -C "{}" --strip-components=1'.format(dest, maven_home))
        if not os.path.isfile(mvn):
            raise ConanInvalidConfiguration("Maven extraction failed: " + mvn)
        self.output.info("Maven installed at " + maven_home)
        return maven_home

    def build(self):
        java_home = self._ensure_java()
        maven_home = self._ensure_maven()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + ":" +
                              os.path.join(maven_home, "bin") + ":" +
                              os.environ.get("PATH", ""))
        # Route `central` to the Aliyun mirror (China CDN) via settings.xml,
        # retry up to 3 times, then fall back to direct Central
        # (jakarta-validation-api 先例：CI 直连 repo1.maven.org 报
        # Connection reset；镜像+重试+兜底三保险)。
        settings_xml = os.path.join(self.build_folder, "maven-settings.xml")
        save(self, settings_xml,
             "<settings><mirrors><mirror>"
             "<id>aliyun-central</id>"
             "<url>https://maven.aliyun.com/repository/central</url>"
             "<mirrorOf>central</mirrorOf>"
             "</mirror></mirrors></settings>")
        # HMDFS 禁 shebang 直接 exec（mvn 脚本报 bad interpreter）→ 显式 sh 调用
        mvn = f"sh {maven_home}/bin/mvn"
        built = False
        for attempt in range(3):
            try:
                self.run(
                    f'bash -c "cd {self.source_folder} && {mvn} -s {settings_xml} -f api/pom.xml clean package -B -DskipTests=false"',
                    env="conanbuild",
                )
                built = True
                break
            except ConanException:
                self.output.warn(
                    f"Maven build attempt {attempt + 1}/3 failed, retrying after 20s...")
                time.sleep(20)
        if not built:
            # Fallback: direct Central without mirror settings
            self.run(
                f'bash -c "cd {self.source_folder} && {mvn} -f api/pom.xml clean package -B -DskipTests=false"',
                env="conanbuild",
            )

    def package(self):
        jar_name = f"jakarta.annotation-api-{self.version}.jar"
        jar_path = os.path.join(self.source_folder, "api", "target", jar_name)
        if not os.path.exists(jar_path):
            raise ConanInvalidConfiguration(f"Build artifact not found: {jar_path}")
        copy(self, jar_name, os.path.join(self.source_folder, "api", "target"),
             os.path.join(self.package_folder, "libexec"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
