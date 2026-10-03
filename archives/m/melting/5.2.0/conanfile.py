#!/usr/bin/env python3
"""Conan recipe — melting 5.2.0 (Ant + Java).

MELTING computes the enthalpy, entropy and melting temperature of nucleic
acid duplexes (DNA/DNA, DNA/RNA, RNA/RNA, mRNA/RNA) by the nearest-neighbor
method. Upstream is pure Java 1.5 + Ant (no Maven, no JUnit/TestNG).

Source: Debian orig tarball of the EBI MELTING 5.2.0 release
Build system: Ant (system ant, or Apache Ant 1.10.14 auto-installed)
Upstream tests: none (audited: build.xml has no test target, no junit/testng,
27 src/examples/MainTest*.java are manual mains, not a harness)

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package calls melting.Main.getMeltingResults API
R38: application package (bin/ wrappers) + commands.json
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get, replace_in_file


class MeltingConan(ConanFile):
    name = "melting"
    version = "5.2.0"
    description = "Compute melting temperature of nucleic acid duplex (nearest-neighbor method)."
    license = "GPL-2.0-only"
    homepage = "https://www.ebi.ac.uk/biomodels/tools/melting/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        pass

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "melting does not support OS: {}".format(self.settings.os)
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    _CA_BUNDLE_CANDIDATES = (
        "/etc/ssl/certs/ca-bundle.crt",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/system/etc/ssl/certs/ca-certificates.crt",
    )

    def _sandbox_env(self):
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
        return ["{}={}".format(k, v) for k, v in env.items()]

    def _fetch_text_file(self, url, out_path):
        # Pure Conan download (no external curl binary) so the build works
        # on minimal CI workers without curl. Must use download(), not
        # get(): get() treats the payload as an archive and tries to
        # unzip it, which fails with "BadZipFile: File is not a zip file"
        # for the plain-text install-jdk.sh script.
        dest_dir = os.path.dirname(out_path) or "."
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.isfile(out_path):
            os.remove(out_path)
        download(self, url, out_path)

    def _ensure_java(self):
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
        self._fetch_text_file(install_url, script_path)
        env = self._sandbox_env()
        self.run('sh "{}" 17.0.13'.format(script_path), env=self._env_list(env))
        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home
        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME, or fetch install-jdk.sh from the cmd-pkgs "
            "releases page and run it with argument 17.0.13."
        )

    _ANT_TARBALL_URL = "https://archive.apache.org/dist/ant/binaries/apache-ant-1.10.14-bin.tar.gz"

    def _ensure_ant(self):
        for candidate in [
            os.path.expanduser("~/ant/bin/ant"),
            os.path.expanduser("~/usr/local/ant/bin/ant"),
            "/usr/share/ant/bin/ant",
            "/opt/ant/bin/ant",
            "/usr/local/ant/bin/ant",
        ]:
            if os.path.isfile(candidate):
                self.output.info("Ant found at " + candidate)
                return candidate
        ant_in_path = shutil.which("ant")
        if ant_in_path:
            self.output.info("Ant found in PATH at " + ant_in_path)
            return ant_in_path
        self.output.info("Ant not found — installing Apache Ant 1.10.14 from archive...")
        home = os.path.expanduser("~")
        ant_root = os.path.join(home, "ant")
        # Conan-native download+extract (no external downloader). get()
        # verifies TLS and extracts the archive directly, so no manual
        # tarball handling is needed on minimal CI workers.
        os.makedirs(ant_root, exist_ok=True)
        get(self, self._ANT_TARBALL_URL, destination=ant_root,
            strip_root=True)
        ant_bin = os.path.join(ant_root, "bin", "ant")
        if os.path.isfile(ant_bin):
            self.output.info("Apache Ant 1.10.14 installed at " + ant_root)
            return ant_bin
        raise ConanInvalidConfiguration(
            "Failed to find or install Apache Ant 1.10.14. Install Ant or add ant to PATH."
        )

    def build(self):
        # Portability: upstream build.xml pins javac source/target 1.5, which
        # modern JDKs (incl. bishengjdk 17) reject. Bump to 1.8 in place.
        # (Replaces the former conandata patch, whose hunk header pointed at
        # line 30 while the compile target actually lives at line 43, so
        # strict patch application failed with "source file is different".)
        build_xml = os.path.join(self.source_folder, "build.xml")
        replace_in_file(
            self, build_xml,
            'source="1.5" target="1.5"',
            'source="1.8" target="1.8"',
        )
        sandbox_env = self._sandbox_env()
        for key in ("TMPDIR", "TMP", "TEMP", "CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
            if key in sandbox_env:
                os.environ[key] = sandbox_env[key]
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")
        ant_cmd = self._ensure_ant()
        env_list = self._env_list(dict(os.environ))
        self.run('"{}" jar'.format(ant_cmd), env=env_list)
        self.run('"{}" guijar'.format(ant_cmd), env=env_list)
        jar_path = os.path.join(self.source_folder, "build", "melting5.jar")
        gui_jar_path = os.path.join(self.source_folder, "build", "melting5GUI.jar")
        if not os.path.isfile(jar_path):
            raise ConanInvalidConfiguration(
                "Build artifact not found: {}. Ensure ant jar completed successfully.".format(jar_path)
            )
        if not os.path.isfile(gui_jar_path):
            self.output.warning("GUI jar not found (non-fatal): {}".format(gui_jar_path))
        import json
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "ant jar",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Upstream MELTING 5.2.0 has no automated test suite: build.xml defines only compile/jar/guijar/javadoc/clean targets (no test target), no junit/testng dependency, 27 src/examples/MainTest*.java are manual mains reading src/examples/test/*.txt without assertions or harness.",
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False), flush=True)

    def package(self):
        copy(self, "melting5.jar", os.path.join(self.source_folder, "build"),
             os.path.join(self.package_folder, "libexec"))
        copy(self, "melting5GUI.jar", os.path.join(self.source_folder, "build"),
             os.path.join(self.package_folder, "libexec"))
        copy(self, "*.xml", os.path.join(self.source_folder, "Data"),
             os.path.join(self.package_folder, "share", "melting", "Data"))
        copy(self, "melting", os.path.join(self.source_folder, "executable"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "melting-batch", os.path.join(self.source_folder, "executable"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "melting4", os.path.join(self.source_folder, "executable"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "README", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "GeneralPublicLicence", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.bindirs = ["bin"]
