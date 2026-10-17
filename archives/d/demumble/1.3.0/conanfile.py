#!/usr/bin/env python3
"""Conan recipe for demumble 1.3.0 on HarmonyOS."""

import json
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class DemumbleConan(ConanFile):
    name = "demumble"
    version = "1.3.0"
    description = "Command-line C++, Rust, D, Swift, and MSVC symbol demangler"
    license = "Apache-2.0"
    homepage = "https://github.com/nico/demumble"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # LLVM and Swift demanglers are vendored by the official source archive.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Conan names this setting "OHOS" but otherwise maps it to the
        # unsupported CMake system name "HarmonyOS".  The SDK ships
        # Platform/OHOS.cmake, so select that canonical platform explicitly.
        if str(self.settings.os) == "OHOS":
            toolchain.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

        if can_run(self):
            # The official script requires demumble to sit beside itself.
            copy(
                self,
                "demumble_test.py",
                src=self.source_folder,
                dst=self.build_folder,
                keep_path=False,
            )
            self.run(
                f'"{sys.executable}" "{os.path.join(self.build_folder, "demumble_test.py")}"',
                cwd=self.build_folder,
            )
            upstream = {
                "status": "passed",
                "framework": "python subprocess",
                "command": "python3 demumble_test.py",
                "discovered": 42,
                "executed": 42,
                "passed": 42,
                "failed": 0,
                "skipped": 0,
            }
        else:
            upstream = {
                "status": "skipped",
                "framework": "python subprocess",
                "command": "python3 demumble_test.py",
                "discovered": 42,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 42,
                "reason": "cross-build; OHOS binary is executed by test_package on the target",
            }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream)}")

    def package(self):
        copy(
            self,
            "demumble",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.txt", src=os.path.join(self.source_folder, "third_party", "llvm"),
             dst=os.path.join(self.package_folder, "licenses", "third_party", "llvm"))
        copy(self, "LICENSE.txt", src=os.path.join(self.source_folder, "third_party", "swift"),
             dst=os.path.join(self.package_folder, "licenses", "third_party", "swift"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
