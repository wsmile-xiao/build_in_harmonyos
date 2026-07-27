#!/usr/bin/env python3
"""Conan test_package for CastXML — command-line tool.

Verifies the castxml binary is installed and functional by running
castxml --version directly from the installed package folder.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
import os


class CastxmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["castxml"]
        binary = os.path.join(dep.package_folder, "bin", "castxml")

        llvm_root = os.environ.get("OHOS_SDK_LLVM_ROOT")
        if not llvm_root:
            sdk_home = os.environ.get("OHOS_SDK_HOME",
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18")
            llvm_root = os.path.join(sdk_home, "ohos", "native", "llvm")

        env = Environment()
        env.append_path("LD_LIBRARY_PATH", os.path.join(llvm_root, "lib"))
        env.append_path("LD_LIBRARY_PATH",
                        os.path.join(llvm_root, "lib", "aarch64-linux-ohos", "c++"))

        self.output.info(f"Testing castxml binary at: {binary}")
        with env.vars(self).apply():
            self.run(f'"{binary}" --version')
