#!/usr/bin/env python3
"""Conan test_package for adplug 2.4.

L1 test: verify the adplugdb CLI tool (which uses libadplug CAdPlug::
get_version()) runs and the library is functional. adplug is a library
package, so test.c uses only standard C and invokes the adplugdb binary
via system().
"""
import os

from conan import ConanFile


class AdplugTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_adplug")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap
        # binary execution with bash.
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        # adplug 是 library 包，VirtualRunEnv 不自动把 bin 加入 PATH，
        # 显式将 package bin 目录加入 PATH 再运行 test_adplug。
        pkg_folder = self.dependencies["adplug"].package_folder
        adplug_bin = os.path.join(pkg_folder, "bin")
        self.run(
            f"PATH={adplug_bin}:$PATH {bash} -c './test_adplug'",
            env="conanrun",
        )
