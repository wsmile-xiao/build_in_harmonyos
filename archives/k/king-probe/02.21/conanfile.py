#!/usr/bin/env python3
"""Build Probe 02.21 with two explicit CLI aliases for native CI."""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save


class KingProbeConan(ConanFile):
    name = "king-probe"
    version = "02.21"
    description = "PDB molecular contact and surface analysis tool"
    license = "LicenseRef-Probe-Notice", "LicenseRef-Hybrid36-Notice"
    homepage = "https://github.com/rlabduke/probe"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # E276: codeload's tag basename has no archive suffix for Conan dispatch.
        get(self, **self.conan_data["sources"], filename="probe-02.21.tar.gz", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Tag 02.21 has no upstream test targets; census is in notes.md.
        self.output.info("Upstream 02.21: no registered tests; functional tests run in test_package")

    def package(self):
        suffix = ".exe" if self.settings.os == "Windows" else ""
        executable = "probe" + suffix
        binary_dir = os.path.join(self.build_folder, self.cpp.build.bindirs[0])
        if not os.path.isfile(os.path.join(binary_dir, executable)):
            raise ConanException("CMake did not produce " + os.path.join(binary_dir, executable))
        # Upstream CMake has no install rules.
        copy(self, executable, src=binary_dir,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "README*.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", self.name))
        # Preserve each source notice verbatim, including the separate hybrid36 notice.
        notices = []
        for filename in sorted(os.listdir(self.source_folder)):
            if filename.endswith((".c", ".h")):
                content = load(self, os.path.join(self.source_folder, filename))
                for block in re.findall(r"/\*.*?\*/", content, re.DOTALL):
                    if "NOTICE: This is free software" in block or "unrestricted Open Source" in block:
                        notices.append(filename + "\n" + block)
        if not any("hybrid_36_c.c\n" in notice for notice in notices):
            raise ConanException("Missing hybrid36 source notice")
        if not any(notice.startswith("probe.c\n") for notice in notices):
            raise ConanException("Missing Probe source notice")
        save(self, os.path.join(self.package_folder, "licenses", "SOURCE-NOTICES.txt"),
             "\n\n".join(notices) + "\n")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
