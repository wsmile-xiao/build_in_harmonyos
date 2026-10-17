#!/usr/bin/env python3
"""Conan recipe — auto64fto32f 2.1 (Java source compilation).

Downloads the upstream source tarball from GitHub (lessthanoptimal/Auto64Fto32F
tag v2.1), compiles the four library sources directly with javac (no Gradle —
the upstream build.gradle only adds jar/javadoc/sourcesJar tasks on top of a
plain `src/` java source set), runs the upstream JUnit 4 test suite with
org.junit.runner.JUnitCore in build(), and packages the resulting JAR.

Source:   https://github.com/lessthanoptimal/Auto64Fto32F (tag v2.1)
License:  Unlicense OR MIT (dual license, user's choice)
Build:    javac --release 11 + jar tool from BiSheng JDK 17 (system tool)
Upstream tests: 4 @Test methods in test/com/peterabeles/auto64fto32f/
          TestAugmentJavaFiles.java, executed via JUnitCore.

R28: test_package/ included
R32: validate() checks settings.os in ("Linux", "OHOS")
R34: test_package calls AugmentJavaFiles / ConvertFile32From64 /
     RecursiveConvert APIs against the installed JAR
R38: no bin/ artifact upstream has no main class — library package,
     commands.json intentionally not created
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, download, apply_conandata_patches, export_conandata_patches


class Auto64Fto32FConan(ConanFile):
    name = "auto64fto32f"
    version = "2.1"
    description = (
        "A minimalist library for converting double (64-bit) numerical "
        "Java code into float (32-bit)"
    )
    license = "Unlicense OR MIT"
    homepage = "https://github.com/lessthanoptimal/Auto64Fto32F"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # JVM application — no C/C++ toolchain involved, but the OHOS CI L0p
    # quality gate requires all four settings (ARCHIVE-SPEC.md §2.2,
    # knowledge/drafts/E216; published precedent: aladin/12.06)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        # R32: must use `in ("Linux", "OHOS")`, never `== "Linux"`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"auto64fto32f does not support OS: {self.settings.os}"
            )

    def source(self):
        # Pin destination: get()/untargz default to "." (process cwd); pinning
        # guarantees the stripped tree lands in source_folder deterministically.
        get(self, **self.conan_data["sources"], strip_root=True,
            destination=self.source_folder)

    # ------------------------------------------------------------------
    # HMBS sandbox quirks handled below
    #   * /tmp is read-only — every child process must inherit HMBS's
    #     writable TMPDIR/TMP/TEMP.
    #   * JDK may be absent on CI workers — auto-install bishengjdk via
    #     cmd-pkgs install-jdk.sh as a last resort.
    # ------------------------------------------------------------------
    _CA_BUNDLE_CANDIDATES = (
        "/etc/ssl/certs/ca-bundle.crt",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/system/etc/ssl/certs/ca-certificates.crt",
    )

    @staticmethod
    def _sandbox_env():
        """Env dict propagating HMBS writable TMPDIR to children."""
        env = dict(os.environ)
        tmpdir = (
            env.get("HMBS_TMPDIR")
            or env.get("TMPDIR")
            or env.get("TMP")
            or env.get("TEMP")
        )
        if tmpdir:
            env["TMPDIR"] = tmpdir
            env["TMP"] = tmpdir
            env["TEMP"] = tmpdir
        for cand in Auto64Fto32FConan._CA_BUNDLE_CANDIDATES:
            if os.path.isfile(cand):
                env["CURL_CA_BUNDLE"] = cand
                env["REQUESTS_CA_BUNDLE"] = cand
                env["SSL_CERT_FILE"] = cand
                break
        return env

    def _ensure_java(self):
        """Find bishengjdk 17, or auto-install it via cmd-pkgs install-jdk.sh.

        Order: JAVA_HOME -> ~/bishengjdk17 / ~/usr/local/bishengjdk17 ->
        `java` on PATH -> cmd-pkgs auto-install. Returns JAVA_HOME path.
        """
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/storage/Users/currentUser/usr/local/bishengjdk17",
            "/usr/lib/jvm/bishengjdk-17",
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(
                os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

        self.output.info(
            "Java not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh"
        )
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        # Pure-Python fetch via conan.tools.files.download (same mechanism as
        # the conandata test_dependencies above) — no external downloader
        # binaries required on CI workers.
        download(self, install_url, script_path, retry=3, retry_wait=2)
        env = self._sandbox_env()
        self.run('sh "{}" 17.0.13'.format(script_path),
                 env=[f"{k}={v}" for k, v in env.items()])

        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home

        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. Set JAVA_HOME to a "
            "full JDK 11+ (with javac) or pre-install BiSheng JDK 17 at "
            "~/bishengjdk17."
        )

    def _run_logged(self, cmd, log_path=None):
        """Run cmd (list of args) capturing combined output; return (rc, text)."""
        self.output.info("Running: " + " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        chunks = []
        for line in proc.stdout:
            chunks.append(line)
            self.output.info(line.rstrip("\n"))
        rc = proc.wait()
        output_text = "".join(chunks)
        if log_path:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(output_text)
        return rc, output_text

    def build(self):
        apply_conandata_patches(self)

        # HMBS sandbox: propagate writable TMPDIR to all children
        sandbox_env = self._sandbox_env()
        for k in ("TMPDIR", "TMP", "TEMP", "CURL_CA_BUNDLE",
                  "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
            if k in sandbox_env:
                os.environ[k] = sandbox_env[k]

        java_home = self._ensure_java()
        javac = os.path.join(java_home, "bin", "javac")
        jartool = os.path.join(java_home, "bin", "jar")
        java = os.path.join(java_home, "bin", "java")
        if not os.path.isfile(javac):
            raise ConanInvalidConfiguration(
                f"javac not found at {javac}; a full JDK (not JRE) is required")

        src_root = self.source_folder
        # Upstream v2.1 tarball (strip_root=True) keeps Gradle's sourceSets
        # layout: <src_root>/src/com/peterabeles/auto64fto32f/*.java
        pkg_dir = os.path.join(src_root, "src", "com", "peterabeles",
                               "auto64fto32f")
        if not os.path.isdir(pkg_dir):
            # Defensive fallback for trees extracted without the top root
            pkg_dir = os.path.join(src_root, "com", "peterabeles", "auto64fto32f")
        if not os.path.isdir(pkg_dir):
            raise ConanInvalidConfiguration(
                "Upstream Java sources not found: expected "
                + os.path.join(src_root, "src", "com", "peterabeles",
                               "auto64fto32f"))
        main_sources = [
            os.path.join(pkg_dir, f) for f in sorted(os.listdir(pkg_dir))
            if f.endswith(".java")
        ]
        if not main_sources:
            raise ConanInvalidConfiguration(
                "No .java files found under " + pkg_dir)

        classes_dir = os.path.join(src_root, "build", "classes")
        test_classes_dir = os.path.join(src_root, "build", "test-classes")
        jar_path = os.path.join(src_root, "auto64fto32f-2.1.jar")
        os.makedirs(classes_dir, exist_ok=True)
        os.makedirs(test_classes_dir, exist_ok=True)

        # ---- Download JUnit 4 runner deps (sha256 verified by conan) ----
        dep_paths = {}
        for dep in self.conan_data.get("test_dependencies", []):
            # Absolute path: download() resolves a relative filename against
            # the conan process cwd (os.path.abspath), not source_folder.
            dep_path = os.path.join(src_root, dep["filename"])
            download(self, url=dep["urls"], filename=dep_path,
                     sha256=dep["sha256"])
            out = dep_path
            if not os.path.isfile(out) or os.path.getsize(out) == 0:
                raise ConanInvalidConfiguration(
                    f"Downloaded test dependency missing/empty: {out}")
            dep_paths[dep["filename"]] = out
        junit_jar = dep_paths.get("junit-4.12.jar")
        hamcrest_jar = dep_paths.get("hamcrest-core-1.3.jar")
        if not junit_jar or not hamcrest_jar:
            raise ConanInvalidConfiguration(
                "junit-4.12.jar / hamcrest-core-1.3.jar missing after download")

        # ---- Compile library sources (upstream targetCompatibility = 11) ----
        rc, out = self._run_logged(
            [javac, "--release", "11", "-encoding", "UTF-8",
             "-d", classes_dir] + main_sources)
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"javac failed for library sources (exit {rc}).")

        # ---- Package the JAR (equivalent of upstream `gradle jar`) ----
        rc, out = self._run_logged(
            [jartool, "cf", jar_path, "-C", classes_dir, "."])
        if rc != 0:
            raise ConanInvalidConfiguration(f"jar packaging failed (exit {rc}).")
        if not os.path.isfile(jar_path) or os.path.getsize(jar_path) == 0:
            raise ConanInvalidConfiguration(
                f"Built JAR missing or empty: {jar_path}")

        # ---- Compile and run the upstream JUnit 4 test suite ----
        test_source = os.path.join(
            src_root, "test", "com", "peterabeles", "auto64fto32f",
            "TestAugmentJavaFiles.java")
        test_cp = ":".join([classes_dir, junit_jar, hamcrest_jar])
        rc, out = self._run_logged(
            [javac, "--release", "11", "-encoding", "UTF-8",
             "-cp", test_cp, "-d", test_classes_dir, test_source])
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"javac failed for upstream test sources (exit {rc}).")

        junit_log = os.path.join(src_root, "hmbs-junit-run.log")
        run_cp = ":".join([classes_dir, test_classes_dir, junit_jar, hamcrest_jar])
        junit_cmd = [
            java, "-cp", run_cp,
            "org.junit.runner.JUnitCore",
            "com.peterabeles.auto64fto32f.TestAugmentJavaFiles",
        ]
        rc, junit_out = self._run_logged(junit_cmd, log_path=junit_log)

        # ------------------------------------------------------------------
        # Parse real numbers from JUnitCore's own output. Success prints
        # "OK (N tests)"; failure prints "... FAILURES!!! Tests run: N,  Failures: M".
        # Exit code 0 alone proves nothing — a missing summary line means the
        # suite never really ran, so we refuse to emit any stub marker.
        # ------------------------------------------------------------------
        discovered_expected = 4  # static @Test count in TestAugmentJavaFiles.java
        executed = passed = failed = skipped = 0
        ok_match = re.search(r"OK \((\d+) tests?\)", junit_out)
        fail_match = re.search(r"Tests run:\s*(\d+),\s*Failures:\s*(\d+)", junit_out)

        if ok_match:
            executed = int(ok_match.group(1))
            passed = executed
        elif fail_match:
            executed = int(fail_match.group(1))
            failed = int(fail_match.group(2))
            passed = executed - failed
        else:
            raise ConanInvalidConfiguration(
                "JUnitCore summary line ('OK (N tests)' or 'Tests run: ...') "
                f"not found in output ({junit_log}). Upstream JUnit suite did "
                "not execute; refusing to emit a stub HMBS_UPSTREAM_TEST_RESULT.")

        if executed < 1:
            raise ConanInvalidConfiguration(
                f"JUnitCore reported {executed} executed tests; expected >= 1.")
        if executed != discovered_expected:
            raise ConanInvalidConfiguration(
                f"Executed test count {executed} != static @Test count "
                f"{discovered_expected}; test discovery mismatch.")

        marker = {
            "status": "passed" if (failed == 0 and skipped == 0 and
                                   passed == executed) else "failed",
            "framework": "junit4",
            "command": " ".join(junit_cmd),
            "discovered": discovered_expected,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(marker, ensure_ascii=False), flush=True)

        if marker["status"] != "passed":
            raise ConanInvalidConfiguration(
                f"Upstream JUnit suite failed: executed={executed}, "
                f"passed={passed}, failed={failed}, skipped={skipped}. "
                f"See {junit_log}.")

    def package(self):
        jar_name = "auto64fto32f-2.1.jar"
        copy(self, jar_name, self.source_folder,
             os.path.join(self.package_folder, "libexec"))
        built_jar = os.path.join(self.package_folder, "libexec", jar_name)
        if not os.path.exists(built_jar) or os.path.getsize(built_jar) == 0:
            raise ConanInvalidConfiguration(
                f"Build artifact missing after package: {built_jar}")

        # Dual license files ship in the tarball root
        copy(self, "LICENSE-MIT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "UNLICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Java code-generation library: consumers put libexec/*.jar on the
        # JVM classpath. No bindirs — upstream ships no CLI entry point.
        self.cpp_info.libdirs = ["libexec"]
