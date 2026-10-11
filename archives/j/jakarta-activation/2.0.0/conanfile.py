#!/usr/bin/env python3
"""Conan recipe — jakarta-activation 2.0.0 (Java API jars, source compilation).

Downloads the upstream source tarball and compiles the Maven reactor's
`activation` + `activationapi` modules with Maven, packaging both produced JARs
into libexec/ (same house pattern as archives/j/jakarta-cdi-api 4.0.1 /
archives/j/jakarta-servlet-api 6.1.0).

Source: GitHub (jakartaee/jaf-api, tag 2.0.0)
License: EPL-2.0 (or GPL-2.0 with Classpath exception)
Build system: Maven 3.9.11 (binary fetched from repo1.maven.org, sha256-pinned;
              upstream ships no mvnw wrapper)
Upstream tests: NONE — the reactor ships no test sources at all
                (`find <src> -type d -name test` → empty; activation module has
                25 main sources / 0 test sources, activationapi has 0/0), so
                surefire has nothing to run. Upstream test pass rate is N/A;
                consumer verification is provided by test_package/.

Reactor note: root pom lists `activation` and `activationapi` (a `demo` module
only under a profile). `activation` produces jakarta.activation-2.0.0.jar
(the classes) and `activationapi` produces jakarta.activation-api-2.0.0.jar
(the API jar assembled by maven-dependency-plugin); building
`-pl activationapi -am` yields both and skips spec/demo.

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package/ compiles and runs a Java consumer program on-device
R38: library package (no commands.json needed)
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches

MAVEN_VERSION = "3.9.11"
MAVEN_URL = ("https://repo1.maven.org/maven2/org/apache/maven/apache-maven/"
             f"{MAVEN_VERSION}/apache-maven-{MAVEN_VERSION}-bin.tar.gz")
MAVEN_SHA256 = "4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac"


class JakartaActivationConan(ConanFile):
    name = "jakarta-activation"
    version = "2.0.0"
    description = ("Jakarta Activation 2.0 API (jakarta.activation: DataHandler, "
                   "DataSource, CommandMap, FileTypeMap, ActivationDataFlavor)")
    license = "EPL-2.0"
    homepage = "https://github.com/jakartaee/jaf-api"
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
                f"jakarta-activation does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.
        (same logic as archives/j/jakarta-cdi-api 4.0.1)

        注意：HNP 自带的 /data/service/hnp/bin/java 在部分环境下无法启动
        （VM init 失败），故优先 JAVA_HOME 与 ~/bishengjdk17（cmd-pkgs 安装）。"""
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
            # 完整性由下方 sha256 钉校验兜底
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
        # 构建完整 reactor（根 all + activation + activationapi）：jaf-api 的
        # reactor 很小（无 spec/tck 之类大模块），必须把 activation 模块一并
        # 编译，才能得到由**源码编译**出的类 jar；若只用 -pl activationapi -am，
        # maven-dependency-plugin 会改为从 Maven Central 解析现成的
        # jakarta.activation-2.0.0.jar（偏离"源码编译"口径）。
        self.run(
            f'bash -c "cd {self.source_folder} && sh {maven_home}/bin/mvn '
            f'clean package -B -DskipTests=false"',
            env="conanbuild",
        )

    def package(self):
        # 产物名不稳定：activation 模块输出 jakarta.activation-<version>.jar；
        # activationapi 由 pom 的 finalName 决定，实测为 jakarta.activation-api.jar
        # （无版本号）——故按目录取「非 sources/javadoc 的 jar」，避免写死文件名。
        for module in ("activation", "activationapi"):
            tdir = os.path.join(self.source_folder, module, "target")
            jars = [
                f for f in os.listdir(tdir)
                if f.endswith(".jar") and "sources" not in f and "javadoc" not in f
            ] if os.path.isdir(tdir) else []
            if not jars:
                raise ConanInvalidConfiguration(
                    f"Build artifact not found in {tdir}")
            for jar in jars:
                copy(self, jar, tdir,
                     os.path.join(self.package_folder, "libexec"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
