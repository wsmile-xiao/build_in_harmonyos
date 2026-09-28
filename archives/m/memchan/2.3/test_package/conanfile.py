#!/usr/bin/env python3
"""Consumer and HarmonyOS-specific tests for Memchan 2.3."""

import os
import shlex

from conan import ConanFile


class MemchanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        memchan_root = self.dependencies["memchan"].package_folder
        tcl_root = self.dependencies["tcl"].package_folder
        tclsh = os.path.join(tcl_root, "bin", "tclsh8.6")
        script = os.path.join(self.source_folder, "test_memchan.tcl")
        package_dir = os.path.join(memchan_root, "lib", "Memchan2.3")
        runner = self.conf.get(
            "user.memchan:qemu_runner", default="", check_type=str
        ).strip()
        command = (
            f"{shlex.quote(tclsh)} {shlex.quote(script)} {shlex.quote(package_dir)}"
        )
        if runner:
            command = f"{runner} {command}"
        test_driver = os.path.join(self.source_folder, "test.sh")
        self.run(
            f"sh {shlex.quote(test_driver)} {command}",
            env="conanrun",
        )
