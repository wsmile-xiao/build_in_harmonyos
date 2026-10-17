#!/usr/bin/env python3
"""Consumer test for Jackson jr 2.14.0."""

import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, rmdir


class JacksonJrTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

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
            "Consumer uses one verified JDK 17 home {}: {}; {}".format(
                java_home, outputs["java"], outputs["javac"]
            )
        )
        return java_home

    def _jdk_tool(self):
        dependency = self.dependencies["jackson-jr"]
        try:
            tool = dependency.conan_data["build_tools"]["bisheng_jdk"]
        except (KeyError, TypeError):
            raise ConanException(
                "The tested jackson-jr recipe does not expose its pinned "
                "BiSheng JDK metadata in conandata.yml"
            )

        required = ("url", "filename", "sha256", "version")
        missing = [name for name in required if not tool.get(name)]
        if missing:
            raise ConanException(
                "Pinned BiSheng JDK metadata is incomplete: {}".format(
                    ", ".join(missing)
                )
            )
        return tool

    def _find_java_home(self, tool):
        installed = os.path.join(self.build_folder, "bishengjdk17")
        roots = [
            os.environ.get("JAVA_HOME", ""),
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
            "/storage/Users/currentUser/usr/local/bishengjdk17",
            "/usr/local/bishengjdk17",
            installed,
        ]
        java_on_path = shutil.which("java")
        if java_on_path:
            roots.append(
                os.path.dirname(os.path.dirname(os.path.realpath(java_on_path)))
            )

        rejected = []
        seen = set()
        for root in roots:
            if not root:
                continue
            root = os.path.abspath(os.path.expanduser(root))
            if root in seen:
                continue
            seen.add(root)
            try:
                return self._validate_java_home(root)
            except ConanException as error:
                rejected.append(str(error))

        rmdir(self, installed)
        self.output.info(
            "No usable JDK 17 was found for the consumer test; downloading "
            "the tested recipe's pinned BiSheng JDK {} OpenHarmony AArch64 "
            "archive".format(tool["version"])
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
                "Pinned BiSheng JDK {} could not be used by the consumer "
                "test: {}. Rejected preinstalled candidates: {}".format(
                    tool["version"],
                    error,
                    "; ".join(rejected) if rejected else "none",
                )
            )

    def test(self):
        dependency = self.dependencies["jackson-jr"]
        package_folder = dependency.package_folder
        version = str(dependency.ref.version)
        lib_path = os.path.join(package_folder, "lib")
        script = os.path.join(self.source_folder, "test.py")
        java_source = os.path.join(
            self.source_folder, "TestJacksonJr.java"
        )
        java_home = self._find_java_home(self._jdk_tool())
        java = self._java_executable(java_home, "java")
        javac = self._java_executable(java_home, "javac")
        self.run(
            '"{}" "{}" --lib "{}" --version "{}" --work "{}" --java "{}" '
            '--javac "{}" --source "{}"'.format(
                sys.executable,
                script,
                lib_path,
                version,
                self.build_folder,
                java,
                javac,
                java_source,
            ),
            env=None,
        )
