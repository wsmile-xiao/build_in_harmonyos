#!/usr/bin/env python3
"""Conan recipe for ACR 2.2.6."""

import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class AcrConan(ConanFile):
    name = "acr"
    version = "2.2.6"
    description = "Autoconf replacement implemented with portable shell scripts"
    license = "GPL-2.0-only"
    homepage = "https://github.com/radareorg/acr"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        for script in ("acr", "acr-cat", "acr-sh"):
            replace_in_file(
                self,
                os.path.join(self.source_folder, "src", script),
                "@VERSION@",
                self.version,
            )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "acr-sh"),
            '"@DATADIR@/acr/modules/${STR2}.acr"',
            '"${ACR_BIN_DIR}/../share/acr/modules/${STR2}.acr"',
        )
        if self.settings.os == "Linux":
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        with tempfile.TemporaryDirectory(prefix="acr-upstream-", dir=self.build_folder) as temporary:
            test_root = os.path.join(temporary, "source")
            shutil.copytree(self.source_folder, test_root)
            tests_dir = os.path.join(test_root, "tests")

            triplet_script = os.path.join(tests_dir, "test-triplet.sh")
            with open(triplet_script, encoding="utf-8") as stream:
                triplet_count = sum(
                    1
                    for line in stream
                    if re.match(r"^\s*test\s+\S+\s+\S+\s+\S+\s*$", line)
                )
            if triplet_count != 12:
                raise ConanException(
                    f"unexpected upstream triplet inventory: {triplet_count}, expected 12"
                )

            triplets = subprocess.run(
                ["sh", "test-triplet.sh"],
                cwd=tests_dir,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
            )
            self.output.info("upstream triplet output:\n" + triplets.stdout.rstrip())
            if triplets.returncode != 0 or "FAIL" in triplets.stdout:
                raise ConanException("upstream triplet tests failed")

            examples = subprocess.run(
                ["sh", "test.sh"],
                cwd=tests_dir,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            self.output.info("upstream example output:\n" + examples.stdout.rstrip())
            executed_examples = examples.stdout.count("[>] executing ")
            if (
                examples.returncode != 0
                or executed_examples != 18
                or "[FAILED]" in examples.stdout
                or "ERROR:" in examples.stdout
            ):
                raise ConanException(
                    f"upstream example tests failed: {executed_examples}/18 executed"
                )
            self.output.info("upstream tests passed: 12 triplets + 18 examples = 30/30")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        for script in ("acr", "acr-cat", "acr-sh", "amr", "acr-wrap", "acr-install"):
            copy(
                self,
                script,
                os.path.join(self.source_folder, "src"),
                os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
        copy(
            self,
            "*.acr",
            os.path.join(self.source_folder, "modules"),
            os.path.join(self.package_folder, "share", "acr", "modules"),
            keep_path=False,
        )
        copy(
            self,
            "*.1",
            os.path.join(self.source_folder, "man", "man1"),
            os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "*.5",
            os.path.join(self.source_folder, "man", "man5"),
            os.path.join(self.package_folder, "share", "man", "man5"),
            keep_path=False,
        )
        if os.name != "nt":
            for script in ("acr", "acr-cat", "acr-sh", "amr", "acr-wrap", "acr-install"):
                os.chmod(os.path.join(self.package_folder, "bin", script), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
