#!/usr/bin/env python3
"""Conan recipe — t-digest 3.0 (Java source compilation).

Downloads the official t-digest 3.0 source tarball (GitHub tag
t-digest-3.0), compiles with Apache Maven, runs the upstream JUnit
suite in build(), and packages the resulting JAR.

Source: GitHub (tdunning/t-digest tag t-digest-3.0)
License: Apache-2.0
Build system: Maven (system mvn with archive.apache.org fallback)
Upstream tests: 72 @Test methods (JUnit 4.8.2 via maven-surefire 2.16)

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package calls t-digest API (TDigest/quantile/cdf/merge)
R38: library package (no commands.json needed)
"""

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get


class TDigestConan(ConanFile):
    name = "t-digest"
    version = "3.0"
    description = "T-Digest: adaptive histogram for accurate quantile estimation on streams"
    license = "Apache-2.0"
    homepage = "https://github.com/tdunning/t-digest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # Pure-Java JAR has no shared/static distinction; option exists only to
    # satisfy Conan library validation and has no build effect.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _JDK_INSTALL_URL = (
        "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
        "releases/download/pkgs/install-jdk.sh"
    )
    _JDK_INSTALL_SHA256 = (
        "e324c0907cb7ade1bdb1dc5ec879608e222741e1eb87a8a5c86cbc38b4d3390b"
    )

    _MAVEN_URL = (
        "https://archive.apache.org/dist/maven/maven-3/3.6.3/binaries/"
        "apache-maven-3.6.3-bin.tar.gz"
    )
    _MAVEN_SHA256 = (
        "26ad91d751b3a9a53087aefa743f4e16a17741d3915b219cf74112bf87a438c5"
    )

    def export_sources(self):
        # No patch files: pom.xml adjustments are applied programmatically
        # in build() via _patch_pom() (whitespace-robust string replaces).
        pass

    def layout(self):
        pass

    def package_id(self):
        # JAR bytecode is identical for shared True/False and independent
        # of C++ compiler/build_type (pure-Java); clear them to a single
        # package_id while keeping os/arch for profile compatibility.
        self.info.options.rm_safe("shared")
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "t-digest is supported only on Linux and OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _java_executable(java_home, tool):
        return os.path.join(java_home, "bin", tool)

    def _find_or_install_java(self):
        java_home = os.environ.get("JAVA_HOME", "")
        candidates = [
            java_home,
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/storage/Users/currentUser/usr/local/bishengjdk17",
            "/usr/local/bishengjdk17",
            "/usr/lib/jvm/bishengjdk-17",
            "/usr/lib/jvm/java-17-openjdk",
            "/usr/lib/jvm/java-17-openjdk-arm64",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(
                self._java_executable(candidate, "java")
            ):
                return candidate

        java_on_path = shutil.which("java")
        if java_on_path:
            return os.path.dirname(
                os.path.dirname(os.path.realpath(java_on_path))
            )

        install_script = os.path.join(
            os.path.expanduser("~"), ".install-jdk.sh"
        )
        self.output.info("Installing BiSheng JDK 17.0.13 via cmd-pkgs")
        self.run(
            'curl -fsSL -o "{}" "{}"'.format(
                install_script, self._JDK_INSTALL_URL
            )
        )
        with open(install_script, "rb") as install_file:
            installer_sha256 = hashlib.sha256(install_file.read()).hexdigest()
        if installer_sha256 != self._JDK_INSTALL_SHA256:
            os.remove(install_script)
            raise ConanInvalidConfiguration(
                "Unexpected JDK installer SHA-256: {}".format(installer_sha256)
            )

        self.run('sh "{}" 17.0.13'.format(install_script))
        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(self._java_executable(java_home, "java")):
            return java_home

        raise ConanInvalidConfiguration(
            "Failed to find or install BiSheng JDK 17.0.13"
        )

    def _find_or_install_maven(self):
        candidates = [
            os.path.expanduser("~/maven/bin/mvn"),
            os.path.expanduser("~/usr/local/maven/bin/mvn"),
            os.path.expanduser("~/usr/local/bin/mvn"),
            "/usr/local/bin/mvn",
            "/usr/share/maven/bin/mvn",
            "/opt/maven/bin/mvn",
        ]
        candidates.extend([shutil.which("mvn")])
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate

        maven_root = os.path.join(self.build_folder, "_tools", "maven")
        mvn = os.path.join(maven_root, "bin", "mvn")
        if not os.path.isfile(mvn):
            os.makedirs(maven_root, exist_ok=True)
            get(
                self,
                url=self._MAVEN_URL,
                sha256=self._MAVEN_SHA256,
                destination=maven_root,
                strip_root=True,
            )
        if not os.path.isfile(mvn):
            raise ConanInvalidConfiguration(
                "Maven 3.6.3 extraction completed without bin/mvn"
            )
        return mvn

    def _prepare_environment(self, java_home):
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.path.join(self.build_folder, "tmp")
        )
        zsh_tmp = os.path.join(tmpdir, "zsh")
        os.makedirs(zsh_tmp, exist_ok=True)

        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            os.path.join(java_home, "bin")
            + os.pathsep
            + os.environ.get("PATH", "")
        )
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["TMPPREFIX"] = zsh_tmp
        maven_opts = os.environ.get("MAVEN_OPTS", "")
        os.environ["MAVEN_OPTS"] = (
            (maven_opts + " ") if maven_opts else ""
        ) + "-Xmx768m -Djava.io.tmpdir={}".format(tmpdir)

    @staticmethod
    def _surefire_result(report_dir):
        report_files = sorted(
            glob.glob(os.path.join(report_dir, "TEST-*.xml"))
        )
        if not report_files:
            raise ConanInvalidConfiguration(
                "Maven succeeded but produced no Surefire TEST-*.xml reports"
            )

        total = failures = errors = skipped = 0
        skipped_cases = []
        for report in report_files:
            root = ET.parse(report).getroot()
            total += int(root.get("tests", "0"))
            failures += int(root.get("failures", "0"))
            errors += int(root.get("errors", "0"))
            skipped += int(root.get("skipped", "0"))
            for case in root.iter("testcase"):
                if case.find("skipped") is not None:
                    skipped_cases.append(
                        "{}.{}".format(
                            case.get("classname", "?"),
                            case.get("name", "?"),
                        )
                    )

        failed = failures + errors
        executed = total - skipped
        passed = executed - failed
        marker = {
            "status": "passed" if (failed == 0 and skipped == 0 and executed == total) else "failed",
            "framework": "maven-surefire-junit4",
            "command": "mvn clean package -B -DskipTests=false -Dmaven.javadoc.skip=true",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if not (passed + failed == executed and executed + skipped <= total):
            raise ConanInvalidConfiguration(
                "Surefire count invariant violated: total={} executed={} "
                "passed={} failed={} skipped={}".format(
                    total, executed, passed, failed, skipped
                )
            )
        if skipped:
            # Rule4 dual判定：核心全绿但已执行小于总数时标failed加reason和gaps
            # 并让构建成功；passed仅当已执行等于官方总数时成立。
            # Skipped here means JUnit @Ignore/Assume (no failure);
            # case names come deterministically from TEST-*.xml.
            detail_cases = ", ".join(sorted(set(skipped_cases))[:10])
            marker["reason"] = (
                "Core suite green ({} executed, {} passed, 0 failures) "
                "but full suite incomplete: {}/{} executed, {} skipped".format(
                    executed, passed, executed, total, skipped
                )
            )
            marker["gaps"] = [
                {
                    "count": skipped,
                    "category": "environment",
                    "detail": (
                        "Surefire reports {} skipped (JUnit Assume/@Ignore, "
                        "0 failures). Cases: {}".format(skipped, detail_cases)
                    ),
                    "evidence": (
                        "target/surefire-reports/TEST-*.xml "
                        "tests={} skipped={}".format(total, skipped)
                    ),
                }
            ]
        return marker

    def _patch_pom(self):
        # HMBS: edit pom.xml in place instead of context-diff patches.
        # Context patches proved brittle under Conan's strict (fuzz=0)
        # applicator: hand-written hunks with slightly off indentation
        # (e.g. 13 vs 12 spaces before <plugin>) fail with
        # "source file is different - pom.xml". Substring replaces below
        # are whitespace-robust and verified against the t-digest-3.0 tag.
        pom = os.path.join(self.source_folder, "pom.xml")
        with open(pom, "r", encoding="utf-8") as pom_file:
            content = pom_file.read()
        original = content

        # 1) JDK 17 no longer accepts source/target 1.6: raise to 1.8.
        #    Only the <source>/<target> values and <compilerVersion>
        #    are touched; test logic is unaffected.
        replacements = [
            ("<compilerVersion>1.7</compilerVersion>",
             "<compilerVersion>1.8</compilerVersion>"),
            ("<source>1.6</source>", "<source>1.8</source>"),
            ("<target>1.6</target>", "<target>1.8</target>"),
            # 2) Run Surefire serially. Upstream configures
            #    parallel=methods + perCoreThreadCount, which races on the
            #    shared MersenneTwister via RandomUtils.useTestSeed and
            #    flakes with ArrayIndexOutOfBoundsException (Index 624).
            #    parallel=none keeps all 72 cases, only removes concurrency.
            ("<parallel>methods</parallel>", "<parallel>none</parallel>"),
        ]
        for old, new in replacements:
            if old not in content:
                raise ConanInvalidConfiguration(
                    "t-digest pom.xml missing expected token: {}".format(old)
                )
            content = content.replace(old, new)
        # Drop thread-count knobs that only matter for parallel runs.
        content = content.replace(
            "<perCoreThreadCount>true</perCoreThreadCount>", ""
        )
        content = content.replace("<threadCount>1</threadCount>", "")
        if content != original:
            with open(pom, "w", encoding="utf-8", newline="\n") as pom_file:
                pom_file.write(content)
            self.output.info("Patched pom.xml in place (JDK 1.8 + serial Surefire)")

    def build(self):
        self._patch_pom()
        java_home = self._find_or_install_java()
        self._prepare_environment(java_home)
        mvn = self._find_or_install_maven()

        log_path = os.path.join(self.build_folder, "maven-build.log")
        shell = shutil.which("sh") or "/bin/sh"
        command = [
            shell,
            mvn,
            "clean",
            "package",
            "-B",
            "-DskipTests=false",
            # Upstream pom binds maven-javadoc-plugin to package; on JDK 17
            # strict doclint turns 61 legacy-doc warnings into 27 errors and
            # fails the build before Surefire runs. Skip API docs only; tests
            # and JAR output are unaffected.
            "-Dmaven.javadoc.skip=true",
        ]
        with open(log_path, "w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                cwd=self.source_folder,
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
                sys.stdout.write(line)
                sys.stdout.flush()
            return_code = process.wait()

        if return_code != 0:
            raise ConanInvalidConfiguration(
                "Maven build failed with exit code {} (log: {})".format(
                    return_code, log_path
                )
            )

        marker = self._surefire_result(
            os.path.join(self.source_folder, "target", "surefire-reports")
        )
        print(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker),
            flush=True,
        )
        # 核心真失败才抛错；核心全绿但未满总数时标failed但让构建成功。
        if marker["failed"]:
            raise ConanInvalidConfiguration(
                "t-digest upstream tests reported failures"
            )

    def package(self):
        jar_name = "t-digest-{}.jar".format(self.version)
        jar_dir = os.path.join(self.source_folder, "target")
        jar_path = os.path.join(jar_dir, jar_name)
        if not os.path.isfile(jar_path):
            raise ConanInvalidConfiguration(
                "Maven did not produce {}".format(jar_path)
            )
        copy(
            self,
            jar_name,
            src=jar_dir,
            dst=os.path.join(self.package_folder, "libexec"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.resdirs = ["libexec"]
        jar = os.path.join(
            self.package_folder,
            "libexec",
            "t-digest-{}.jar".format(self.version),
        )
        self.buildenv_info.define_path("TDIGEST_JAR", jar)
        self.buildenv_info.define("TDIGEST_VERSION", str(self.version))
