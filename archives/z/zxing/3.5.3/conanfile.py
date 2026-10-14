#!/usr/bin/env python3
"""Conan recipe for ZXing 3.5.3 (core barcode encoding/decoding library, JVM)."""

import glob
import os
import re
import shutil
import struct
import subprocess
import zipfile
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
    rmdir,
)
from conan.tools.layout import basic_layout


class ZxingConan(ConanFile):
    name = "zxing"
    version = "3.5.3"
    description = "ZXing (Zebra Crossing) barcode image processing library - core encoder/decoder"
    license = "Apache-2.0"
    homepage = "https://github.com/zxing/zxing"
    url = "https://github.com/zxing/zxing"

    # Java artifacts have no static/shared semantics; "library" would demand
    # a `shared` option that does not exist for a JAR (weupnp/jackson-jr case).
    package_type = "unknown"
    # A JVM build consumes neither `compiler` nor `build_type`, but the OHOS
    # build profiles carry all four settings and the archive gate rejects a
    # recipe that omits any of them (missing_setting_compiler/build_type).
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    # Upstream core-module Surefire results for tag zxing-3.5.3.  Hard-coded so
    # a silent "0 tests ran" or a partial run cannot be reported as success.
    _EXPECTED_SUITES = 131
    _EXPECTED_TESTS = 542
    _EXPECTED_CLASSES = 291

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zxing is packaged for Linux/OpenHarmony JVM environments"
            )

    def package_id(self):
        # The packaged JAR is platform independent bytecode; the JVM that
        # consumes it is supplied by build_tools.bisheng_jdk.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ JDK
    @staticmethod
    def _java_executable(java_home, tool):
        return os.path.join(java_home, "bin", tool)

    @staticmethod
    def _java_major(output, tool):
        if tool == "java":
            match = re.search(r'version\s+"([0-9]+)(?:[._][^"]*)?"', output)
        else:
            match = re.search(r"(?m)^javac\s+([0-9]+)(?:[._]\S*)?", output)
        if not match:
            raise ConanException(
                "Could not parse {} version output: {!r}".format(tool, output.strip())
            )
        return int(match.group(1))

    def _validate_java_home(self, java_home):
        java_home = os.path.abspath(os.path.expanduser(java_home))
        outputs = {}
        for tool in ("java", "javac"):
            executable = self._java_executable(java_home, tool)
            if not os.path.isfile(executable):
                raise ConanException(
                    "{} is missing from the candidate JDK: {}".format(tool, executable)
                )
            try:
                result = subprocess.run(
                    [executable, "-version"],
                    check=True,
                    text=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                raise ConanException(
                    "Could not execute {} from {}: {}".format(tool, java_home, error)
                )
            output = "\n".join(
                part for part in (result.stdout, result.stderr) if part
            ).strip()
            major = self._java_major(output, tool)
            if major != 17:
                raise ConanException(
                    "{} from {} has major version {}, expected 17".format(
                        tool, java_home, major
                    )
                )
            outputs[tool] = output.splitlines()[0]

        self.output.info(
            "Using one verified JDK 17 home {}: {}; {}".format(
                java_home, outputs["java"], outputs["javac"]
            )
        )
        return java_home

    def _find_java_home(self):
        candidates = []
        configured = os.environ.get("JAVA_HOME", "")
        if configured:
            candidates.append(configured)
        candidates.extend(
            [
                os.path.expanduser("~/bishengjdk17"),
                os.path.expanduser("~/usr/local/bishengjdk17"),
                "/storage/Users/currentUser/usr/local/bishengjdk17",
                "/usr/local/bishengjdk17",
            ]
        )

        java_on_path = shutil.which("java")
        if java_on_path:
            candidates.append(
                os.path.dirname(os.path.dirname(os.path.realpath(java_on_path)))
            )

        rejected = []
        seen = set()
        for candidate in candidates:
            normalized = os.path.abspath(os.path.expanduser(candidate))
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                return self._validate_java_home(normalized)
            except ConanException as error:
                rejected.append(str(error))

        tool = self.conan_data["build_tools"]["bisheng_jdk"]
        installed = os.path.join(self.build_folder, "bishengjdk17")
        self.output.info(
            "No usable JDK 17 was found; downloading the pinned BiSheng JDK "
            "{} OpenHarmony AArch64 archive".format(tool["version"])
        )
        rmdir(self, installed)
        get(
            self,
            url=tool["url"],
            filename=tool["filename"],
            sha256=tool["sha256"],
            destination=installed,
            strip_root=True,
            keep_permissions=True,
        )
        try:
            return self._validate_java_home(installed)
        except ConanException as error:
            raise ConanException(
                "Pinned BiSheng JDK {} could not be used: {}. Rejected "
                "preinstalled candidates: {}".format(
                    tool["version"],
                    error,
                    "; ".join(rejected) if rejected else "none",
                )
            )

    # --------------------------------------------------------------- Maven
    def _maven_home(self):
        tool = self.conan_data["build_tools"]["maven"]
        home = os.path.join(
            self.build_folder, "apache-maven-{}".format(tool["version"])
        )
        marker = os.path.join(home, "bin", "mvn")
        if os.path.isfile(marker):
            return home
        if os.path.isdir(home):
            rmdir(self, home)
        self.output.info(
            "Downloading the pinned Apache Maven {} archive".format(tool["version"])
        )
        # strip_root=True drops the `apache-maven-3.6.3/` container directory,
        # so the destination must be the directory Maven has to live in.
        get(
            self,
            url=tool["url"],
            filename=tool["filename"],
            sha256=tool["sha256"],
            destination=home,
            strip_root=True,
            keep_permissions=True,
        )
        if not os.path.isfile(marker):
            raise ConanException(
                "Pinned Apache Maven {} could not be unpacked: missing {}".format(
                    tool["version"], marker
                )
            )
        return home

    @staticmethod
    def _maven_command(mvn_script):
        if os.access(mvn_script, os.X_OK):
            launcher = [mvn_script]
        else:
            # HMDFS can drop the executable bit on extracted files.
            launcher = ["/bin/sh", mvn_script]
        return launcher + [
            "-B",
            "-ntp",
            "-Dstyle.color=never",
            "-Djava.awt.headless=true",
            "clean",
            "verify",
        ]

    # -------------------------------------------------------------- verify
    def _verify_upstream_tests(self):
        reports = glob.glob(
            os.path.join(
                self.source_folder,
                "core",
                "target",
                "surefire-reports",
                "TEST-*.xml",
            )
        )
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        for report in reports:
            suite = ET.parse(report).getroot()
            for name in totals:
                totals[name] += int(suite.attrib.get(name, "0"))

        if (
            len(reports) != self._EXPECTED_SUITES
            or totals["tests"] != self._EXPECTED_TESTS
            or totals["failures"]
            or totals["errors"]
            or totals["skipped"]
        ):
            raise ConanException(
                "Unexpected upstream test result: suites={}, totals={}".format(
                    len(reports), totals
                )
            )
        self.output.info(
            "Upstream tests passed: {} Surefire suites, {} tests, "
            "0 failures/errors/skips".format(
                self._EXPECTED_SUITES, self._EXPECTED_TESTS
            )
        )

    def _artifact_path(self, folder):
        return os.path.join(folder, "core-{}.jar".format(self.version))

    @staticmethod
    def _class_major(data, entry, jar_path):
        if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
            raise ConanException(
                "{} in {} is not a valid Java class".format(entry, jar_path)
            )
        return struct.unpack(">H", data[6:8])[0]

    def _verify_jar(self, jar_path, expected_classes):
        if not os.path.isfile(jar_path) or os.path.getsize(jar_path) <= 0:
            raise ConanException("Required artifact is missing or empty: {}".format(jar_path))
        try:
            with zipfile.ZipFile(jar_path) as archive:
                corrupt = archive.testzip()
                if corrupt:
                    raise ConanException(
                        "{} has a corrupt ZIP entry: {}".format(jar_path, corrupt)
                    )
                entries = set(archive.namelist())
                classes = sorted(e for e in entries if e.endswith(".class"))
                if len(classes) != expected_classes:
                    raise ConanException(
                        "{} has {} classes, expected {}".format(
                            jar_path, len(classes), expected_classes
                        )
                    )
                majors = {self._class_major(archive.read(e), e, jar_path) for e in classes}
                if majors != {52}:
                    raise ConanException(
                        "{} has unexpected bytecode majors {} (expected 52)".format(
                            jar_path, sorted(majors)
                        )
                    )
                manifest = archive.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
                if "Automatic-Module-Name: com.google.zxing" not in manifest:
                    raise ConanException(
                        "{} is missing Automatic-Module-Name: com.google.zxing".format(
                            jar_path
                        )
                    )
                required = (
                    "com/google/zxing/MultiFormatReader.class",
                    "com/google/zxing/MultiFormatWriter.class",
                    "com/google/zxing/qrcode/QRCodeWriter.class",
                )
                missing = [e for e in required if e not in entries]
                if missing:
                    raise ConanException(
                        "{} is missing entries: {}".format(jar_path, ", ".join(missing))
                    )
        except (OSError, zipfile.BadZipFile) as error:
            raise ConanException("Could not validate {}: {}".format(jar_path, error))

        self.output.info(
            "Artifact verification passed: nonempty JAR, clean ZIP, {} Java 8 "
            "classes, Automatic-Module-Name present".format(expected_classes)
        )

    def _verify_source_artifact(self):
        self._verify_jar(
            self._artifact_path(os.path.join(self.source_folder, "core", "target")),
            self._EXPECTED_CLASSES,
        )

    def _verify_packaged_artifact(self):
        self._verify_jar(
            os.path.join(
                self.package_folder, "lib", "zxing-core-{}.jar".format(self.version)
            ),
            self._EXPECTED_CLASSES,
        )

    # --------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)

        java_home = self._find_java_home()
        maven_home = self._maven_home()
        mvn_script = os.path.join(maven_home, "bin", "mvn")

        environment = os.environ.copy()
        environment["JAVA_HOME"] = java_home
        environment["MAVEN_HOME"] = maven_home
        environment["MAVEN_SKIP_RC"] = "1"
        environment["MAVEN_OPTS"] = "-Xmx1024m -Dos.name=Linux"
        environment["PATH"] = os.pathsep.join(
            [
                os.path.join(java_home, "bin"),
                os.path.join(maven_home, "bin"),
                environment.get("PATH", ""),
            ]
        )
        # Maven, Surefire forked JVMs and java.awt do not recognise "HarmonyOS"
        # as an os.name value; expose the platform family as Linux to Java tools.
        existing_java_options = environment.get("JAVA_TOOL_OPTIONS", "").strip()
        environment["JAVA_TOOL_OPTIONS"] = (existing_java_options + " -Dos.name=Linux").strip()

        # Build the `core` module only: it is the delivered library and it has
        # no third-party runtime dependency.  Building from inside `core/` also
        # keeps the JDK-17-only `zxingorg` profile (whose pom still points at a
        # 3.5.3-SNAPSHOT parent on this tag) out of the reactor.
        core_dir = os.path.join(self.source_folder, "core")
        if not os.path.isfile(os.path.join(core_dir, "pom.xml")):
            raise ConanException("Upstream core/pom.xml is missing: {}".format(core_dir))

        self.output.info(
            "Building the upstream core module and running its complete "
            "Surefire test suite"
        )
        subprocess.run(
            self._maven_command(mvn_script),
            cwd=core_dir,
            env=environment,
            check=True,
        )
        self._verify_upstream_tests()
        self._verify_source_artifact()

    # -------------------------------------------------------------- package
    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        # rename() will not create the destination directory itself.
        os.makedirs(lib_dir, exist_ok=True)
        rename(
            self,
            self._artifact_path(os.path.join(self.source_folder, "core", "target")),
            os.path.join(lib_dir, "zxing-core-{}.jar".format(self.version)),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "NOTICE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "zxing"),
        )
        self._verify_packaged_artifact()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib"]
        jar_path = os.path.join(
            self.package_folder, "lib", "zxing-core-{}.jar".format(self.version)
        )
        self.buildenv_info.define_path("ZXING_CORE_JAR", jar_path)
        self.runenv_info.define_path("ZXING_CORE_JAR", jar_path)
