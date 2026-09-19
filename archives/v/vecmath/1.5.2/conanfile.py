#!/usr/bin/env python3
"""Conan recipe — vecmath 1.5.2 (javax.vecmath, Java3D).

Downloads the official vecmath 1.5.2 source archive from Maven Central
(vecmath-1.5.2-sources.jar, the only official source distribution of this
exact release), compiles the pure-Java sources with javac, and packages the
resulting vecmath-1.5.2.jar.

Source: https://repo1.maven.org/maven2/javax/vecmath/vecmath/1.5.2/
         vecmath-1.5.2-sources.jar
License: GPL-2.0 WITH Classpath-exception-2.0
Build system: plain javac + jar (the 1.5.2 release ships no build script)

Upstream tests: the 1.5.2 release artifact contains NO test code (audited in
test_package/MANIFEST.yml; see upstream_test_audit). The HMBS machine gates
are therefore emitted from test_package/test(): HMBS_UPSTREAM_TEST_RESULT with
status="no_tests" and HMBS_TEST_PACKAGE_RESULT from the real API smoke test.

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package calls real vecmath API (Vector3f/Matrix4f/Quat4f)
R38: library package (no commands.json needed)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    unzip,
)


class VecmathConan(ConanFile):
    name = "vecmath"
    version = "1.5.2"
    description = "Java3D javax.vecmath — vector and matrix mathematics library (pure Java)"
    license = "GPL-2.0 WITH Classpath-exception-2.0"
    homepage = "https://java.net/projects/vecmath/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vecmath does not support OS: {self.settings.os}"
            )

    def source(self):
        # The 1.5.2 sources jar has no single root directory (files live
        # directly under javax/vecmath/), so strip_root=False keeps the
        # package path intact. `download` + `unzip` is used explicitly (rather
        # than `get`) because the extension is `.jar`: unzip() handles any
        # valid zip (jar) via Python's zipfile regardless of the extension.
        sources = self.conan_data["sources"]
        jar_file = sources["filename"]
        download(
            self,
            url=sources["url"],
            filename=jar_file,
            sha256=sources["sha256"],
        )
        unzip(self, jar_file, destination=self.source_folder, strip_root=False)

    @staticmethod
    def _validate_java_home(java_home):
        java_home = os.path.abspath(os.path.expanduser(java_home))
        java = os.path.join(java_home, "bin", "java")
        javac = os.path.join(java_home, "bin", "javac")
        if not os.path.isfile(java) or not os.path.isfile(javac):
            return None
        return java_home

    def _find_java_home(self):
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]
        java = shutil.which("java")
        if java:
            candidates.append(os.path.dirname(os.path.dirname(os.path.realpath(java))))
        for candidate in candidates:
            if candidate:
                verified = self._validate_java_home(candidate)
                if verified:
                    self.output.info("Using JDK: " + verified)
                    return verified
        return None

    def _ensure_java(self):
        java_home = self._find_java_home()
        if java_home:
            return java_home

        tool = self.conan_data["build_tools"]["bisheng_jdk"]
        # Install to the canonical home location (~/bishengjdk17) so the
        # downstream test_package() can discover the same JDK (build() and
        # test_package run in separate Conan processes).
        installed = os.path.expanduser("~/bishengjdk17")
        self.output.info("Downloading pinned BiSheng JDK " + tool["version"])
        tool_url = "{}://{}{}".format(tool["scheme"], tool["host"], tool["path"])
        os.makedirs(installed, exist_ok=True)
        get(
            self,
            url=tool_url,
            filename=tool["filename"],
            sha256=tool["sha256"],
            destination=installed,
            strip_root=True,
            keep_permissions=True,
        )
        verified = self._validate_java_home(installed)
        if not verified:
            raise ConanInvalidConfiguration(
                "Pinned JDK missing bin/java or bin/javac at " + installed
            )
        return verified

    def build(self):
        apply_conandata_patches(self)
        java_home = self._ensure_java()
        javac = os.path.join(java_home, "bin", "javac")
        jar = os.path.join(java_home, "bin", "jar")
        classes = os.path.join(self.build_folder, "classes")
        sources_list = os.path.join(self.build_folder, "sources.list")
        os.makedirs(classes, exist_ok=True)

        # Collect every *.java under the extracted source tree
        source_root = self.source_folder
        java_sources = []
        for root, _, files in os.walk(source_root):
            for filename in files:
                if filename.endswith(".java"):
                    java_sources.append(os.path.join(root, filename))
        java_sources.sort()
        if not java_sources:
            raise ConanInvalidConfiguration("No Java source files found")
        with open(sources_list, "w", encoding="utf-8") as handle:
            handle.write("\n".join(java_sources) + "\n")

        self.run(
            f'"{javac}" -source 8 -target 8 -encoding UTF-8 '
            f'-d "{classes}" @"{sources_list}"'
        )

        # Copy non-code resources (.properties) next to the compiled classes
        copy(self, "*.properties", source_root, classes, keep_path=True)

        output = os.path.join(self.build_folder, f"vecmath-{self.version}.jar")
        self.run(f'"{jar}" cf "{output}" -C "{classes}" .')
        self.output.info("Built " + output)

    def package(self):
        copy(
            self,
            f"vecmath-{self.version}.jar",
            self.build_folder,
            os.path.join(self.package_folder, "libexec"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        # Expose the JAR path so consumers (notably test_package) can locate it
        self.buildenv_info.define_path(
            "VECMATH_JAR",
            os.path.join(self.package_folder, "libexec", f"vecmath-{self.version}.jar"),
        )
