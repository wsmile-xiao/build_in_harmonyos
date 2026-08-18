#!/usr/bin/env python3
"""Conan recipe — servlet-api 4.0.1 (Custom/Javac)."""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ServletApiConan(ConanFile):
    name = "servlet-api"
    version = "4.0.1"
    description = "Java Servlet 4.0 API"
    license = "CDDL-1.1 OR GPL-2.0-only WITH Classpath-exception-2.0"
    homepage = "https://javaee.github.io/servlet-spec/"
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
                f"servlet-api does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _validate_java_home(java_home):
        java_home = os.path.abspath(os.path.expanduser(java_home))
        java = os.path.join(java_home, "bin", "java")
        javac = os.path.join(java_home, "bin", "javac")
        if not os.path.isfile(java) or not os.path.isfile(javac):
            return None
        try:
            java_result = subprocess.run(
                [java, "-version"], check=True, text=True, capture_output=True
            )
            javac_result = subprocess.run(
                [javac, "-version"], check=True, text=True, capture_output=True
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        java_output = "\n".join((java_result.stdout, java_result.stderr))
        javac_output = "\n".join((javac_result.stdout, javac_result.stderr))
        if "BiSheng" not in java_output:
            return None
        if not re.search(r'17\.0\.13(?:[+"\s]|$)', java_output):
            return None
        if not re.search(r'javac\s+17\.0\.13(?:\s|$)', javac_output):
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
                    self.output.info("Using verified BiSheng JDK 17.0.13: " + verified)
                    return verified
        return None

    def _ensure_java(self):
        java_home = self._find_java_home()
        if java_home:
            return java_home

        tool = self.conan_data["build_tools"]["bisheng_jdk"]
        build_os = str(self.settings_build.os)
        build_arch = str(self.settings_build.arch)
        if build_os != "OHOS" or build_arch != "armv8":
            raise ConanInvalidConfiguration(
                "Pinned BiSheng JDK fallback requires an OHOS/armv8 build context; "
                f"got {build_os}/{build_arch}"
            )
        installed = os.path.join(self.build_folder, "bishengjdk17")
        self.output.info("Downloading pinned BiSheng JDK " + tool["version"])
        tool_url = "{}://{}{}".format(
            tool["scheme"], tool["host"], tool["path"]
        )
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
                "Pinned JDK failed BiSheng 17.0.13 identity validation"
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

        source_root = os.path.join(self.source_folder, "src", "main", "java")
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

        self.run(f'"{javac}" -source 8 -target 8 -encoding UTF-8 -d "{classes}" @"{sources_list}"')
        copy(self, "*.properties", source_root, classes, keep_path=True)
        resources = os.path.join(self.source_folder, "src", "main", "resources")
        copy(self, "META-INF/*", resources, classes, keep_path=True)
        output = os.path.join(self.build_folder, "javax.servlet-api-4.0.1.jar")
        manifest = os.path.join(classes, "META-INF", "MANIFEST.MF")
        self.run(f'"{jar}" cfm "{output}" "{manifest}" -C "{classes}" .')

    def package(self):
        copy(self, "javax.servlet-api-4.0.1.jar", self.build_folder,
             os.path.join(self.package_folder, "libexec"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.buildenv_info.define_path(
            "SERVLET_API_JAR",
            os.path.join(self.package_folder, "libexec", "javax.servlet-api-4.0.1.jar"),
        )
