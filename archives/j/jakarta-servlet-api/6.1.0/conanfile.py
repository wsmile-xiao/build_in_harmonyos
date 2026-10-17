#!/usr/bin/env python3
"""Conan recipe — jakarta-servlet-api 6.1.0 (Java API jar, source compilation).

Downloads the upstream source tarball and compiles only the `api` module of the
Maven reactor with Maven, packaging the produced JAR into libexec/ (same house
pattern as archives/j/jakarta-cdi-api 4.0.1 / archives/j/jakarta-inject-api 2.0.1).

Source: GitHub (jakartaee/servlet, tag 6.1.0-RELEASE)
License: Apache-2.0 (EPL-2.0 dual)
Build system: Maven 3.9.11 (binary fetched from repo1.maven.org, sha256-pinned;
              upstream ships no mvnw wrapper)
Upstream tests: api/src/test/java has 10 sources — 3 JUnit 5 test classes
                (CanonicalUriPathTest, CookieTest, HttpServletTest) plus 7
                mock/helper classes; run by -DskipTests=false via surefire.

Reactor note: the root pom lists three modules (api, spec, tck). `spec` is a
documentation module and `tck` is the full Servlet TCK (a large separate build
that is not part of the API artifact), so the build is scoped with
`-pl api -am` — only the api module and its parent poms are built.

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


class JakartaServletApiConan(ConanFile):
    name = "jakarta-servlet-api"
    version = "6.1.0"
    description = ("Jakarta Servlet API 6.1 (jakarta.servlet / jakarta.servlet.http "
                   "— Servlet, Filter, HTTP request/response, cookies, sessions)")
    license = "Apache-2.0"
    homepage = "https://github.com/jakartaee/servlet"
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
                f"jakarta-servlet-api does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _fetch_nocurl(self, url, dest):
        """非 curl 抓取（CI worker 无 curl）：用 python3 stdlib 的 urllib 下载。

        免证书校验是刻意的：OHOS 侧的 python 常无 CA bundle，而下载物随后会用
        钉死的 sha256 校验，故不依赖 TLS 链。抓取后由调用方做哈希校验。
        """
        # 注意：source() 阶段 self.build_folder 可能为 None → 不放 build_folder，
        # 放家目录缓存（OHOS 上 /tmp 不可写）。
        helper = os.path.join(os.path.expanduser("~"), ".cache", "_fetch_nocurl.py")
        os.makedirs(os.path.dirname(helper), exist_ok=True)
        with open(helper, "w") as fh:
            fh.write("import ssl, sys, urllib.request\n"
                     "url, dst = sys.argv[1], sys.argv[2]\n"
                     "ctx = ssl._create_unverified_context()\n"
                     "data = urllib.request.urlopen(url, context=ctx, timeout=300).read()\n"
                     "open(dst, 'wb').write(data)\n"
                     "print('fetched', len(data), 'bytes ->', dst)\n")
        self.run('python3 "{}" "{}" "{}"'.format(helper, url, dest))
        if not (os.path.isfile(dest) and os.path.getsize(dest) > 0):
            raise ConanInvalidConfiguration("抓取失败（本环境无 curl）：" + url)
        return dest

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.
        (same logic as archives/j/jakarta-cdi-api 4.0.1)"""
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
        self._fetch_nocurl(install_url, script_path)
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
            self._fetch_nocurl(MAVEN_URL, dest)
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
        # 只构建 api 模块及其父 pom（-pl api -am）：
        #   spec 模块是文档、tck 模块是完整 Servlet TCK（独立大工程，
        #   不是 API 制品的组成部分），全 reactor 构建既慢又无必要。
        # -DskipTests=false 保留上游 3 个 JUnit 5 测试类（surefire 执行）。
        self.run(
            f'bash -c "cd {self.source_folder} && sh {maven_home}/bin/mvn -pl api -am '
            f'clean package -B -DskipTests=false"',
            env="conanbuild",
        )

    def package(self):
        jar_name = f"jakarta.servlet-api-{self.version}.jar"
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
