#!/usr/bin/env python3
"""Conan recipe for the JFlex 1.9.1 JVM scanner generator."""

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
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JflexConan(ConanFile):
    name = "jflex"
    version = "1.9.1"
    description = "Fast lexical analyzer generator for Java"
    license = "BSD-3-Clause"
    homepage = "https://www.jflex.de/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "build-scripts"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "jflex.sh"
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
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jflex is supported only on Linux and OHOS"
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

        cert_candidates = [
            os.environ.get("SSL_CERT_FILE", ""),
            os.environ.get("CURL_CA_BUNDLE", ""),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/ssl/certs/cacert.pem",
        ]
        for ssl_cert in cert_candidates:
            if ssl_cert and os.path.isfile(ssl_cert):
                os.environ["SSL_CERT_FILE"] = ssl_cert
                os.environ["CURL_CA_BUNDLE"] = ssl_cert
                break

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
        for report in report_files:
            root = ET.parse(report).getroot()
            total += int(root.get("tests", "0"))
            failures += int(root.get("failures", "0"))
            errors += int(root.get("errors", "0"))
            skipped += int(root.get("skipped", "0"))

        failed = failures + errors
        passed = total - failed - skipped
        return {
            "status": "passed" if failed == 0 else "failed",
            "framework": "maven-surefire-junit4",
            "command": "mvn clean package -B -DskipTests=false",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    def build(self):
        apply_conandata_patches(self)
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
        if marker["failed"]:
            raise ConanInvalidConfiguration(
                "JFlex upstream tests reported failures"
            )

    def package(self):
        jar_name = "jflex-full-{}.jar".format(self.version)
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
            "LICENSE_JFLEX",
            src=os.path.join(self.source_folder, "src", "main", "resources"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "jflex.sh",
            src=self.export_sources_folder,
            dst=os.path.join(self.package_folder, "libexec"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["libexec"]

        jar = os.path.join(
            self.package_folder,
            "libexec",
            "jflex-full-{}.jar".format(self.version),
        )
        command = os.path.join(
            self.package_folder, "libexec", "jflex.sh"
        )
        self.buildenv_info.define_path("JFLEX_JAR", jar)
        self.buildenv_info.define_path("JFLEX_COMMAND", command)
        self.buildenv_info.define("JFLEX_VERSION", str(self.version))
