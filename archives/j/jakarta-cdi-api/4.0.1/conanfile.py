#!/usr/bin/env python3
"""Conan recipe — jakarta-cdi-api 4.0.1 (Java API jars, source compilation).

Downloads upstream source tarball, compiles the Maven reactor with Maven and
packages the two produced JARs into libexec/ (same house pattern as
archives/j/jackson-core 2.14.1 / archives/j/jakarta-inject-api 2.0.1).

Source: GitHub (jakartaee/cdi tag 4.0.1)
License: Apache-2.0
Build system: Maven 3.9.11 (binary fetched from repo1.maven.org, sha256-pinned;
              upstream repo ships no mvnw wrapper)
Upstream tests: 56 TestNG test methods, all in the api module (33 test sources;
                lang-model/spec modules ship no test sources) — run by
                `mvn clean package -B -DskipTests=false` via maven-surefire

The reactor has three modules (spec: pom-only doc module, lang-model: jar,
api: jar); the root pom's modules are built in one `mvn clean package` run.
Two JARs are packaged: api/target/jakarta.enterprise.cdi-api-<v>.jar and
lang-model/target/jakarta.enterprise.lang-model-<v>.jar (api depends on
lang-model, so consumers need both on the classpath).

Patches (JDK 17.0.13+ compatibility, applied via conandata):
  0001-jdk17-doclint.patch — maven-javadoc-plugin doclint:none
    (heading-sequence doclint error introduced in newer JDK 17 patch releases)
    The cdi reactor already pins maven-bundle-plugin 5.1.2, so the
    bnd/ZipFile incompatibility that jakarta-inject-api hit does not apply.

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package/ compiles and runs a Java consumer program on-device
R38: library package (no commands.json needed)
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches

MAVEN_VERSION = "3.9.11"
MAVEN_URL = ("https://repo1.maven.org/maven2/org/apache/maven/apache-maven/"
             f"{MAVEN_VERSION}/apache-maven-{MAVEN_VERSION}-bin.tar.gz")
MAVEN_SHA256 = "4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac"


class JakartaCdiApiConan(ConanFile):
    name = "jakarta-cdi-api"
    version = "4.0.1"
    description = ("Jakarta Contexts and Dependency Injection API "
                   "(jakarta.enterprise.cdi-api + jakarta.enterprise.lang-model)")
    license = "Apache-2.0"
    homepage = "https://github.com/jakartaee/cdi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R32/L0p：四项齐全（Java 包不消费 compiler/build_type，仅进 package_id）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jakarta-cdi-api does not support OS: {self.settings.os}"
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
            # 完整性由下方 sha256 钉校验兜底（真机实踩 2026-09-27）
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
        apply_conandata_patches(self)
        java_home = self._ensure_java()
        maven_home = self._ensure_maven()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + ":" +
                              os.path.join(maven_home, "bin") + ":" +
                              os.environ.get("PATH", ""))
        # Root reactor (spec + lang-model + api): `package` compiles classes +
        # javadoc + sources + jar per module and runs the 56 upstream TestNG
        # tests of the api module (-DskipTests=false kept for R34/L1c parity
        # with the Maven house pattern).
        # OHOS 真机: spec-doc 模块的 asciidoctor-maven-plugin (JRuby) 在
        # generate-pdf-doc 时 gemspec 解析失败 (ENOENT concurrent-ruby)；
        # 该模块纯文档产物、不打包，真机跳过文档生成，Linux CI 仍全量构建。
        skip_doc = " -Dasciidoctor.skip=true" if self.settings.os == "OHOS" else ""
        self.run(
            f'bash -c "cd {self.source_folder} && sh {maven_home}/bin/mvn clean package -B -DskipTests=false{skip_doc}"',
            env="conanbuild",
        )

    def package(self):
        jars = [
            ("api", f"jakarta.enterprise.cdi-api-{self.version}.jar"),
            ("lang-model", f"jakarta.enterprise.lang-model-{self.version}.jar"),
        ]
        for module, jar_name in jars:
            jar_path = os.path.join(self.source_folder, module, "target", jar_name)
            if not os.path.exists(jar_path):
                raise ConanInvalidConfiguration(f"Build artifact not found: {jar_path}")
            copy(self, jar_name, os.path.join(self.source_folder, module, "target"),
                 os.path.join(self.package_folder, "libexec"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
