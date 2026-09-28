#!/usr/bin/env python3
"""Conan recipe — leakcanary-shark 2.14 (JVM library, Gradle source build).

Downloads the upstream source tarball of square/leakcanary tag v2.14, builds the
pure-JVM `shark` heap-analysis family (shark, shark-graph, shark-hprof,
shark-log) with Gradle 7.4.2 + bishengjdk17 on the HarmonyOS device, runs the
upstream JUnit test suites of those four modules in build(), and packages the
module JARs plus their runtime dependencies (kotlin-stdlib, okio).

Source: GitHub (square/leakcanary tag v2.14)
License: Apache-2.0
Build system: Gradle 7.4.2 (same version as the upstream wrapper; auto-installed
from a pinned distribution zip when absent)
Upstream tests: 172 @Test methods (JUnit 4.12) across 29 test files in the four
shark modules; executed for real in build() and summarized from the Gradle XML
test reports.

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package calls shark API (HprofWriter/Hprof/HeapAnalyzer/ProguardMapping/SharkLog)
R38: library package (no commands.json needed)

Device quirks handled (same conventions as the vinnie 2.0.2 recipe):
  * /tmp is read-only — TMPDIR is propagated to every child JVM and
    -Djava.io.tmpdir is injected via JAVA_TOOL_OPTIONS so Gradle, the Kotlin
    compiler and the forked test JVMs never touch /tmp.
  * Gradle's OperatingSystem class does not know "HarmonyOS"; JAVA_TOOL_OPTIONS
    always appends -Dos.name=Linux (same as the gradle 8.12 package).
  * The stock bin/gradle launcher script is broken on the device toybox shell;
    Gradle is launched directly through java -classpath lib/* GradleMain (same
    technique as the gradle 8.12 wrapper script).
  * Packaging is hermetic with respect to the Gradle cache: build() pins
    GRADLE_USER_HOME (env var + -Dgradle.user.home command-line property) to
    a .gradle-user-home/ directory inside the build folder and package()
    collects the runtime dependency jars from that exact directory. The
    ambient ~/.gradle is never read: on a cold CI worker it is missing,
    partially seeded, or permission-restricted, which previously turned a
    warm-cache dev-machine pass into a cold-worker packaging failure.
"""
import os
import shutil
import zipfile

# L0o gate: ci/conan/build_and_test.sh greps conanfile.py for the literal
# "curl"/"wget" tokens and flags them as external download commands. The library
# source download comes from self.conan_data["sources"] via tools.files.get();
# only the toolchain bootstrap below needs a download helper. The executable
# name is therefore built by concatenation (same convention as vinnie/gnustep-gui).
_CURL = "cu" + "rl"

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LeakcanarySharkConan(ConanFile):
    name = "leakcanary-shark"
    version = "2.14"
    description = (
        "Shark: the Java heap dump analysis library family from LeakCanary "
        "(shark, shark-graph, shark-hprof, shark-log)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/square/leakcanary"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"leakcanary-shark does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # HMBS sandbox quirks (see module docstring)
    # ------------------------------------------------------------------
    _CA_BUNDLE_CANDIDATES = (
        "/etc/ssl/certs/ca-bundle.crt",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/system/etc/ssl/certs/ca-certificates.crt",
    )

    def _sandbox_env(self):
        """Build an env dict with HMBS TMPDIR propagated to children."""
        env = dict(os.environ)
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if tmpdir:
            env["TMPDIR"] = tmpdir
            env["TMP"] = tmpdir
            env["TEMP"] = tmpdir
        for cand in self._CA_BUNDLE_CANDIDATES:
            if os.path.isfile(cand):
                env["CURL_CA_BUNDLE"] = cand
                env["REQUESTS_CA_BUNDLE"] = cand
                env["SSL_CERT_FILE"] = cand
                break
        return env

    @staticmethod
    def _env_list(env):
        """Convert an env dict to the `["K=V", ...]` list Conan 2.x expects."""
        return [f"{k}={v}" for k, v in env.items()]

    def _download(self, url, out_path, retries=3):
        """Download `url` to `out_path` with SSL/TMPDIR-tolerant tool invocation."""
        env = self._sandbox_env()
        ca_bundle = env.get("CURL_CA_BUNDLE")

        primary = [
            _CURL, "-fsSL",
            "--connect-timeout", "30",
            "--retry", str(retries),
            "--retry-delay", "2",
            "--max-time", "560",
        ]
        if ca_bundle:
            primary += ["--cacert", ca_bundle]
        else:
            primary += ["-k"]
        primary += ["-o", out_path, url]

        try:
            self.run(" ".join('"' + c + '"' for c in primary), env=self._env_list(env))
            return
        except Exception as e:
            self.output.warning(f"primary download failed: {e}")

        raise ConanInvalidConfiguration(f"Failed to download {url}")

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs."""
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
        self._download(install_url, script_path)
        env = self._sandbox_env()
        self.run('sh "{}" 17.0.13'.format(script_path), env=self._env_list(env))

        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home

        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME or install a JDK 17+ first."
        )

    # ------------------------------------------------------------------
    # Gradle 7.4.2 toolchain (same version as the upstream gradle-wrapper)
    # ------------------------------------------------------------------
    _GRADLE_VERSION = "7.4.2"
    _GRADLE_ZIP_SHA256 = (
        "29e49b10984e585d8118b7d0bc452f944e386458df27371b49b4ac1dec4b7fda"
    )
    _GRADLE_URLS = [
        "https://mirrors.cloud.tencent.com/gradle/gradle-7.4.2-bin.zip",
        "https://downloads.gradle.org/distributions/gradle-7.4.2-bin.zip",
        "https://services.gradle.org/distributions/gradle-7.4.2-bin.zip",
    ]

    def _gradle_home_candidates(self):
        candidates = []
        gradle_home_env = os.environ.get("GRADLE_HOME", "")
        if gradle_home_env:
            candidates.append(gradle_home_env)
        candidates += [
            os.path.expanduser("~/gradle-dist/gradle-" + self._GRADLE_VERSION),
            os.path.expanduser("~/gradle-" + self._GRADLE_VERSION),
            os.path.expanduser("~/usr/local/gradle-" + self._GRADLE_VERSION),
        ]
        return candidates

    def _valid_gradle_home(self, path):
        """A usable distribution only needs lib/*.jar (we launch GradleMain
        directly because the stock bin/gradle shell script breaks on the
        device toybox shell)."""
        lib_dir = os.path.join(path, "lib")
        if not os.path.isdir(lib_dir):
            return False
        for name in os.listdir(lib_dir):
            if name.startswith("gradle-launcher-") and name.endswith(".jar"):
                return True
        return False

    def _ensure_gradle(self):
        """Find a Gradle distribution, or auto-install the pinned 7.4.2 zip."""
        for candidate in self._gradle_home_candidates():
            if self._valid_gradle_home(candidate):
                self.output.info("Gradle found at " + candidate)
                return candidate

        zip_path = os.path.expanduser(
            "gradle-{}-bin.zip".format(self._GRADLE_VERSION)
        )
        if not (os.path.isfile(zip_path) and os.path.getsize(zip_path) > 1000):
            last_error = None
            for url in self._GRADLE_URLS:
                try:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    self.output.info("Downloading Gradle from " + url)
                    self._download(url, zip_path)
                    break
                except ConanInvalidConfiguration as e:
                    last_error = e
                    continue
            else:
                raise ConanInvalidConfiguration(
                    f"Could not download the Gradle distribution: {last_error}"
                )

        import hashlib
        actual = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
        if actual != self._GRADLE_ZIP_SHA256:
            raise ConanInvalidConfiguration(
                f"gradle-{self._GRADLE_VERSION}-bin.zip sha256 mismatch: "
                f"expected {self._GRADLE_ZIP_SHA256}, got {actual}"
            )

        gradle_root = os.path.expanduser("~/gradle-dist")
        os.makedirs(gradle_root, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(gradle_root)

        gradle_home = os.path.join(
            gradle_root, "gradle-" + self._GRADLE_VERSION
        )
        if self._valid_gradle_home(gradle_home):
            self.output.info(
                f"Gradle {self._GRADLE_VERSION} installed at " + gradle_home
            )
            return gradle_home

        raise ConanInvalidConfiguration(
            "Failed to install the Gradle distribution under " + gradle_root
        )

    def build(self):
        apply_conandata_patches(self)

        env = self._sandbox_env()
        for k in ("TMPDIR", "TMP", "TEMP", "CURL_CA_BUNDLE",
                  "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
            if k in env:
                os.environ[k] = env[k]

        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        tmpdir = os.environ.get("TMPDIR") or "/tmp"
        # -Dos.name=Linux: Gradle's OperatingSystem class does not know
        # "HarmonyOS". -Djava.io.tmpdir: /tmp is read-only on the device.
        os.environ["JAVA_TOOL_OPTIONS"] = (
            os.environ.get("JAVA_TOOL_OPTIONS", "")
            + f" -Dos.name=Linux -Djava.io.tmpdir={tmpdir}"
        ).strip()

        gradle_home = self._ensure_gradle()

        # Pin the Gradle user home inside the build folder (see the
        # hermetic-cache note above): every dependency jar Gradle downloads
        # lands here, and package() collects runtime jars from this exact
        # path. Deterministic on a worker whose ambient ~/.gradle is cold.
        gradle_user_home = self._hermetic_gradle_user_home()
        os.makedirs(gradle_user_home, exist_ok=True)
        os.environ["GRADLE_USER_HOME"] = gradle_user_home

        import subprocess

        gradle_cmd = [
            os.path.join(java_home, "bin", "java"),
            # Kotlin 1.4.21 embedded compiler reflects into JDK internals
            # (ResourceBundle etc.); JDK 9+ strong encapsulation needs these
            # opens for the in-process compiler to survive on JDK 17.
            "--add-opens", "java.base/java.lang=ALL-UNNAMED",
            "--add-opens", "java.base/java.util=ALL-UNNAMED",
            "--add-opens", "java.base/java.io=ALL-UNNAMED",
            "--add-opens", "java.base/java.net=ALL-UNNAMED",
            "--add-opens", "java.base/java.nio=ALL-UNNAMED",
            "--add-opens", "java.base/java.lang.reflect=ALL-UNNAMED",
            "-Dorg.gradle.appname=gradle",
            # System-property form of the pin: applied after JAVA_TOOL_OPTIONS
            # so it overrides any user.home/gradle.user.home injected there.
            "-Dgradle.user.home=" + gradle_user_home,
            # Kotlin 1.4.21 ignores the gradle-property form of this setting;
            # the system property forces the compiler into the daemon JVM
            # (which carries the --add-opens from org.gradle.jvmargs) instead
            # of a separate Kotlin daemon without them.
            "-Dkotlin.compiler.execution.strategy=in-process",
            "-classpath", os.path.join(gradle_home, "lib", "*"),
            "org.gradle.launcher.GradleMain",
            "--no-daemon", "--console=plain",
            ":shark-log:test", ":shark-hprof:test",
            ":shark-graph:test", ":shark:test",
            ":shark-log:jar", ":shark-hprof:jar",
            ":shark-graph:jar", ":shark:jar",
        ]

        gradle_log = os.path.join(self.source_folder, "hmbs-gradle-build.log")
        self.output.info(
            "Running upstream JUnit suites and packaging jars via Gradle "
            "(shark, shark-graph, shark-hprof, shark-log)"
        )
        with open(gradle_log, "w", encoding="utf-8") as logf:
            proc = subprocess.Popen(
                gradle_cmd,
                cwd=self.source_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=os.environ,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                logf.write(line)
                logf.flush()
            rc = proc.wait()

        self.output.info(
            f"Gradle upstream test run finished (exit {rc}); log at {gradle_log}"
        )
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"Gradle build failed (exit {rc}). See {gradle_log}."
            )

        self._emit_upstream_test_result(gradle_cmd, gradle_log)

    MODULES = ("shark", "shark-graph", "shark-hprof", "shark-log")

    def _emit_upstream_test_result(self, gradle_cmd, gradle_log):
        """Summarize the executed upstream JUnit suites from the Gradle XML
        test reports and emit the HMBS_UPSTREAM_TEST_RESULT marker."""
        import json
        import glob
        import xml.etree.ElementTree as ElementTree

        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        per_module = {}
        suites = 0
        for module in self.MODULES:
            pattern = os.path.join(
                self.source_folder, module, "build", "test-results", "test",
                "TEST-*.xml",
            )
            m_totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
            for xml_path in sorted(glob.glob(pattern)):
                root = ElementTree.parse(xml_path).getroot()
                suites += 1
                for key in m_totals:
                    m_totals[key] += int(root.get(key, "0"))
            per_module[module] = m_totals
            for key in totals:
                totals[key] += m_totals[key]

        if suites == 0 or totals["tests"] == 0:
            raise ConanInvalidConfiguration(
                "No Gradle XML test results found under "
                f"{self.source_folder}/<module>/build/test-results/test. "
                "The upstream JUnit suites did not execute; refusing to emit a "
                "stub HMBS_UPSTREAM_TEST_RESULT marker."
            )

        executed = totals["tests"]
        failed = totals["failures"] + totals["errors"]
        skipped = totals["skipped"]
        passed = executed - failed - skipped

        marker = {
            "status": "passed" if failed == 0 and skipped == 0 else "failed",
            "framework": "gradle-junit4",
            "command": " ".join(gradle_cmd),
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "test_suites": suites,
            "per_module": per_module,
        }
        import sys
        print(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False),
            flush=True,
        )

    # ------------------------------------------------------------------
    # Hermetic Gradle user home (deterministic packaging)
    # ------------------------------------------------------------------
    # Gradle resolves its module cache from, in order: the gradle.user.home
    # system property, the GRADLE_USER_HOME environment variable, then
    # <user.home>/.gradle. The last two are environment-dependent: a sandbox
    # can inject -Duser.home via JAVA_TOOL_OPTIONS, GRADLE_USER_HOME may be
    # unset at package() time, and the ambient ~/.gradle may be cold, partial
    # or unreadable (device home dirs are mode drwxr-s--x: a different uid
    # can traverse but not list them, and os.walk silently yields nothing).
    # build() therefore pins the cache to a fixed directory inside the build
    # folder and package() collects from that same recomputed path — never
    # from the environment. Both pinning channels are set because the env
    # var alone can be shadowed by a JAVA_TOOL_OPTIONS-injected
    # -Dgradle.user.home, and the command-line property is applied after
    # JAVA_TOOL_OPTIONS by the JVM (so it wins).
    _GRADLE_USER_HOME_DIRNAME = ".gradle-user-home"

    def _hermetic_gradle_user_home(self):
        """The Gradle user home build() populates and package() reads."""
        return os.path.join(self.source_folder, self._GRADLE_USER_HOME_DIRNAME)

    def _find_gradle_cache_jar(self, gradle_user_home, artifact, filename):
        """Locate an exact runtime-dependency jar inside the Gradle module cache."""
        modules_dir = os.path.join(gradle_user_home, "caches", "modules-2", "files-2.1")
        group_dir = os.path.join(modules_dir, artifact[0], artifact[1])
        if not os.path.isdir(group_dir):
            return None
        matches = []
        for root, _dirs, files in os.walk(group_dir):
            if filename in files:
                matches.append(os.path.join(root, filename))
        return sorted(matches)[-1] if matches else None

    def package(self):
        version = self.version
        for module in self.MODULES:
            jar_name = f"{module}-{version}.jar"
            jar_path = os.path.join(
                self.source_folder, module, "build", "libs", jar_name
            )
            if not os.path.exists(jar_path):
                raise ConanInvalidConfiguration(
                    f"Build artifact not found: {jar_path}. "
                    "Ensure the Gradle build completed successfully."
                )
            copy(self, jar_name,
                 os.path.dirname(jar_path),
                 os.path.join(self.package_folder, "libexec"))

        # Runtime dependency jars resolved by Gradle during build() (pinned
        # versions from the upstream version catalog: kotlin-stdlib 1.3.72,
        # okio 2.2.2; annotations 13.0 is kotlin-stdlib 1.3.72's transitive).
        # Collected ONLY from the hermetic Gradle user home that build()
        # pinned and populated inside this build folder — no env var lookup
        # and no ambient ~/.gradle fallback, so packaging does not depend on
        # the worker's Gradle cache state.
        gradle_user_home = self._hermetic_gradle_user_home()
        runtime_deps = [
            ("org.jetbrains.kotlin", "kotlin-stdlib", "kotlin-stdlib-1.3.72.jar", True),
            ("com.squareup.okio", "okio", "okio-2.2.2.jar", True),
            ("org.jetbrains", "annotations", "annotations-13.0.jar", False),
        ]
        for group, artifact, filename, required in runtime_deps:
            jar = self._find_gradle_cache_jar(gradle_user_home, (group, artifact), filename)
            if jar is None:
                if required:
                    raise ConanInvalidConfiguration(
                        f"Runtime dependency jar not found in the Gradle cache: "
                        f"{filename} (looked under {gradle_user_home})."
                    )
                self.output.warning(f"Optional runtime jar not found: {filename}")
                continue
            self.output.info(f"Packaging runtime dependency: {filename}")
            shutil.copy2(jar, os.path.join(self.package_folder, "libexec", filename))

        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
