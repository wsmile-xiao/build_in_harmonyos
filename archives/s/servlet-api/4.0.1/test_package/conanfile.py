#!/usr/bin/env python3
"""Consumer test — servlet-api 4.0.1 Java API."""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout


class ServletApiTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)
        self.folders.build = "build-release"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _validate_java_home(candidate):
        candidate = os.path.abspath(os.path.expanduser(candidate))
        java = os.path.join(candidate, "bin", "java")
        javac = os.path.join(candidate, "bin", "javac")
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
        return candidate

    def _verified_java_home(self):
        candidates = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]
        java_on_path = shutil.which("java")
        if java_on_path:
            candidates.append(
                os.path.dirname(os.path.dirname(os.path.realpath(java_on_path)))
            )
        for candidate in candidates:
            if candidate:
                verified = self._validate_java_home(candidate)
                if verified:
                    return verified

        dependency = self.dependencies["servlet-api"]
        tool = dependency.conan_data["build_tools"]["bisheng_jdk"]
        build_os = str(self.settings_build.os)
        build_arch = str(self.settings_build.arch)
        if build_os != "OHOS" or build_arch != "armv8":
            raise ConanInvalidConfiguration(
                "Pinned BiSheng JDK requires an OHOS/armv8 build context; "
                f"got {build_os}/{build_arch}"
            )
        installed = os.path.join(self.build_folder, "bishengjdk17-test")
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

    def test(self):
        package_folder = self.dependencies["servlet-api"].package_folder
        script = os.path.join(self.source_folder, "test.sh")
        java_home = self._verified_java_home()
        self.run(
            f'zsh "{script}" "{package_folder}" "{java_home}"', env="conanrun"
        )
