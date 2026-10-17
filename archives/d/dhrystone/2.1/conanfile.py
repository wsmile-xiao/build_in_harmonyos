#!/usr/bin/env python3
"""Conan recipe for Dhrystone 2.1, built as separate CMake translation units."""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches, copy, download, export_conandata_patches, load, save,
)


class DhrystoneConan(ConanFile):
    name = "dhrystone"
    version = "2.1"
    description = "Dhrystone 2.1 integer CPU and compiler benchmark"
    license = "LicenseRef-Dhrystone"
    homepage = "https://www.netlib.org/benchmark/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Dhrystone requires POSIX process timing")

    def source(self):
        # Extract only known text members of the historical shar; never execute it.
        archive = os.path.join(self.source_folder, "dhry-c")
        download(self, filename=archive, **self.conan_data["sources"])
        contents = load(self, archive)
        pattern = re.compile(
            r"^sed >([\w.]+) <<'//GO.SYSIN DD \1' 's/\^-//'\n"
            r"(.*?)^//GO.SYSIN DD \1$", re.MULTILINE | re.DOTALL
        )
        members = pattern.findall(contents)
        expected = {"RATIONALE", "README_C", "VARIATIONS", "dhry.h",
                    "dhry_1.c", "dhry_2.c", "dhry_c.dif", "submit.frm"}
        if len(members) != 8 or {name for name, _ in members} != expected:
            raise ConanException("unexpected Dhrystone 2.1 shar members")
        for name, body in members:
            lines = body.splitlines(keepends=True)
            if any(not line.startswith("-") for line in lines):
                raise ConanException(f"invalid shar member: {name}")
            save(self, os.path.join(self.source_folder, name),
                 "".join(line[1:] for line in lines))
        apply_conandata_patches(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests", "framework": "none", "command": "",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
            "reason": "Netlib dhry-c contains eight source/documentation files, "
                      "no build scripts or automated test suite; printed reference "
                      "values are checked by the added Conan consumer suite",
        }))

    def package(self):
        CMake(self).install()
        os.chmod(os.path.join(self.package_folder, "bin", "dhrystone"), 0o755)
        for name in ("README_C", "RATIONALE", "dhry.h"):
            copy(self, name, self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
