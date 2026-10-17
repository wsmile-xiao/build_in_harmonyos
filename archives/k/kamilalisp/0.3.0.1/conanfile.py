#!/usr/bin/env python3
"""Conan recipe — kamilalisp 0.3.0.1 (Java source build with Maven).

KamilaLisp ("Two: Electric Boogaloo") is a functional/array Lisp interpreter.
Upstream ships a Java 17 + Maven project whose fat JAR (`kamilalisp-0.3.jar`,
``Main-Class: palaiologos.kamilalisp.repl.Main``) is a runnable REPL / script
interpreter. There is no native (C/C++) code in the project.

This recipe follows the repository's existing Java packaging precedent
(archives/a/airlift-slice, archives/t/t-digest, archives/v/vinnie,
archives/w/weupnp): download the upstream tarball, build with Maven +
BiSheng JDK 17, run the upstream JUnit suite in ``build()``, and package the
resulting JAR as a CLI application.

OHOS platform adaptations (documented in notes.md):
  * BiSheng JDK 17 is required (JVM ``os.name`` == "HarmonyOS"); the recipe
    locates it (JAVA_HOME / ~/bishengjdk17 / PATH) or installs it via cmd-pkgs.
  * ``user.home`` is reported as "?" by the BiSheng JVM on OpenHarmony, so
    Maven cannot find ``~/.m2``. We pass ``-Duser.home=$HOME`` explicitly.
  * ProGuard 7.3.2 OOMs (SIGKILL 137) obfuscating the 36 MB fat JAR on the
    OHOS worker; obfuscation is a non-functional packaging step, so it is
    skipped via ``-Dproguard.skip=true`` (the shaded, functional JAR is kept).

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package executes the packaged CLI / JAR (not a stub)
R38: application package → software-level commands.json declares the CLI
R51: upstream JUnit suite is actually executed in build() and counted
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (get, copy, download,
                               apply_conandata_patches, export_conandata_patches)


class KamilalispConan(ConanFile):
    name = "kamilalisp"
    version = "0.3.0.1"
    description = "KamilaLisp — a functional, flexible and concise Lisp interpreter (Java)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/iczelia/kamilalisp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    # upstream pom.xml declares <version>0.3</version>, so the shaded artifact
    # is target/kamilalisp-0.3.jar (conan version tracks the upstream tag v0.3.0.1)
    _UPSTREAM_JAR = "kamilalisp-0.3.jar"

    # ── toolchain discovery / bootstrap (no external curl/wget — conan download) ──
    _JDK_INSTALL_URL = (
        "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
        "/releases/download/pkgs/install-jdk.sh"
    )
    _MAVEN_TARBALL_URL = (
        "https://archive.apache.org/dist/maven/maven-3/3.6.3/binaries"
        "/apache-maven-3.6.3-bin.tar.gz"
    )
    _MAVEN_TARBALL_SHA256 = (
        "26ad91d751b3a9a53087aefa743f4e16a17741d3915b219cf74112bf87a438c5"
    )

    def export_sources(self):
        # no patches for this release; kept for recipe structural completeness
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kamilalisp does not support OS: {self.settings.os}"
            )

    # ------------------------------------------------------------------ env
    def _home(self):
        return os.environ.get("HOME") or os.path.expanduser("~")

    def _sandbox_env(self):
        """HMBS/OHOS sandbox: /tmp may be read-only; propagate a writable TMPDIR."""
        env = dict(os.environ)
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self._home(), "tmp")
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        return env

    @staticmethod
    def _env_list(env):
        return [f"{k}={v}" for k, v in env.items()]

    # --------------------------------------------------------------- java
    def _find_java(self):
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            return java_home
        home = self._home()
        for candidate in (
            os.path.join(home, "bishengjdk17"),
            os.path.join(home, "usr", "local", "bishengjdk17"),
            "/data/service/hnp/bishengjdk17",
        ):
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                return candidate
        java_in_path = shutil.which("java")
        if java_in_path:
            return os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
        return ""

    def _ensure_java(self):
        java_home = self._find_java()
        if java_home:
            self.output.info("Using JDK at " + java_home)
            return java_home

        # Auto-install BiSheng JDK 17.0.13 via cmd-pkgs (CI workers may lack JDK)
        self.output.info("JDK not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        script_path = os.path.join(self._home(), ".install-jdk.sh")
        download(self, self._JDK_INSTALL_URL, script_path)
        env = self._sandbox_env()
        self.run(f'sh "{script_path}" 17.0.13', env=self._env_list(env))

        java_home = os.path.join(self._home(), "bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            return java_home
        raise ConanInvalidConfiguration(
            "Failed to locate or install BiSheng JDK 17. "
            "Set JAVA_HOME or install via cmd-pkgs install-jdk.sh."
        )

    # -------------------------------------------------------------- maven
    def _find_maven(self):
        home = self._home()
        for candidate in (
            os.path.join(home, "maven", "bin", "mvn"),
            os.path.join(home, "usr", "local", "maven", "bin", "mvn"),
            "/usr/share/maven/bin/mvn",
            "/opt/maven/bin/mvn",
            "/usr/local/maven/bin/mvn",
        ):
            if os.path.isfile(candidate):
                return candidate
        mvn_in_path = shutil.which("mvn")
        if mvn_in_path:
            return mvn_in_path
        return ""

    def _ensure_maven(self):
        mvn = self._find_maven()
        if mvn:
            self.output.info("Using Maven at " + mvn)
            return mvn

        self.output.info("Maven not found — installing Maven 3.6.3 from Apache archive...")
        home = self._home()
        tarball_path = os.path.join(home, "apache-maven-3.6.3-bin.tar.gz")
        maven_root = os.path.join(home, "maven")
        download(self, self._MAVEN_TARBALL_URL, tarball_path,
                 sha256=self._MAVEN_TARBALL_SHA256)
        # double-check integrity (download() already verifies sha256; keep explicit)
        actual = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual != self._MAVEN_TARBALL_SHA256:
            raise ConanInvalidConfiguration(
                f"apache-maven-3.6.3 sha256 mismatch: {actual}"
            )
        os.makedirs(maven_root, exist_ok=True)
        env = self._sandbox_env()
        self.run(
            'tar -xzf "{}" -C "{}" --strip-components=1'.format(tarball_path, maven_root),
            env=self._env_list(env),
        )
        mvn_bin = os.path.join(maven_root, "bin", "mvn")
        if os.path.isfile(mvn_bin):
            return mvn_bin
        raise ConanInvalidConfiguration("Failed to install Maven 3.6.3.")

    # -------------------------------------------------------------- source
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # --------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)  # no-op unless conandata.yml declares patches
        env = self._sandbox_env()
        for k in ("TMPDIR", "TMP", "TEMP"):
            if k in env:
                os.environ[k] = env[k]

        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        mvn_cmd = self._ensure_maven()

        # `user.home` is "?" under the BiSheng JVM on OpenHarmony → Maven would
        # resolve ~/.m2 to a bogus path. Pin it to the real HOME.
        home = self._home()
        mvn_cmd_line = [
            mvn_cmd, "clean", "package", "-B",
            "-DskipTests=false",
            "-Dproguard.skip=true",
            f"-Duser.home={home}",
        ]

        # Log must live outside target/ (clean removes it).
        mvn_log = os.path.join(self.source_folder, "hmbs-maven-build.log")
        self.output.info("Running upstream JUnit suite via Maven (surefire): "
                         + " ".join(mvn_cmd_line))
        import sys
        with open(mvn_log, "w", encoding="utf-8") as logf:
            proc = subprocess.Popen(
                mvn_cmd_line,
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

        self.output.info(f"Maven run finished (exit {rc}); log at {mvn_log}")
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"Maven build failed (exit {rc}). See {mvn_log}."
            )

        # ── parse upstream surefire summary ("Tests run: N, Failures: F, Errors: E, Skipped: S") ──
        with open(mvn_log, "r", encoding="utf-8", errors="replace") as f:
            log_text = f.read()
        rx = re.compile(
            r"Tests run:\s*(\d+)\s*,\s*Failures:\s*(\d+)\s*,\s*"
            r"Errors:\s*(\d+)\s*,\s*Skipped:\s*(\d+)"
        )
        match = None
        for m in rx.finditer(log_text):
            match = m  # last match == reactor total
        if match is None:
            raise ConanInvalidConfiguration(
                "Surefire summary 'Tests run: ...' not found in Maven output "
                f"({mvn_log}). Upstream test suite did not execute."
            )
        executed = int(match.group(1))
        failed = int(match.group(2)) + int(match.group(3))
        skipped = int(match.group(4))
        passed = executed - failed - skipped
        marker = {
            "status": "passed" if failed == 0 and skipped == 0 else "failed",
            "framework": "junit5-surefire",
            "command": " ".join(mvn_cmd_line),
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False),
              flush=True)

    # ------------------------------------------------------------- package
    def package(self):
        jar_name = self._UPSTREAM_JAR
        target_dir = os.path.join(self.source_folder, "target")
        jar_src = os.path.join(target_dir, jar_name)
        if not os.path.exists(jar_src):
            # fallback: discover the shaded artifact (exclude the pre-shade original)
            import glob
            candidates = [p for p in glob.glob(os.path.join(target_dir, "*.jar"))
                          if not os.path.basename(p).startswith("original-")]
            if len(candidates) == 1:
                jar_src = candidates[0]
                jar_name = os.path.basename(jar_src)
            else:
                raise ConanInvalidConfiguration(
                    f"Build artifact not found: {jar_src}. Maven build did not finish."
                )
        copy(self, jar_name, target_dir, os.path.join(self.package_folder, "libexec"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        # CLI launcher (kamilalisp is a REPL / script interpreter)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "kamilalisp")
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env sh\n"
                "# kamilalisp CLI launcher (HarmonyOS PC)\n"
                'HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
                f'JAR="$HERE/../libexec/{jar_name}"\n'
                'if [ -n "$JAVA_HOME" ] && [ -x "$JAVA_HOME/bin/java" ]; then\n'
                '    JAVA="$JAVA_HOME/bin/java"\n'
                "else\n"
                "    JAVA=java\n"
                "fi\n"
                'exec "$JAVA" -jar "$JAR" "$@"\n'
            )
        os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["libexec"]
