#!/usr/bin/env python3
"""Conan recipe for Jackson jr 2.14.0."""

import glob
import os
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JacksonJrConan(ConanFile):
    name = "jackson-jr"
    version = "2.14.0"
    description = "Compact JSON data binding, composer, and simple tree library"
    license = "Apache-2.0"
    homepage = "https://github.com/FasterXML/jackson-jr"
    url = "https://github.com/FasterXML/jackson-jr"

    package_type = "unknown"
    settings = "os", "arch"
    exports_sources = "conandata.yml"

    _modules = (
        "jr-all",
        "jr-objects",
        "jr-stree",
        "jr-annotation-support",
        "jr-retrofit2",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jackson-jr is packaged for Linux/OpenHarmony JVM environments"
            )

    def package_id(self):
        # Runtime classes are Java 8 bytecode; the versioned JPMS descriptors
        # are Java 9 bytecode. Both are independent of CPU and OS.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _java_executable(java_home, tool):
        suffix = ".exe" if os.name == "nt" else ""
        return os.path.join(java_home, "bin", tool + suffix)

    @staticmethod
    def _java_major(output, tool):
        if tool == "java":
            match = re.search(r'version\s+"([0-9]+)(?:[._][^"]*)?"', output)
        else:
            match = re.search(r"(?m)^javac\s+([0-9]+)(?:[._]\S*)?", output)
        if not match:
            raise ConanException(
                "Could not parse {} version output: {!r}".format(
                    tool, output.strip()
                )
            )
        return int(match.group(1))

    def _validate_java_home(self, java_home):
        java_home = os.path.abspath(os.path.expanduser(java_home))
        outputs = {}
        for tool in ("java", "javac"):
            executable = self._java_executable(java_home, tool)
            if not os.path.isfile(executable):
                raise ConanException(
                    "{} is missing from the candidate JDK: {}".format(
                        tool, executable
                    )
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
                    "Could not execute {} from {}: {}".format(
                        tool, java_home, error
                    )
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

    def _maven_command(self, java):
        wrapper_jar = os.path.join(
            self.source_folder, ".mvn", "wrapper", "maven-wrapper.jar"
        )
        if not os.path.isfile(wrapper_jar):
            raise ConanException("Upstream Maven wrapper JAR is missing")
        return [
            java,
            "-Xmx768m",
            "-Dos.name=Linux",
            "-classpath",
            wrapper_jar,
            "-Dmaven.multiModuleProjectDirectory={}".format(self.source_folder),
            "org.apache.maven.wrapper.MavenWrapperMain",
            "-B",
            "-ntp",
            "-Dstyle.color=never",
            "-Dmaven.javadoc.skip=true",
            "clean",
            "verify",
        ]

    def _verify_upstream_tests(self):
        reports = glob.glob(
            os.path.join(
                self.source_folder,
                "**",
                "target",
                "surefire-reports",
                "TEST-*.xml",
            ),
            recursive=True,
        )
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        for report in reports:
            suite = ET.parse(report).getroot()
            for name in totals:
                totals[name] += int(suite.attrib.get(name, "0"))

        expected_suites = 35
        expected_tests = 150
        if (
            len(reports) != expected_suites
            or totals["tests"] != expected_tests
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
            "Upstream tests passed: 35 Surefire suites, 150 tests, "
            "0 failures/errors/skips"
        )

    def _artifact_name(self, module):
        return "jackson-{}-{}.jar".format(module, self.version)

    @staticmethod
    def _class_major(data, entry, jar_path):
        if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
            raise ConanException(
                "{} in {} is not a valid Java class".format(entry, jar_path)
            )
        return struct.unpack(">H", data[6:8])[0]

    def _verify_jar(self, module, jar_path):
        if not os.path.isfile(jar_path) or os.path.getsize(jar_path) <= 0:
            raise ConanException(
                "Required {} artifact is missing or empty: {}".format(
                    module, jar_path
                )
            )

        try:
            with zipfile.ZipFile(jar_path) as archive:
                corrupt = archive.testzip()
                if corrupt:
                    raise ConanException(
                        "{} has a corrupt ZIP entry: {}".format(
                            jar_path, corrupt
                        )
                    )
                entries = set(archive.namelist())
                class_entries = sorted(
                    entry for entry in entries if entry.endswith(".class")
                )
                regular_classes = [
                    entry
                    for entry in class_entries
                    if not entry.startswith("META-INF/versions/")
                ]
                regular_majors = {
                    self._class_major(archive.read(entry), entry, jar_path)
                    for entry in regular_classes
                }
                module_info = "META-INF/versions/9/module-info.class"
                if module_info not in entries:
                    raise ConanException(
                        "{} is missing its Java 9 JPMS descriptor".format(
                            jar_path
                        )
                    )
                module_major = self._class_major(
                    archive.read(module_info), module_info, jar_path
                )
                if regular_majors != {52} or module_major != 53:
                    raise ConanException(
                        "Unexpected bytecode in {}: runtime majors={}, "
                        "JPMS major={}".format(
                            jar_path, sorted(regular_majors), module_major
                        )
                    )

                if module == "jr-all":
                    required = {
                        "com/fasterxml/jackson/jr/ob/JSON.class",
                        "com/fasterxml/jackson/jr/stree/JrsObject.class",
                        "com/fasterxml/jackson/jr/private_/JsonFactory.class",
                    }
                    missing = sorted(required - entries)
                    if missing or len(class_entries) != 238:
                        raise ConanException(
                            "Invalid jr-all JAR: missing={}, classes={}".format(
                                missing, len(class_entries)
                            )
                        )
        except (OSError, zipfile.BadZipFile) as error:
            raise ConanException(
                "Could not validate {}: {}".format(jar_path, error)
            )

        self.output.info(
            "{} verification passed: nonempty JAR, clean ZIP, Java 8 "
            "runtime classes, Java 9 JPMS descriptor".format(module)
        )

    def _verify_source_artifacts(self):
        for module in self._modules:
            self._verify_jar(
                module,
                os.path.join(
                    self.source_folder,
                    module,
                    "target",
                    self._artifact_name(module),
                ),
            )

    def _verify_packaged_artifacts(self):
        for module in self._modules:
            self._verify_jar(
                module,
                os.path.join(
                    self.package_folder,
                    "lib",
                    self._artifact_name(module),
                ),
            )

    def build(self):
        apply_conandata_patches(self)

        java_home = self._find_java_home()
        java = self._java_executable(java_home, "java")
        environment = os.environ.copy()
        environment["JAVA_HOME"] = java_home
        environment["PATH"] = (
            os.path.join(java_home, "bin")
            + os.pathsep
            + environment.get("PATH", "")
        )
        # Maven and its forked Surefire JVMs do not recognize "HarmonyOS" as
        # an os.name value. OpenHarmony PC provides a Linux-compatible JVM
        # environment, so expose the platform family as Linux to Java tools.
        existing_java_options = environment.get("JAVA_TOOL_OPTIONS", "").strip()
        environment["JAVA_TOOL_OPTIONS"] = (
            existing_java_options + " -Dos.name=Linux"
        ).strip()

        self.output.info(
            "Building all Jackson jr modules and running the complete "
            "upstream Maven test suite"
        )
        subprocess.run(
            self._maven_command(java),
            cwd=self.source_folder,
            env=environment,
            check=True,
        )
        self._verify_upstream_tests()
        self._verify_source_artifacts()

    def package(self):
        for module in self._modules:
            artifact = self._artifact_name(module)
            copy(
                self,
                artifact,
                src=os.path.join(self.source_folder, module, "target"),
                dst=os.path.join(self.package_folder, "lib"),
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._verify_packaged_artifacts()
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(
                self.package_folder, "share", "doc", "jackson-jr"
            ),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib"]
        jar_path = os.path.join(
            self.package_folder,
            "lib",
            "jackson-jr-all-{}.jar".format(self.version),
        )
        self.buildenv_info.define_path("JACKSON_JR_JAR", jar_path)
        self.runenv_info.define_path("JACKSON_JR_JAR", jar_path)
