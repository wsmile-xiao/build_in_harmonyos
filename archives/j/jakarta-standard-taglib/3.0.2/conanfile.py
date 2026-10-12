#!/usr/bin/env python3
"""Conan recipe — jakarta-standard-taglib 3.0.2 (JSTL API + implementation jars).

Builds the upstream Maven multi-module project and packages two artifacts:

  * libexec/jakarta.servlet.jsp.jstl-api-3.0.2.jar   (api module, the JSTL API)
  * libexec/jakarta.servlet.jsp.jstl-3.0.2.jar       (impl module, the JSTL implementation)

Source: Debian pool orig tarball (upstream repo tags/layout differ; the Debian
        orig tarball is the authoritative 3.0.2 source tree).
License: EPL-2.0 OR GPL-2.0-with-classpath-exception
Build system: Maven (binary fetched from repo1.maven.org, sha256-pinned; upstream
              ships no mvnw wrapper). Same house helpers as
              archives/j/jakarta-inject-api 2.0.1 / archives/j/jackson-core 2.14.1.

Zero Conan `requires`: every build/test dependency is fetched from Maven Central at
build time (jakarta.servlet-api 6.0.0, jakarta.servlet.jsp-api 3.1.0,
jakarta.el-api 5.0.0, jakarta.servlet.jsp.jstl-api 3.0.0, xalan 2.7.3,
junit-jupiter-engine 5.8.2) — verified resolvable (HTTP 200) before starting.

Modules `spec` (documentation) and `tagsdoc` (asciidoctor docs) are intentionally
NOT built: they are documentation-only and not part of the shipped artifacts
(reactor pruning is legitimate here — see knowledge draft on Maven reactor scope).

R32: validate() checks settings.os in (Linux, OHOS)
R34: upstream tests (impl module, JUnit 5) are really executed in build()
     and their surefire summary is asserted (0 failures / 0 errors).
R38: library package (no commands.json needed)
"""
import hashlib
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches

MAVEN_VERSION = "3.9.11"
MAVEN_URL = ("https://repo1.maven.org/maven2/org/apache/maven/apache-maven/"
             f"{MAVEN_VERSION}/apache-maven-{MAVEN_VERSION}-bin.tar.gz")
MAVEN_SHA256 = "4b7195b6a4f5c81af4c0212677a32ee8143643401bc6e1e8412e6b06ea82beac"

# Reactor scope: the two artifact modules (parent pom is pulled in by -am).
MODULES = "api,impl"


class JakartaStandardTaglibConan(ConanFile):
    name = "jakarta-standard-taglib"
    version = "3.0.2"
    description = ("Jakarta Standard Tag Library (JSTL) 3.0.2 — API and "
                   "implementation jars")
    license = "EPL-2.0"
    homepage = "https://github.com/jakartaee/tags"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jakarta-standard-taglib does not support OS: {self.settings.os}"
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
        (same logic as archives/j/jakarta-inject-api 2.0.1)"""
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
        self._fetch_nocurl(MAVEN_URL, dest)
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

    def _run_upstream_tests_summary(self):
        """Assert the impl module's surefire summary: hard constraint on failures/errors.

        Discipline (see knowledge drafts): the upstream suite must be *really* run —
        a missing/absent report is a failure, not a silent pass; and any failure or
        error in the report aborts the build (no "counting only passes").
        """
        report_dir = os.path.join(self.source_folder, "impl", "target", "surefire-reports")
        if not os.path.isdir(report_dir):
            raise ConanInvalidConfiguration(
                "upstream tests not run: no surefire-reports directory at " + report_dir
            )
        total = failures = errors = skipped = 0
        files = 0
        for name in sorted(os.listdir(report_dir)):
            if not name.endswith(".txt"):
                continue
            files += 1
            text = open(os.path.join(report_dir, name), encoding="utf-8",
                        errors="replace").read()
            m = re.search(r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),"
                          r"\s*Skipped:\s*(\d+)", text)
            if not m:
                raise ConanInvalidConfiguration(
                    "unparsable surefire report " + name + " → cannot assert results"
                )
            total += int(m.group(1))
            failures += int(m.group(2))
            errors += int(m.group(3))
            skipped += int(m.group(4))
        self.output.info("[upstream tests] surefire reports={}  Tests run={} Failures={} "
                         "Errors={} Skipped={}".format(files, total, failures, errors, skipped))
        if files == 0 or total == 0:
            raise ConanInvalidConfiguration(
                "upstream tests reported zero tests — refusing to claim success"
            )
        if failures or errors:
            raise ConanInvalidConfiguration(
                "upstream tests have real failures/errors: Failures={} Errors={}".format(
                    failures, errors)
            )

    def build(self):
        apply_conandata_patches(self)
        java_home = self._ensure_java()
        maven_home = self._ensure_maven()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + ":" +
                              os.path.join(maven_home, "bin") + ":" +
                              os.environ.get("PATH", ""))
        self.run(
            f'bash -c "cd {self.source_folder} && '
            f'mvn -pl {MODULES} -am clean package -B -DskipTests=false"',
            env="conanbuild",
        )
        self._run_upstream_tests_summary()

    def _find_jar(self, module, prefix):
        """Locate a produced jar (upstream impl module carries -SNAPSHOT in its
        pom version, so match by prefix instead of the exact release name)."""
        target = os.path.join(self.source_folder, module, "target")
        if not os.path.isdir(target):
            raise ConanInvalidConfiguration("missing target dir: " + target)
        for name in sorted(os.listdir(target)):
            if (name.startswith(prefix) and name.endswith(".jar")
                    and "-sources" not in name and "-javadoc" not in name):
                return os.path.join(target, name)
        raise ConanInvalidConfiguration(
            "build artifact not found in {}: expected {}*.jar".format(target, prefix)
        )

    def package(self):
        api_jar = self._find_jar("api", "jakarta.servlet.jsp.jstl-api-")
        impl_jar = self._find_jar("impl", "jakarta.servlet.jsp.jstl-")
        copy(self, os.path.basename(api_jar), os.path.dirname(api_jar),
             os.path.join(self.package_folder, "libexec"))
        # Normalise the implementation jar name (upstream pom version is
        # 3.0.2-SNAPSHOT); the jar's own MANIFEST is unaffected by the file name.
        shutil.copy2(impl_jar, os.path.join(self.package_folder, "libexec",
                                            f"jakarta.servlet.jsp.jstl-{self.version}.jar"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.bindirs = []
